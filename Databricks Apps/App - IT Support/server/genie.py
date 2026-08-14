"""Genie Room API integration for 'Sala Chamados IT'."""

import asyncio
import aiohttp
from server.config import get_workspace_host, get_auth_headers

GENIE_SPACE_ID = "01f124528653102d8b5ea6443c331153"


async def _genie_request(method: str, path: str, json_body: dict = None) -> dict:
    host = get_workspace_host()
    url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/{path}"
    headers = {**get_auth_headers(), "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, json=json_body, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"Genie API error ({resp.status}): {text}")
            return await resp.json()


async def start_conversation(question: str) -> dict:
    """Start a new Genie conversation and poll for the answer."""
    data = await _genie_request("POST", "start-conversation", {"content": question})
    conversation_id = data.get("conversation_id", data.get("id", ""))
    message_id = data.get("message_id", "")

    # The response may contain the conversation and message id nested
    if not conversation_id:
        conversation_id = data.get("conversation", {}).get("id", "")
    if not message_id:
        messages = data.get("messages", data.get("conversation", {}).get("messages", []))
        if messages:
            message_id = messages[-1].get("id", "")

    # Poll for result
    result = await poll_message_result(conversation_id, message_id)
    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        **result,
    }


async def post_message(conversation_id: str, question: str) -> dict:
    """Send a follow-up message in an existing conversation."""
    data = await _genie_request(
        "POST",
        f"conversations/{conversation_id}/messages",
        {"content": question},
    )
    message_id = data.get("message_id", data.get("id", ""))
    if not message_id:
        messages = data.get("messages", [])
        if messages:
            message_id = messages[-1].get("id", "")

    result = await poll_message_result(conversation_id, message_id)
    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        **result,
    }


async def poll_message_result(conversation_id: str, message_id: str, max_attempts: int = 60) -> dict:
    """Poll Genie for the message result until completed or failed."""
    for attempt in range(max_attempts):
        data = await _genie_request(
            "GET",
            f"conversations/{conversation_id}/messages/{message_id}",
        )
        status = data.get("status", "")

        if status in ("COMPLETED", "COMPLETED_WITH_ERROR"):
            return _extract_result(data)
        if status in ("FAILED", "CANCELLED"):
            error_msg = data.get("error", {}).get("message", "Genie query failed")
            return {"text": error_msg, "sql": None, "status": status}

        # Wait with backoff: 1s for first 10, then 2s
        await asyncio.sleep(1 if attempt < 10 else 2)

    return {"text": "Timeout waiting for Genie response.", "sql": None, "status": "TIMEOUT"}


def _extract_result(data: dict) -> dict:
    """Extract text and SQL from Genie message response."""
    attachments = data.get("attachments", [])
    text_parts = []
    sql_query = None

    for attachment in attachments:
        # Text attachment: {text: {content: "..."}}
        if attachment.get("text"):
            content = attachment["text"].get("content", "")
            if content:
                text_parts.append(content)

        # Query attachment: {query: {query: "SELECT...", description: "..."}}
        if attachment.get("query"):
            query_info = attachment["query"]
            sql_query = query_info.get("query", query_info.get("sql", ""))
            description = query_info.get("description", "")
            if description:
                text_parts.append(description)

    return {
        "text": "\n\n".join(text_parts) if text_parts else "Sem resposta do Genie.",
        "sql": sql_query,
        "status": data.get("status", "COMPLETED"),
    }


def _format_table(columns: list, rows: list) -> str:
    """Format as a simple markdown table."""
    if not columns:
        return ""
    header = "| " + " | ".join(str(c) for c in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in rows)
    return f"{header}\n{separator}\n{body}"
