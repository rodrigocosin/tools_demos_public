"""Genie One integration via the managed Genie MCP server.

Talks to the Databricks-hosted Genie MCP endpoint
(``/api/2.0/mcp/genie/<space_id>``) instead of the raw Conversation API, so
the app reproduces the "Genie One" experience: natural-language answer, the
generated SQL, the resulting data table, and follow-up suggestions.

The MCP server exposes two per-space tools:
  - ``query_space_<space_id>``   -> starts a question (async), returns ids/status
  - ``poll_response_<space_id>`` -> polls until the message reaches a terminal state

Auth note: the Genie MCP server requires *user* authentication (service
principals are not supported). Inside a Databricks App the caller's token is
forwarded on the ``X-Forwarded-Access-Token`` header; we use it when present and
fall back to the app/service-principal token from ``config`` for local dev.
"""

import asyncio
import json
import aiohttp

from server.config import get_workspace_host, get_auth_headers

GENIE_SPACE_ID = "01f124528653102d8b5ea6443c331153"

_QUERY_TOOL = f"query_space_{GENIE_SPACE_ID}"
_POLL_TOOL = f"poll_response_{GENIE_SPACE_ID}"

_TERMINAL_STATES = {"COMPLETED", "COMPLETED_WITH_ERROR", "FAILED", "CANCELLED"}


def _mcp_url() -> str:
    host = get_workspace_host()
    return f"{host}/api/2.0/mcp/genie/{GENIE_SPACE_ID}"


def _genie_one_url() -> str:
    """Workspace-level 'Genie One' MCP server that exposes the interactive
    View tools (view_ask, view_poll_response, ...) and the ui:// resource."""
    return f"{get_workspace_host()}/api/2.0/mcp/genie"


async def relay(body: dict, session_id: str = None, user_token: str = None) -> dict:
    """Transparently relay a JSON-RPC message to the Genie One MCP server.

    Acts as the server side of the MCP Apps host bridge: the browser forwards
    the interactive View's ``tools/call`` / ``resources/read`` (and the initial
    ``initialize``) here, we add auth + the MCP session header, and hand back
    the response plus the (possibly newly issued) session id.

    Returns ``{"session_id": str|None, "body": dict|None}``. ``body`` is None
    for notifications that the server acknowledges with an empty 202.
    """
    url = _genie_one_url()
    headers = _headers(user_token)
    if session_id:
        headers["mcp-session-id"] = session_id
        headers["MCP-Protocol-Version"] = "2025-06-18"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            raw = await resp.text()
            new_sid = resp.headers.get("mcp-session-id") or session_id
            if resp.status >= 400:
                raise Exception(f"Genie MCP error ({resp.status}): {raw}")
            parsed = _parse_mcp_body(raw) if raw.strip() else None
    return {"session_id": new_sid, "body": parsed}


def _headers(user_token: str = None) -> dict:
    """Prefer the forwarded user token (OBO); fall back to the app token."""
    if user_token:
        auth = {"Authorization": f"Bearer {user_token}"}
    else:
        auth = get_auth_headers()
    return {
        **auth,
        "Content-Type": "application/json",
        # MCP streamable-HTTP transport can answer with either a JSON body or an
        # SSE stream; accept both so we work regardless of what the server picks.
        "Accept": "application/json, text/event-stream",
    }


async def _call_tool(session: aiohttp.ClientSession, url: str, headers: dict,
                     name: str, arguments: dict, req_id: int) -> dict:
    """Invoke a single MCP tool and return its ``structuredContent``."""
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    async with session.post(url, json=body, headers=headers) as resp:
        raw = await resp.text()
        if resp.status >= 400:
            raise Exception(f"Genie MCP error ({resp.status}): {raw}")
        payload = _parse_mcp_body(raw)

    if "error" in payload:
        err = payload["error"]
        raise Exception(f"Genie MCP tool error: {err.get('message', err)}")

    result = payload.get("result", {})
    if result.get("isError"):
        raise Exception(f"Genie MCP tool failed: {_text_of(result)}")

    structured = result.get("structuredContent")
    if structured is None:
        # Fall back to the text content block if structuredContent is absent.
        structured = _text_of(result)
        if isinstance(structured, str):
            try:
                structured = json.loads(structured)
            except (ValueError, TypeError):
                structured = {"content": {"textAttachments": [structured]}}
    return structured


def _parse_mcp_body(raw: str) -> dict:
    """Parse an MCP response body that may be plain JSON or an SSE stream."""
    raw = raw.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        return json.loads(raw)
    # SSE framing: one or more "data: {...}" lines. Use the last JSON payload.
    last = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            chunk = line[len("data:"):].strip()
            if chunk and chunk != "[DONE]":
                try:
                    last = json.loads(chunk)
                except ValueError:
                    pass
    return last


def _text_of(result: dict) -> str:
    """Concatenate the plain text content blocks of an MCP tool result."""
    parts = []
    for block in result.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(p for p in parts if p)


