"""LLM integration via Foundation Model API."""
import json
import aiohttp
from server.config import get_workspace_host, get_token, SERVING_ENDPOINT


_PATIENT_SYSTEM = """Voce e um especialista em leitura de laudos e exames clinicos brasileiros.
Extraia os dados do PACIENTE e do MEDICO SOLICITANTE do texto abaixo e retorne SOMENTE um JSON sem markdown.

ATENCAO — FORMATO FLEURY (colunas fora de ordem):
O PDF pode ter sido lido coluna por coluna, gerando texto fora de ordem como:
  DR. ANDRE JAIME CRM 87719SP   <- medico (aparece ANTES dos labels)
  Cliente:                       <- label SEM valor na mesma linha
  Data de Nascimento:            <- label SEM valor na mesma linha
  Medico:                        <- label SEM valor na mesma linha
  RODRIGO QUINELATO COSIN        <- paciente (aparece APOS o label Medico:!)
  16/05/1983 Ficha:              <- data de nascimento + label de outra data

Nesse formato, o valor de cada label esta na proxima linha nao-vazia, nao na mesma linha.

REGRAS CRITICAS:
1. "nome" = nome do PACIENTE (a pessoa que fez o exame).
   - Aparece apos labels como: Cliente, Paciente, Nome, Beneficiario, Solicitado para
   - No formato Fleury, aparece logo abaixo do label (mesmo que o label diga "Medico:")
   - NUNCA e o medico. NUNCA e um label. NUNCA e uma data.
2. "medico_solicitante" = medico que SOLICITOU o exame.
   - Identificado por: prefixo Dr./Dra., numero CRM, ou label "Medico Solicitante"
   - Remova titulos (Dr., Dra.) e numero CRM do nome final
3. "data_nascimento" = data de nascimento do paciente (geralmente a mais antiga)
4. "data_exame" = data de realizacao/coleta/ficha do exame (geralmente a mais recente)
   - Procure labels: "Data da Ficha", "Data do Exame", "Data de Realizacao", "Data de Coleta"
   - Se nao houver label, use a data que NAO seja a data de nascimento
5. "cpf" = CPF do paciente no formato XXX.XXX.XXX-XX
6. "idade" = idade em anos (numero inteiro)
7. "sexo" = "M" ou "F"

Retorne SOMENTE o JSON, sem explicacoes:
{"nome": "...", "medico_solicitante": "...", "data_nascimento": "DD/MM/YYYY", "data_exame": "DD/MM/YYYY", "cpf": "...", "idade": null, "sexo": null}
Use null para campos nao encontrados."""


# Conservative limit: system prompt (~800 chars) + response (4096 tokens) leaves ~20k chars
# for user content before hitting typical endpoint input limits.
_CHUNK_SIZE = 20_000
_CHUNK_OVERLAP = 1_500


async def call_llm(messages: list[dict], max_tokens: int = 4096, temperature: float = 0.1) -> str:
    """Call Foundation Model API and return the assistant response text."""
    host = get_workspace_host()
    token = get_token()
    endpoint = SERVING_ENDPOINT

    url = f"{host}/serving-endpoints/{endpoint}/invocations"
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"LLM API error ({resp.status}): {error[:500]}")
            data = await resp.json()

    choices = data.get("choices", [])
    if not choices:
        raise Exception("No choices in LLM response")

    return choices[0].get("message", {}).get("content", "")


def _parse_json_response(response: str) -> dict | list:
    """Strip markdown fences and parse JSON from LLM response."""
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:])
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to find the first JSON structure
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = response.find(start_char)
            end = response.rfind(end_char) + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    continue
    raise ValueError(f"Could not parse JSON from response: {response[:300]}")


