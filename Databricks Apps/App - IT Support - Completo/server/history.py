"""Durable, per-user history for the Genie One tab.

The native Genie One thread store has no public list API, so we persist the
conversations the app itself creates (conversation_id + response_id per turn)
in a Unity Catalog table, keyed by the logged-in user's email. This survives
reloads, incognito windows and different devices — unlike browser storage.

Writes/reads run as the app service principal via the SQL Statement Execution
API; rows are scoped by ``user_email`` (from the ``x-forwarded-email`` header).
"""

import os
import aiohttp

from server.config import get_workspace_host, get_auth_headers

TABLE = "cosin_aws_serverless_catalog.it_support.genie_one_history"


def _warehouse_id() -> str:
    return os.environ.get("DATABRICKS_WAREHOUSE_ID", "")


async def _exec(statement: str, parameters: list = None) -> dict:
    """Run a SQL statement on the app's warehouse and return the response."""
    url = f"{get_workspace_host()}/api/2.0/sql/statements"
    headers = {**get_auth_headers(), "Content-Type": "application/json"}
    body = {
        "warehouse_id": _warehouse_id(),
        "statement": statement,
        "wait_timeout": "30s",
    }
    if parameters:
        body["parameters"] = parameters
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise Exception(f"SQL API error ({resp.status}): {data}")
    state = (data.get("status") or {}).get("state")
    if state not in ("SUCCEEDED", "FINISHED"):
        msg = (data.get("status") or {}).get("error", {}).get("message", state)
        raise Exception(f"SQL statement failed: {msg}")
    return data


async def save_turn(user_email: str, conversation_id: str, title: str,
                    question: str, response_id: str) -> None:
    """Persist one Genie One turn for the user."""
    if not user_email or not conversation_id or not response_id:
        return
    await _exec(
        f"INSERT INTO {TABLE} "
        "(user_email, conversation_id, title, question, response_id, turn_ts) "
        "VALUES (:email, :conv, :title, :question, :resp, current_timestamp())",
        parameters=[
            {"name": "email", "value": user_email},
            {"name": "conv", "value": conversation_id},
            {"name": "title", "value": (title or "")[:500]},
            {"name": "question", "value": (question or "")[:2000]},
            {"name": "resp", "value": response_id},
        ],
    )


async def list_history(user_email: str, limit: int = 50) -> list:
    """Return the user's conversations, newest first:
    [{conversationId, title, ts, turns:[{question, responseId}]}].
    """
    if not user_email:
        return []
    data = await _exec(
        "SELECT conversation_id, question, response_id, "
        "CAST(turn_ts AS STRING) AS ts "
        f"FROM {TABLE} WHERE user_email = :email ORDER BY turn_ts ASC",
        parameters=[{"name": "email", "value": user_email}],
    )
    rows = (data.get("result") or {}).get("data_array") or []

    convs = {}
    order = []
    for row in rows:
        conv_id, question, response_id, ts = (row + [None, None, None, None])[:4]
        if conv_id not in convs:
            convs[conv_id] = {
                "conversationId": conv_id,
                "title": question or "(sem título)",
                "ts": ts,
                "turns": [],
            }
            order.append(conv_id)
        convs[conv_id]["turns"].append({"question": question, "responseId": response_id})
        convs[conv_id]["ts"] = ts  # last (latest) turn timestamp

    # newest conversation first (by latest turn)
    result = [convs[c] for c in order]
    result.sort(key=lambda c: c.get("ts") or "", reverse=True)
    return result[:limit]
