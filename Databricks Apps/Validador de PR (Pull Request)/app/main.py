"""
Validador Automático de PRs - Backend FastAPI.
App para validação de conformidade de notebooks Databricks.
"""

from __future__ import annotations

import html
import logging
import os
import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.llm_assistant import FRIENDLY_TYPES, VALID_RULE_TYPES, generate_rule_params
from app.parser.notebook_parser import MAX_FILE_SIZE, parse_notebook
from app.validators.engine import run_all_validations
from app.validators.rule_loader import get_rules, invalidate_cache

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Validador de PRs", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

STATIC_DIR = Path(__file__).parent / "static"
_SAFE_ID_PATTERN = re.compile(r"^[a-z0-9_]{3,80}$")


# ---------------------------------------------------------------------------
# VALIDAÇÃO DE NOTEBOOKS
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Validador de PRs</h1>")


@app.post("/api/validate")
async def validate_notebook(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo ausente.")
    safe_filename = os.path.basename(file.filename)
    if not safe_filename or ".." in safe_filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Arquivo excede {MAX_FILE_SIZE // (1024*1024)} MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    try:
        notebook = parse_notebook(content, safe_filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    report = run_all_validations(notebook)
    report_dict = report.to_dict()
    _sanitize_dict(report_dict)
    return JSONResponse(content=report_dict)


# ---------------------------------------------------------------------------
# GERENCIAMENTO DE REGRAS
# ---------------------------------------------------------------------------

@app.get("/api/rules")
async def api_list_rules():
    """Lista todas as regras (incluindo desabilitadas)."""
    try:
        from app.db_client import list_all_rules
        rules = list_all_rules()
        return {"rules": rules, "count": len(rules)}
    except Exception as e:
        logger.exception("Erro ao listar regras")
        raise HTTPException(status_code=500, detail=f"Erro ao carregar regras: {type(e).__name__}: {e}")


@app.post("/api/rules")
async def api_create_rule(request: Request):
    """Cria uma nova regra na tabela."""
    body = await request.json()

    rule_id = body.get("rule_id", "").strip()
    rule_type = body.get("rule_type", "").strip()
    category = body.get("category", "").strip()
    severity = body.get("severity", "erro").strip()
    message_fail = body.get("message_fail", "").strip()

    if not _SAFE_ID_PATTERN.match(rule_id):
        raise HTTPException(status_code=400, detail="rule_id inválido (use snake_case, 3-80 chars).")
    if rule_type not in VALID_RULE_TYPES:
        raise HTTPException(status_code=400, detail=f"rule_type inválido: {rule_type}")
    if not category:
        raise HTTPException(status_code=400, detail="category é obrigatório.")
    if severity not in ("erro", "aviso"):
        raise HTTPException(status_code=400, detail="severity deve ser 'erro' ou 'aviso'.")
    if not message_fail:
        raise HTTPException(status_code=400, detail="message_fail é obrigatório.")
    if not isinstance(body.get("params", {}), dict):
        raise HTTPException(status_code=400, detail="params deve ser um objeto JSON.")

    try:
        from app.db_client import insert_rule, rule_exists
        if rule_exists(rule_id):
            raise HTTPException(status_code=409, detail=f"rule_id '{rule_id}' já existe.")

        insert_rule({
            "rule_id": rule_id,
            "rule_type": rule_type,
            "category": category,
            "severity": severity,
            "message_ok": body.get("message_ok") or "",
            "message_fail": message_fail,
            "details_fail": body.get("details_fail") or "",
            "params": body.get("params", {}),
            "enabled": body.get("enabled", True),
            "priority": body.get("priority", 200),
        })
        invalidate_cache()
        return {"status": "created", "rule_id": rule_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao criar regra")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {e}")


@app.put("/api/rules/{rule_id}")
async def api_update_rule(rule_id: str, request: Request):
    """Atualiza uma regra (toggle enabled, editar campos)."""
    if not _SAFE_ID_PATTERN.match(rule_id):
        raise HTTPException(status_code=400, detail="rule_id inválido.")

    body = await request.json()
    allowed = {"category", "severity", "message_ok", "message_fail", "details_fail", "params", "enabled", "priority"}
    fields = {k: v for k, v in body.items() if k in allowed}

    if not fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    try:
        from app.db_client import update_rule
        update_rule(rule_id, fields)
        invalidate_cache()
        return {"status": "updated", "rule_id": rule_id}
    except Exception as e:
        logger.exception("Erro ao atualizar regra")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar: {e}")


@app.delete("/api/rules/{rule_id}")
async def api_delete_rule(rule_id: str):
    """Remove uma regra da tabela."""
    if not _SAFE_ID_PATTERN.match(rule_id):
        raise HTTPException(status_code=400, detail="rule_id inválido.")
    try:
        from app.db_client import delete_rule
        delete_rule(rule_id)
        invalidate_cache()
        return {"status": "deleted", "rule_id": rule_id}
    except Exception as e:
        logger.exception("Erro ao remover regra")
        raise HTTPException(status_code=500, detail=f"Erro ao remover: {e}")


# ---------------------------------------------------------------------------
# ASSISTENTE LLM
# ---------------------------------------------------------------------------

@app.post("/api/generate-rule")
async def api_generate_rule(request: Request):
    """Usa LLM para gerar rule_type e params a partir de descrição natural."""
    body = await request.json()
    description = body.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Descrição é obrigatória.")
    if len(description) > 1000:
        raise HTTPException(status_code=400, detail="Descrição muito longa (max 1000 chars).")

    try:
        result = generate_rule_params(description, body.get("friendly_type", ""), body.get("category", ""))
    except Exception as e:
        logger.exception("Erro no generate_rule_params")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar regra: {type(e).__name__}: {e}")

    if result is None:
        raise HTTPException(status_code=500, detail="LLM não retornou resultado válido. Tente reformular a descrição.")
    return result


@app.get("/api/rule-types")
async def api_rule_types():
    return {"friendly_types": FRIENDLY_TYPES, "valid_types": list(VALID_RULE_TYPES)}


# ---------------------------------------------------------------------------
# UTILITÁRIOS
# ---------------------------------------------------------------------------

@app.post("/api/reload-rules")
async def api_reload_rules():
    invalidate_cache()
    rules = get_rules()
    return {"status": "reloaded", "rules_count": len(rules) if rules else 0}


@app.get("/api/health")
async def api_health():
    rules = get_rules()
    return {
        "status": "ok",
        "rules_source": "dynamic" if rules else "static_fallback",
        "rules_count": len(rules) if rules else 0,
    }


def _sanitize_dict(obj):
    if isinstance(obj, dict):
        for key in obj:
            if isinstance(obj[key], str):
                obj[key] = html.escape(obj[key])
            elif isinstance(obj[key], (dict, list)):
                _sanitize_dict(obj[key])
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str):
                obj[i] = html.escape(item)
            elif isinstance(item, (dict, list)):
                _sanitize_dict(item)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
