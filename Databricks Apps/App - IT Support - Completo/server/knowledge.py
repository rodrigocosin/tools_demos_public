"""Knowledge Agent (RAG) endpoint integration."""

import asyncio
import aiohttp
import json
import re
from server.config import get_workspace_host, get_auth_headers

KA_ENDPOINT = "ka-1a0b7165-endpoint"

# The KA agent intermittently returns "no info" without citations — usually
# because its internal retrieval call hit a rate limit (429) or the agent
# skipped the search. Retry with backoff until we get a sourced answer.
MAX_RETRIEVAL_ATTEMPTS = 4


def _extract_references(content_chunks: list) -> list:
    """Extract source citations from output_text annotations (url_citation).

    The Knowledge Assistant embeds references as annotations on each
    output_text chunk, e.g.:
        {"type": "url_citation", "url": "...", "title": "arquivo.pdf"}
    Page numbers, when present, come as a dedicated field or in the url
    (e.g. ...#page=3).
    """
    refs = []
    seen = set()
    for chunk in content_chunks:
        for ann in chunk.get("annotations") or []:
            if ann.get("type") not in ("url_citation", "citation", "file_citation"):
                continue
            url = ann.get("url") or ann.get("doc_uri") or ""
            title = (
                ann.get("title")
                or ann.get("filename")
                or ann.get("doc_title")
                or (url.rstrip("/").split("/")[-1] if url else "")
                or "Documento"
            )
            page = ann.get("page") or ann.get("page_number")
            if page is None and url:
                m = re.search(r"[#?&]page=(\d+)", url)
                if m:
                    page = int(m.group(1))
            key = (title, page)
            if key in seen:
                continue
            seen.add(key)
            refs.append({"title": title, "url": url or None, "page": page})
    return refs


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

    # Retry until we get a sourced answer. Tolerate per-attempt failures
    # (e.g. 429 rate limits from the agent's internal retrieval) and back off
    # between attempts so transient throttling has time to clear.
    last = None
    last_error = None
    for attempt in range(MAX_RETRIEVAL_ATTEMPTS):
        if attempt:
            await asyncio.sleep(min(2 ** attempt * 0.5, 4.0))  # 1s, 2s, 4s
        try:
            last = await _single_response(url, headers, payload)
        except Exception as e:  # noqa: BLE001 — retry on any transient error
            last_error = e
            continue
        if last.get("references"):
            return last
    if last is not None:
        return last
    if last_error is not None:
        raise last_error
    return {"answer": "Sem resposta.", "references": []}


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
                content_chunks = item.get("content", [])
                parts = [
                    chunk["text"].strip()
                    for chunk in content_chunks
                    if chunk.get("type") == "output_text" and chunk.get("text", "").strip()
                ]
                if parts:
                    return {
                        "answer": "\n\n".join(parts),
                        "references": _extract_references(content_chunks),
                    }

    # OpenAI-compatible format
    choices = data.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if content:
            return {"answer": content, "references": []}

    return {"answer": "Sem resposta.", "references": []}


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
