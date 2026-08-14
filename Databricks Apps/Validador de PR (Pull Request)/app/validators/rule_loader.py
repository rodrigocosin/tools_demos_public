"""Carrega regras dinâmicas da tabela Delta com cache TTL."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_cache: dict = {"rules": None, "ts": 0.0}
_TTL = 300  # 5 minutos


def get_rules() -> list[dict] | None:
    """
    Retorna lista de regras habilitadas da tabela Delta.
    Usa cache com TTL de 5 minutos.
    Retorna None em caso de falha (ativa fallback para validadores estáticos).
    """
    now = time.time()
    if _cache["rules"] is not None and (now - _cache["ts"]) < _TTL:
        return _cache["rules"]

    try:
        from app.db_client import list_enabled_rules
        rows = list_enabled_rules()
        _cache["rules"] = rows
        _cache["ts"] = now
        logger.info("Carregadas %d regras dinâmicas", len(rows))
        return rows
    except Exception:
        logger.exception("Falha ao carregar regras dinâmicas - usando fallback estático")
        return None


def invalidate_cache():
    """Invalida o cache forçando recarga na próxima chamada."""
    _cache["rules"] = None
    _cache["ts"] = 0.0