async def extract_exam_data(pdf_text: str) -> dict:
    """Extract structured exam data from PDF text using LLM.

    For long PDFs (>_CHUNK_SIZE chars), patient data is extracted from the header
    and exams are extracted chunk-by-chunk to avoid input token limits.
    """
    print(f"[LLM] PDF text: {len(pdf_text)} chars")

    # ── Step 1: patient / doctor data from header via LLM ─────────────────
    header = pdf_text[:6000]
    patient_data: dict = {}
    try:
        patient_resp = await call_llm([
            {"role": "system", "content": _PATIENT_SYSTEM},
            {"role": "user", "content": f"Texto do cabecalho do laudo:\n\n{header}"},
        ], max_tokens=300, temperature=0.0)
        parsed = _parse_json_response(patient_resp)
        if isinstance(parsed, dict):
            patient_data = {k: v for k, v in parsed.items() if v not in (None, "", "null")}
    except Exception as e:
        print(f"[LLM] Patient extraction failed: {e}")

    paciente = {
        "nome": patient_data.get("nome") or "Desconhecido",
        "data_nascimento": patient_data.get("data_nascimento"),
        "idade": patient_data.get("idade"),
        "sexo": patient_data.get("sexo"),
        "cpf": patient_data.get("cpf"),
        "medico_solicitante": patient_data.get("medico_solicitante"),
    }
    data_exame = patient_data.get("data_exame")
    print(f"[LLM] Patient: {paciente['nome']} | Medico: {paciente['medico_solicitante']} | DataExame: {data_exame}")

    # ── Step 2: exam list from all chunks ─────────────────────────────────
    if len(pdf_text) <= _CHUNK_SIZE:
        chunks = [pdf_text]
    else:
        chunks = []
        pos = 0
        while pos < len(pdf_text):
            chunks.append(pdf_text[pos: pos + _CHUNK_SIZE])
            pos += _CHUNK_SIZE - _CHUNK_OVERLAP
    print(f"[LLM] Extracting exams from {len(chunks)} chunk(s)")

    exam_system = """Voce e um assistente especializado em analise de exames clinicos brasileiros.
Extraia TODOS os exames clinicos do texto e retorne APENAS um JSON array (sem markdown):
[
  {
    "nome_exame": "Nome do Exame",
    "tipo_exame": "sangue|urina|imagem|hormonios|bioquimica",
    "categoria": "hemograma|glicemia|colesterol|funcao_renal|funcao_hepatica|hormonios|urina|imagem|outros",
    "valor_resultado": "valor como string",
    "unidade": "unidade de medida ou vazio",
    "valor_referencia": "faixa de referencia ou vazio",
    "status_resultado": "normal|alterado|critico"
  }
]
Retorne [] se nao encontrar exames. Retorne SOMENTE o array JSON."""

    exames: list[dict] = []
    seen_names: set[str] = set()

    for i, chunk in enumerate(chunks):
        print(f"[LLM] Chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
        try:
            exam_resp = await call_llm([
                {"role": "system", "content": exam_system},
                {"role": "user", "content": f"Extraia os exames clinicos do texto:\n\n{chunk}"},
            ], max_tokens=4096, temperature=0.05)
            chunk_exames = _parse_json_response(exam_resp)
            if not isinstance(chunk_exames, list):
                chunk_exames = []
        except Exception as e:
            print(f"[LLM] Exam chunk {i+1} failed: {e}")
            chunk_exames = []

        for e in chunk_exames:
            key = str(e.get("nome_exame", "")).strip().lower()
            if key and key not in seen_names:
                seen_names.add(key)
                exames.append(e)

    print(f"[LLM] Total exams extracted: {len(exames)}")
    return {"paciente": paciente, "data_exame": data_exame, "exames": exames}


async def generate_parecer(exames: list[dict], paciente: dict) -> str:
    """Generate medical parecer (opinion) for the exam results."""
    system_prompt = """Voce e um medico especialista analisando resultados de exames clinicos.
Gere um parecer medico breve e objetivo em portugues sobre os resultados.
Destaque:
- Valores alterados ou criticos
- Possiveis correlacoes entre exames
- Recomendacoes gerais
Mantenha o parecer em no maximo 3 paragrafos. Seja direto e profissional."""

    exames_text = "\n".join([
        f"- {e.get('nome_exame', 'N/A')}: {e.get('valor_resultado', 'N/A')} {e.get('unidade', '')} "
        f"(Ref: {e.get('valor_referencia', 'N/A')}) - Status: {e.get('status_resultado', 'N/A')}"
        for e in exames
    ])

    paciente_info = (
        f"Paciente: {paciente.get('nome', 'N/A')}, "
        f"{paciente.get('idade', 'N/A')} anos, "
        f"Sexo: {paciente.get('sexo', 'N/A')}"
    )

    user_prompt = f"{paciente_info}\n\nResultados dos exames:\n{exames_text}\n\nGere o parecer medico:"

    return await call_llm([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ], max_tokens=1024, temperature=0.3)
