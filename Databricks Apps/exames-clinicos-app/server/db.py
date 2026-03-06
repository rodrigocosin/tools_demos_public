"""Database operations via Databricks SQL Statement Execution API."""
import json
import time
from typing import Any, Optional
import aiohttp

from server.config import get_workspace_host, get_token, get_warehouse_id, CATALOG, SCHEMA


FULL_TABLE = lambda table: f"{CATALOG}.{SCHEMA}.{table}"


async def execute_sql(
    sql: str, parameters: Optional[list] = None
) -> dict:
    """Execute SQL against Databricks SQL Warehouse and return results."""
    host = get_workspace_host()
    token = get_token()
    warehouse_id = get_warehouse_id()

    url = f"{host}/api/2.0/sql/statements"
    payload: dict[str, Any] = {
        "warehouse_id": warehouse_id,
        "statement": sql,
        "wait_timeout": "50s",
    }
    if parameters:
        payload["parameters"] = parameters

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"SQL API error ({resp.status}): {error_text[:500]}")
            data = await resp.json()

        state = data.get("status", {}).get("state", "UNKNOWN")
        stmt_id = data.get("statement_id", "")

        # Poll if still running
        retries = 0
        while state in ("PENDING", "RUNNING") and retries < 60:
            await _async_sleep(3)
            poll_url = f"{host}/api/2.0/sql/statements/{stmt_id}"
            async with session.get(poll_url, headers=headers) as poll_resp:
                data = await poll_resp.json()
            state = data.get("status", {}).get("state", "UNKNOWN")
            retries += 1

        if state == "FAILED":
            err = data.get("status", {}).get("error", {}).get("message", "Unknown")
            raise Exception(f"SQL execution failed: {err}")

        return data


async def _async_sleep(seconds: int):
    import asyncio
    await asyncio.sleep(seconds)


def parse_results(data: dict) -> list[dict]:
    """Parse SQL statement execution results into list of dicts."""
    manifest = data.get("manifest", {})
    schema = manifest.get("schema", {})
    columns = schema.get("columns", [])
    col_names = [c["name"] for c in columns]

    result = data.get("result", {})
    rows_raw = result.get("data_array", [])

    rows = []
    for row in rows_raw:
        row_dict = {}
        for i, col_name in enumerate(col_names):
            row_dict[col_name] = row[i] if i < len(row) else None
        rows.append(row_dict)

    return rows


async def query(sql: str) -> list[dict]:
    """Execute SQL and return parsed rows."""
    data = await execute_sql(sql)
    return parse_results(data)


async def execute(sql: str) -> dict:
    """Execute SQL without parsing results (for INSERT/UPDATE/DDL)."""
    return await execute_sql(sql)