async def _genie_api(method: str, path: str, user_token: str = None) -> dict:
    """Call the classic Genie Space REST API (used for conversation history)."""
    url = f"{get_workspace_host()}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/{path}"
    auth = {"Authorization": f"Bearer {user_token}"} if user_token else get_auth_headers()
    headers = {**auth, "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers) as resp:
            raw = await resp.text()
            if resp.status >= 400:
                raise Exception(f"Genie API error ({resp.status}): {raw}")
            return json.loads(raw) if raw.strip() else {}


async def list_conversations(user_token: str = None, page_size: int = 30) -> list:
    """List the caller's conversations for the space (native history)."""
    data = await _genie_api("GET", f"conversations?page_size={page_size}", user_token)
    out = []
    for c in data.get("conversations", []) or []:
        out.append({
            "conversation_id": c.get("conversation_id") or c.get("id"),
            "title": c.get("title") or "(sem título)",
            "created_timestamp": c.get("created_timestamp"),
        })
    return out


async def get_conversation(conversation_id: str, user_token: str = None) -> list:
    """Return a conversation's turns as [{question, text, sql}] (oldest first)."""
    data = await _genie_api("GET", f"conversations/{conversation_id}/messages", user_token)
    messages = data.get("messages", []) or []
    # Order oldest-first when timestamps are available.
    messages.sort(key=lambda m: m.get("created_timestamp") or 0)
    turns = []
    for m in messages:
        mid = m.get("message_id") or m.get("id")
        if not mid:
            continue
        detail = await _genie_api("GET", f"conversations/{conversation_id}/messages/{mid}", user_token)
        parsed = _extract_message(detail)
        turns.append({"question": m.get("content", ""), **parsed})
    return turns


def _extract_message(detail: dict) -> dict:
    """Extract answer text + SQL from a classic Genie message's attachments."""
    text_parts = []
    sql = None
    for att in detail.get("attachments", []) or []:
        if att.get("text") and att["text"].get("content"):
            text_parts.append(att["text"]["content"])
        if att.get("query"):
            q = att["query"]
            if not sql:
                sql = q.get("query") or q.get("sql")
            if q.get("description"):
                text_parts.insert(0, q["description"])
    return {"text": "\n\n".join(p for p in text_parts if p) or "(sem resposta)", "sql": sql}


async def ask(question: str, conversation_id: str = None,
              user_token: str = None, max_attempts: int = 60) -> dict:
    """Ask Genie a question via MCP and poll until it completes.

    Returns a dict with: ``text``, ``sql``, ``columns``, ``rows``,
    ``suggested`` (follow-up questions) and ``conversation_id``.
    """
    url = _mcp_url()
    headers = _headers(user_token)

    async with aiohttp.ClientSession() as session:
        arguments = {"query": question}
        if conversation_id:
            arguments["conversation_id"] = conversation_id

        structured = await _call_tool(session, url, headers, _QUERY_TOOL, arguments, 1)
        conv_id = structured.get("conversationId") or conversation_id
        msg_id = structured.get("messageId", "")
        status = structured.get("status", "")

        attempt = 0
        while status not in _TERMINAL_STATES and attempt < max_attempts:
            await asyncio.sleep(1 if attempt < 10 else 2)
            attempt += 1
            structured = await _call_tool(
                session, url, headers, _POLL_TOOL,
                {"conversation_id": conv_id, "message_id": msg_id}, 2,
            )
            status = structured.get("status", "")

    if status not in _TERMINAL_STATES:
        return {
            "text": "Tempo esgotado aguardando a resposta do Genie.",
            "sql": None, "columns": [], "rows": [],
            "suggested": [], "conversation_id": conv_id, "status": "TIMEOUT",
        }

    result = _extract(structured)
    result["conversation_id"] = conv_id
    result["status"] = status
    return result


def _extract(structured: dict) -> dict:
    """Flatten Genie MCP ``structuredContent`` into a UI-friendly shape."""
    content = structured.get("content", {}) or {}
    text_parts = list(content.get("textAttachments", []) or [])

    sql = None
    columns = []
    rows = []
    for att in content.get("queryAttachments", []) or []:
        description = att.get("description")
        if description:
            text_parts.insert(0, description)
        if not sql and att.get("query"):
            sql = att["query"]
        stmt = att.get("statement_response") or {}
        cols, data = _parse_statement(stmt)
        if cols and not columns:
            columns = cols
            rows = data

    return {
        "text": "\n\n".join(p for p in text_parts if p) or "Sem resposta do Genie.",
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "suggested": list(content.get("suggestedQuestions", []) or []),
    }


def _parse_statement(stmt: dict) -> tuple:
    """Extract (columns, rows) from a SQL Statement Execution response."""
    manifest = stmt.get("manifest", {}) or {}
    schema = manifest.get("schema", {}) or {}
    columns = [c.get("name", f"col_{i}") for i, c in enumerate(schema.get("columns", []) or [])]

    data_array = ((stmt.get("result") or {}).get("data_array")) or []
    rows = [_row_values(row) for row in data_array]
    return columns, rows


def _row_values(row) -> list:
    """Normalize a data_array row to a list of display strings.

    The MCP server wraps cells as ``{"values": [{"string_value": ...}]}`` or,
    depending on the format, returns a plain list of scalars.
    """
    if isinstance(row, dict):
        cells = row.get("values", [])
    else:
        cells = row
    out = []
    for cell in cells or []:
        if isinstance(cell, dict):
            val = (
                cell.get("string_value")
                or cell.get("value")
                or next((v for v in cell.values() if v is not None), "")
            )
            out.append("" if val is None else str(val))
        else:
            out.append("" if cell is None else str(cell))
    return out
