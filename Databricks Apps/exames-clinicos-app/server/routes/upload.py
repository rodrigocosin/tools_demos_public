"""Upload routes - handle PDF upload, storage, and processing."""
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import PyPDF2

from server.db import execute, query
from server.config import CATALOG, SCHEMA
from server.volume import upload_to_volume
from server.llm import extract_exam_data, generate_parecer

router = APIRouter(prefix="/api", tags=["uploads"])

T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"


def _escape(val: str) -> str:
    """Escape single quotes for SQL."""
    if val is None:
        return "NULL"
    return "'" + str(val).replace("'", "''") + "'"


def _parse_date(val: str | None) -> str | None:
    """Convert Brazilian date (DD/MM/YY or DD/MM/YYYY) to ISO format YYYY-MM-DD.
    Returns None if val is None or unparseable."""
    if not val:
        return None
    val = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(val, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Already ISO or unrecognized — return as-is if it looks like a date
    if len(val) >= 8 and "-" in val:
        return val
    return None


def _nome_como_cpf(nome: str) -> str:
    """Gera uma chave estável a partir do nome quando o CPF não está disponível.
    Normaliza removendo acentos e espaços extras para garantir deduplicação
    de PDFs do mesmo paciente sem CPF."""
    import unicodedata
    if not nome or nome.strip().lower() in ("desconhecido", ""):
        return f"NOCPF_{uuid.uuid4().hex[:8]}"
    normalized = unicodedata.normalize("NFKD", nome.strip().upper())
    ascii_nome = "".join(c for c in normalized if not unicodedata.combining(c))
    # Remove caracteres não alfanuméricos exceto espaço
    clean = " ".join(ascii_nome.split())
    return f"NOME_{clean}"


@router.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a PDF file, save to volume, and trigger async processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    upload_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    stored_name = f"{timestamp}_{upload_id[:8]}_{safe_name}"

    # Upload to volume
    try:
        volume_path = await upload_to_volume(content, stored_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to volume: {str(e)}")

    # Insert upload record
    sql = f"""INSERT INTO {T('uploads')} VALUES (
        {_escape(upload_id)}, NULL, {_escape(file.filename)},
        {_escape(volume_path)},
        current_timestamp(), 'pendente', 0
    )"""
    try:
        await execute(sql)
    except Exception as e:
        print(f"Error inserting upload record: {e}")

    # Process in background
    background_tasks.add_task(process_upload, upload_id, content, volume_path)

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "volume_path": volume_path,
        "status": "pendente",
    }


async def process_upload(upload_id: str, pdf_content: bytes, volume_path: str):
    """Process the uploaded PDF: extract text, call LLM, store results."""
    try:
        # Update status
        await execute(
            f"UPDATE {T('uploads')} SET status = 'processando' WHERE upload_id = {_escape(upload_id)}"
        )

        # Extract text from PDF
        pdf_text = _extract_pdf_text(pdf_content)
        if not pdf_text.strip():
            await execute(
                f"UPDATE {T('uploads')} SET status = 'erro_texto_vazio' WHERE upload_id = {_escape(upload_id)}"
            )
            return

        # Call LLM to extract structured data
        exam_data = await extract_exam_data(pdf_text)

        paciente = exam_data.get("paciente", {})
        exames = exam_data.get("exames", [])
        data_exame = exam_data.get("data_exame")

        # Extract patient fields
        nome = paciente.get("nome", "Desconhecido")
        dn = paciente.get("data_nascimento")
        idade = paciente.get("idade")
        sexo = paciente.get("sexo")
        cpf = paciente.get("cpf") or _nome_como_cpf(nome)
        medico = paciente.get("medico_solicitante")

        dn_iso = _parse_date(dn)
        dn_sql = _escape(dn_iso) if dn_iso else "NULL"
        idade_sql = str(idade) if idade else "NULL"

        # Upsert patient: MERGE on CPF (deduplication)
        await execute(f"""
            MERGE INTO {T('pacientes')} AS t
            USING (SELECT {_escape(cpf)} AS cpf, {_escape(nome)} AS nome,
                          CAST({dn_sql} AS DATE) AS data_nascimento,
                          CAST({idade_sql} AS INT) AS idade,
                          {_escape(sexo)} AS sexo,
                          {_escape(medico)} AS medico_solicitante) AS s
            ON t.cpf = s.cpf
            WHEN NOT MATCHED THEN INSERT (cpf, nome, data_nascimento, idade, sexo, medico_solicitante, criado_em)
              VALUES (s.cpf, s.nome, s.data_nascimento, s.idade, s.sexo, s.medico_solicitante, current_timestamp())
        """)

        # Generate parecer
        parecer = ""
        try:
            parecer = await generate_parecer(exames, paciente)
        except Exception as e:
            print(f"Parecer generation failed: {e}")
            parecer = "Parecer nao disponivel."

        # Insert exames
        for exam in exames:
            exame_id = str(uuid.uuid4())
            data_exame_iso = _parse_date(data_exame)
            data_exame_sql = _escape(data_exame_iso) if data_exame_iso else "NULL"

            await execute(f"""INSERT INTO {T('exames')} VALUES (
                {_escape(exame_id)}, {_escape(upload_id)}, {_escape(cpf)},
                {_escape(exam.get('tipo_exame', 'outros'))},
                {_escape(exam.get('categoria', 'outros'))},
                {_escape(exam.get('nome_exame', 'N/A'))},
                {_escape(exam.get('valor_resultado', 'N/A'))},
                {_escape(exam.get('unidade', ''))},
                {_escape(exam.get('valor_referencia', ''))},
                {_escape(exam.get('status_resultado', 'normal'))},
                {_escape(parecer)},
                {data_exame_sql}, current_timestamp()
            )""")

        # Update upload
        await execute(f"""UPDATE {T('uploads')}
            SET status = 'concluido',
                cpf = {_escape(cpf)},
                total_exames = {len(exames)}
            WHERE upload_id = {_escape(upload_id)}""")

    except Exception as e:
        print(f"Processing error for {upload_id}: {e}")
        try:
            await execute(
                f"UPDATE {T('uploads')} SET status = {_escape(f'erro: {str(e)[:200]}')} WHERE upload_id = {_escape(upload_id)}"
            )
        except Exception:
            pass


def _extract_pdf_text(pdf_content: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    reader = PyPDF2.PdfReader(BytesIO(pdf_content))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


@router.get("/uploads")
async def list_uploads():
    """List all uploads with status."""
    rows = await query(
        f"SELECT * FROM {T('uploads')} ORDER BY data_upload DESC LIMIT 100"
    )
    return {"uploads": rows}


@router.post("/processar/{upload_id}")
async def reprocess_upload(upload_id: str, background_tasks: BackgroundTasks):
    """Re-process an existing upload."""
    rows = await query(
        f"SELECT * FROM {T('uploads')} WHERE upload_id = {_escape(upload_id)}"
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Upload not found")

    upload = rows[0]
    volume_path = upload.get("caminho_volume", "")

    # Read PDF from volume
    from server.volume import read_from_volume
    try:
        pdf_content = await read_from_volume(volume_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file from volume: {str(e)}")

    # Delete old exames for this upload
    await execute(f"DELETE FROM {T('exames')} WHERE upload_id = {_escape(upload_id)}")

    background_tasks.add_task(process_upload, upload_id, pdf_content, volume_path)
    return {"status": "reprocessando", "upload_id": upload_id}
