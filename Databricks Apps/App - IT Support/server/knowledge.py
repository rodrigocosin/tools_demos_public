"""Knowledge Agent (RAG) endpoint integration."""

import aiohttp
import json
from server.config import get_workspace_host, get_auth_headers

KA_ENDPOINT = "ka-1a0b7165-endpoint"


async def query_knowledge_agent(question: str, stream: bool = False):
    """Query the Knowledge Agent RAG endpoint."""
    host = get_workspace_host()
    url = f"{host}/serving-endpoints/{KA_ENDPOINT}/invocations"
    headers = {**get_auth_headers(), "Content-Type": "application/json"}
    payload = {
        "input": [{"role": "user", "content": question}],
    }

    if stream:
        payload["stream"] = True
        return _stream_response(url, headers, payload)
    else:
        return await _single_response(url, headers, payload)


async def _single_response(url: str, headers: dict, payload: dict) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"Knowledge Agent error ({resp.status}): {text}")
            data = await resp.json()

    # Databricks Agent Framework format:
    # {"output": [{"type": "message", "content": [{"type": "output_text", "text": "..."}]}]}
    output_items = data.get("output", [])
    if output_items and isinstance(output_items, list):
        for item in output_items:
            if item.get("type") == "message":
                parts = []
                for chunk in item.get("content", []):
                    if chunk.get("type") == "output_text" and chunk.get("text", "").strip():
                        parts.append(chunk["text"].strip())
                if parts:
                    return {"answer": "\n\n".join(parts)}

    # OpenAI-compatible format
    choices = data.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if content:
            return {"answer": content}

    return {"answer": "Sem resposta."}


async def _stream_response(url: str, headers: dict, payload: dict):
    """Yield streaming chunks from the KA endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"Knowledge Agent error ({resp.status}): {text}")

            buffer = ""
            async for chunk in resp.content.iter_any():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            return
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield {"content": content}
                        except json.JSONDecodeError:
                            pass
                    else:
                        # Try parsing as raw JSON
                        try:
                            data = json.loads(line)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield {"content": content}
                        except json.JSONDecodeError:
                            pass
