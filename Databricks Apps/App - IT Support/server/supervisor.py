"""Multi-Agent Supervisor endpoint integration (Genie + KA)."""

import aiohttp
from server.config import get_workspace_host, get_auth_headers

SUPERVISOR_ENDPOINT = "mas-3754ad3f-endpoint"


async def query_supervisor(question: str) -> dict:
    host = get_workspace_host()
    url = f"{host}/serving-endpoints/{SUPERVISOR_ENDPOINT}/invocations"
    headers = {**get_auth_headers(), "Content-Type": "application/json"}
    payload = {"input": [{"role": "user", "content": question}]}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"Supervisor error ({resp.status}): {text}")
            data = await resp.json()

    return {"answer": _extract_final_answer(data)}


def _extract_final_answer(data: dict) -> str:
    """Extract the final supervisor answer from the MAS response."""
    output_items = data.get("output", [])
    # Find the last completed assistant message with meaningful text
    last_text = ""
    for item in output_items:
        if item.get("type") == "message" and item.get("role") == "assistant":
            for chunk in item.get("content", []):
                if chunk.get("type") == "output_text":
                    text = chunk.get("text", "").strip()
                    # Skip internal routing markers like <name>...</name>
                    if text and not (text.startswith("<name>") and text.endswith("</name>")):
                        last_text = text
    return last_text or "Sem resposta."
