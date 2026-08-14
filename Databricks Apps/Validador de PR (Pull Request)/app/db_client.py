"""
Cliente SQL para Databricks usando o SDK com autenticação automática do App.
Usa Statement Execution API com parâmetros para evitar SQL injection e
problemas de escape em strings com caracteres especiais.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

_TABLE_NAME_PATTERN = re.compile(r"^\w+\.\w+\.\w+$")


def _get_warehouse_id() -> str:
    http_path = os.environ.get("SQL_WAREHOUSE_HTTP_PATH", "")
    if http_path:
        parts = http_path.rstrip("/").split("/")
        return parts[-1] if parts else ""
    return ""


def _get_rules_table() -> str:
    table = os.environ.get("RULES_TABLE", "cosin_aws_serverless_catalog.pr_review.tb_validacao_regras")
    if not _TABLE_NAME_PATTERN.match(table):
        raise ValueError("Nome de tabela inválido")
    return table


def _execute_sql(statement: str, parameters: list | None = None) -> dict:
    """Executa SQL via Databricks SDK com suporte a parâmetros."""
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementParameterListItem

    warehouse_id = _get_warehouse_id()
    if not warehouse_id:
        raise RuntimeError("SQL_WAREHOUSE_HTTP_PATH não configurado")

    w = WorkspaceClient()

    logger.info("Executing SQL: %.150s...", statement)

    # Converte parâmetros para o formato do SDK
    sdk_params = None
    if parameters:
        sdk_params = []
        for p in parameters:
            sdk_params.append(StatementParameterListItem(
                name=p["name"],
                value=str(p["value"]) if p["value"] is not None else None,
                type=p.get("type", "STRING"),
            ))

    response = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="30s",
        parameters=sdk_params,
    )

    state_str = str(response.status.state).upper() if response.status else "UNKNOWN"
    logger.info("SQL initial state: %s", state_str)

    # Polling se pendente
    if "PENDING" in state_str or "RUNNING" in state_str:
        stmt_id = response.statement_id
        for attempt in range(15):
            time.sleep(2)
            response = w.statement_execution.get_statement(stmt_id)
            state_str = str(response.status.state).upper() if response.status else "UNKNOWN"
            logger.info("SQL poll [%d]: %s", attempt, state_str)
            if any(s in state_str for s in ("SUCCEEDED", "FAILED", "CANCEL", "CLOSED")):
                break

    if "FAILED" in state_str:
        err = response.status.error if response.status else None
        err_msg = getattr(err, 'message', str(err)) if err else "Unknown"
        logger.error("SQL FAILED: %s", err_msg)
        raise RuntimeError(f"SQL failed: {err_msg}")

    if "SUCCEEDED" not in state_str:
        logger.error("SQL unexpected state: %s", state_str)
        raise RuntimeError(f"SQL unexpected state: {state_str}")

    logger.info("SQL SUCCEEDED")

    columns = []
    if response.manifest and response.manifest.schema and response.manifest.schema.columns:
        columns = [c.name for c in response.manifest.schema.columns]

    rows = []
    if response.result and response.result.data_array:
        rows = response.result.data_array

    return {"columns": columns, "rows": rows}


def get_rules_table() -> str:
    return _get_rules_table()


def list_all_rules() -> list[dict]:
    table = _get_rules_table()
    data = _execute_sql(
        f"SELECT rule_id, rule_type, category, severity, message_ok, "
        f"message_fail, details_fail, params, enabled, priority "
        f"FROM {table} ORDER BY priority"
    )
    return _rows_to_dicts(data)


def list_enabled_rules() -> list[dict]:
    table = _get_rules_table()
    data = _execute_sql(
        f"SELECT rule_id, rule_type, category, severity, message_ok, "
        f"message_fail, details_fail, params, enabled, priority "
        f"FROM {table} WHERE enabled = TRUE ORDER BY priority"
    )
    return _rows_to_dicts(data)


def insert_rule(rule: dict) -> None:
    """Insere uma nova regra usando parâmetros para evitar problemas de escape."""
    table = _get_rules_table()
    params_json = json.dumps(rule["params"], ensure_ascii=False) if isinstance(rule["params"], dict) else rule["params"]

    sql = (
        f"INSERT INTO {table} "
        f"(rule_id, rule_type, category, severity, message_ok, message_fail, "
        f"details_fail, params, enabled, priority, created_at, updated_at) VALUES "
        f"(:rule_id, :rule_type, :category, :severity, :message_ok, :message_fail, "
        f":details_fail, :params, :enabled, :priority, current_timestamp(), current_timestamp())"
    )

    parameters = [
        {"name": "rule_id", "value": rule["rule_id"]},
        {"name": "rule_type", "value": rule["rule_type"]},
        {"name": "category", "value": rule["category"]},
        {"name": "severity", "value": rule["severity"]},
        {"name": "message_ok", "value": rule.get("message_ok") or ""},
        {"name": "message_fail", "value": rule["message_fail"]},
        {"name": "details_fail", "value": rule.get("details_fail") or ""},
        {"name": "params", "value": params_json},
        {"name": "enabled", "value": str(rule.get("enabled", True)).lower(), "type": "BOOLEAN"},
        {"name": "priority", "value": str(rule.get("priority", 100)), "type": "INT"},
    ]

    logger.info("Inserting rule: %s (type=%s)", rule["rule_id"], rule["rule_type"])
    _execute_sql(sql, parameters)

    # Verifica se realmente inseriu
    if not rule_exists(rule["rule_id"]):
        raise RuntimeError(f"INSERT retornou sucesso mas regra '{rule['rule_id']}' não encontrada na tabela")

    logger.info("Rule %s verified in table", rule["rule_id"])


def update_rule(rule_id: str, fields: dict) -> None:
    table = _get_rules_table()
    sets = []
    params = []
    i = 0

    for key, val in fields.items():
        param_name = f"p{i}"
        if key == "params" and isinstance(val, dict):
            val = json.dumps(val, ensure_ascii=False)

        if isinstance(val, bool):
            sets.append(f"{key} = :{param_name}")
            params.append({"name": param_name, "value": str(val).lower(), "type": "BOOLEAN"})
        elif isinstance(val, (int, float)):
            sets.append(f"{key} = :{param_name}")
            params.append({"name": param_name, "value": str(val), "type": "INT"})
        elif val is None:
            sets.append(f"{key} = NULL")
        else:
            sets.append(f"{key} = :{param_name}")
            params.append({"name": param_name, "value": str(val)})
        i += 1

    sets.append("updated_at = current_timestamp()")
    params.append({"name": "rid", "value": rule_id})

    sql = f"UPDATE {table} SET {', '.join(sets)} WHERE rule_id = :rid"
    logger.info("Updating rule %s: %s", rule_id, sql[:150])
    _execute_sql(sql, params)


def delete_rule(rule_id: str) -> None:
    table = _get_rules_table()
    _execute_sql(
        f"DELETE FROM {table} WHERE rule_id = :rid",
        [{"name": "rid", "value": rule_id}],
    )


def rule_exists(rule_id: str) -> bool:
    table = _get_rules_table()
    data = _execute_sql(
        f"SELECT count(*) FROM {table} WHERE rule_id = :rid",
        [{"name": "rid", "value": rule_id}],
    )
    rows = data.get("rows", [])
    return rows and int(rows[0][0]) > 0


def _rows_to_dicts(data: dict) -> list[dict]:
    columns = data.get("columns", [])
    rows = data.get("rows", [])
    result = []
    for row in rows:
        rule = dict(zip(columns, row))
        try:
            rule["params"] = json.loads(rule["params"]) if isinstance(rule["params"], str) else rule["params"]
        except (json.JSONDecodeError, TypeError):
            rule["params"] = {}
        if isinstance(rule.get("enabled"), str):
            rule["enabled"] = rule["enabled"].lower() in ("true", "1", "yes")
        result.append(rule)
    return result
