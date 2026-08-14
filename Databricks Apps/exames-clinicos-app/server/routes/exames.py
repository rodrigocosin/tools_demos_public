"""Exam routes - list and filter exams."""
from typing import Optional
from fastapi import APIRouter, Query
from server.db import query
from server.config import CATALOG, SCHEMA

router = APIRouter(prefix="/api", tags=["exames"])
T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"


@router.get("/exames")
async def list_exames(
    categoria: Optional[str] = Query(None),
    status_resultado: Optional[str] = Query(None),
    cpf: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    """List all exams with optional filters."""
    conditions = []
    if categoria:
        conditions.append(f"categoria = '{categoria}'")
    if status_resultado:
        conditions.append(f"status_resultado = '{status_resultado}'")
    if cpf:
        conditions.append(f"e.cpf = '{cpf}'")

    where = " AND ".join(conditions)
    where_clause = f"WHERE {where}" if where else ""

    sql = f"""SELECT e.*, p.nome as paciente_nome
        FROM {T('exames')} e
        LEFT JOIN {T('pacientes')} p ON e.cpf = p.cpf
        {where_clause}
        ORDER BY e.processado_em DESC
        LIMIT {limit}"""

    rows = await query(sql)
    return {"exames": rows}


@router.get("/exames/{upload_id}")
async def get_exames_by_upload(upload_id: str):
    """Get all exams for a specific upload."""
    rows = await query(
        f"""SELECT e.*, p.nome as paciente_nome
            FROM {T('exames')} e
            LEFT JOIN {T('pacientes')} p ON e.cpf = p.cpf
            WHERE e.upload_id = '{upload_id}'
            ORDER BY e.categoria, e.nome_exame"""
    )
    return {"exames": rows}


@router.get("/stats")
async def get_stats():
    """Get dashboard statistics."""
    total_uploads = await query(f"SELECT COUNT(*) as cnt FROM {T('uploads')}")
    total_exames = await query(f"SELECT COUNT(*) as cnt FROM {T('exames')}")
    total_pacientes = await query(f"SELECT COUNT(*) as cnt FROM {T('pacientes')}")
    alterados = await query(
        f"SELECT COUNT(*) as cnt FROM {T('exames')} WHERE status_resultado = 'alterado'"
    )
    criticos = await query(
        f"SELECT COUNT(*) as cnt FROM {T('exames')} WHERE status_resultado = 'critico'"
    )
    by_category = await query(
        f"SELECT categoria, COUNT(*) as cnt FROM {T('exames')} GROUP BY categoria ORDER BY cnt DESC"
    )
    by_status = await query(
        f"SELECT status_resultado, COUNT(*) as cnt FROM {T('exames')} GROUP BY status_resultado ORDER BY cnt DESC"
    )
    recent_uploads = await query(
        f"SELECT u.*, p.nome as paciente_nome FROM {T('uploads')} u LEFT JOIN {T('pacientes')} p ON u.cpf = p.cpf ORDER BY u.data_upload DESC LIMIT 5"
    )

    return {
        "total_uploads": int(total_uploads[0]["cnt"]) if total_uploads else 0,
        "total_exames": int(total_exames[0]["cnt"]) if total_exames else 0,
        "total_pacientes": int(total_pacientes[0]["cnt"]) if total_pacientes else 0,
        "exames_alterados": int(alterados[0]["cnt"]) if alterados else 0,
        "exames_criticos": int(criticos[0]["cnt"]) if criticos else 0,
        "by_category": by_category,
        "by_status": by_status,
        "recent_uploads": recent_uploads,
    }
