"""Patient routes."""
from fastapi import APIRouter
from server.db import query
from server.config import CATALOG, SCHEMA

router = APIRouter(prefix="/api", tags=["pacientes"])
T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"
_escape = lambda val: "NULL" if val is None else "'" + str(val).replace("'", "''") + "'"


@router.get("/pacientes")
async def list_pacientes():
    """List all patients."""
    rows = await query(
        f"""SELECT p.*,
            (SELECT COUNT(*) FROM {T('exames')} e WHERE e.cpf = p.cpf) as total_exames,
            (SELECT COUNT(*) FROM {T('uploads')} u WHERE u.cpf = p.cpf) as total_uploads
        FROM {T('pacientes')} p
        ORDER BY p.criado_em DESC LIMIT 100"""
    )
    return {"pacientes": rows}


@router.get("/paciente")
async def get_paciente(cpf: str):
    """Get patient details with their exams."""
    paciente = await query(
        f"SELECT * FROM {T('pacientes')} WHERE cpf = {_escape(cpf)}"
    )
    if not paciente:
        return {"error": "Patient not found"}, 404

    exames = await query(
        f"""SELECT * FROM {T('exames')} WHERE cpf = {_escape(cpf)}
            ORDER BY data_exame DESC, categoria"""
    )
    uploads = await query(
        f"SELECT * FROM {T('uploads')} WHERE cpf = {_escape(cpf)} ORDER BY data_upload DESC"
    )

    return {
        "paciente": paciente[0],
        "exames": exames,
        "uploads": uploads,
    }
