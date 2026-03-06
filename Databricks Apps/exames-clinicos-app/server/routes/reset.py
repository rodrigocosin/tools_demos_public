"""Reset endpoint — apaga todos os dados para demo."""
import aiohttp
from fastapi import APIRouter
from server.db import execute, FULL_TABLE
from server.config import get_workspace_host, get_token, CATALOG, SCHEMA

router = APIRouter()
T = FULL_TABLE

VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/uploads_volume"


@router.delete("/api/reset")
async def reset_all():
    """Apaga todos os registros das tabelas e arquivos do volume."""
    # 1. Apaga registros (na ordem correta para evitar conflitos)
    await execute(f"DELETE FROM {T('exames')}")
    await execute(f"DELETE FROM {T('uploads')}")
    await execute(f"DELETE FROM {T('pacientes')}")

    # 2. Remove arquivos do volume
    host = get_workspace_host()
    token = get_token()
    api_headers = {"Authorization": f"Bearer {token}"}
    deleted_files = 0

    async with aiohttp.ClientSession() as session:
        list_url = f"{host}/api/2.0/fs/files{VOLUME_PATH}"
        async with session.get(list_url, headers=api_headers) as r:
            if r.status == 200:
                data = await r.json()
                files = data.get("files", [])
                for f in files:
                    file_path = f.get("path", "")
                    if file_path:
                        del_url = f"{host}/api/2.0/fs/files{file_path}"
                        async with session.delete(del_url, headers=api_headers):
                            deleted_files += 1

    return {
        "status": "ok",
        "message": "Ambiente zerado com sucesso",
        "arquivos_removidos": deleted_files,
    }
