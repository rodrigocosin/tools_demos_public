import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from server.config import get_workspace_host, get_auth_headers
from server.genie import start_conversation, post_message, poll_message_result
from server.genie_mcp import (
    ask as genie_mcp_ask,
    relay as genie_mcp_relay,
    list_conversations as genie_mcp_list_conversations,
    get_conversation as genie_mcp_get_conversation,
)
from server.knowledge import query_knowledge_agent
from server.supervisor import query_supervisor
from server.history import save_turn as history_save_turn, list_history
import json

app = FastAPI(title="IT Support Workshop")

# --- Models ---

class GenieRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class GenieMcpRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class GenieMcpRpcRequest(BaseModel):
    session_id: Optional[str] = None
    body: dict

class HistorySaveRequest(BaseModel):
    conversation_id: str
    response_id: str
    question: str
    title: Optional[str] = None


def _user_email(request: Request) -> str:
    return (
        request.headers.get("x-forwarded-email")
        or request.headers.get("x-forwarded-user")
        or ""
    )

class KnowledgeRequest(BaseModel):
    question: str

class SupervisorRequest(BaseModel):
    question: str

# --- API Routes ---

@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/whoami")
async def whoami(request: Request):
    """Diagnostic: is the user's OBO token being forwarded, and as whom?

    Decodes the (JWT) x-forwarded-access-token locally without extra API calls,
    so it works regardless of the token's scopes. Use it to confirm that
    'User authorization' + the 'genie' scope are enabled on the app.
    """
    import base64

    token = request.headers.get("x-forwarded-access-token")
    if not token:
        return {"obo_forwarded": False,
                "detail": "x-forwarded-access-token ausente — habilite 'User authorization' no app."}

    claims = {}
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        pass

    return {
        "obo_forwarded": True,
        "subject": claims.get("sub"),
        "scope": claims.get("scope"),
        "client_id": claims.get("client_id"),
    }


@app.post("/api/genie")
async def genie(req: GenieRequest):
    """Start or continue a Genie conversation."""
    try:
        if req.conversation_id:
            result = await post_message(req.conversation_id, req.question)
        else:
            result = await start_conversation(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/genie-mcp")
async def genie_mcp(req: GenieMcpRequest, request: Request):
    """Ask Genie One through the managed Genie MCP server.

    The Genie MCP endpoint requires user authentication, so we forward the
    caller's identity token (injected by Databricks Apps on
    ``X-Forwarded-Access-Token``) when it is present.
    """
    try:
        user_token = request.headers.get("x-forwarded-access-token")
        result = await genie_mcp_ask(
            req.question,
            conversation_id=req.conversation_id,
            user_token=user_token,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/genie-mcp/conversations")
async def genie_mcp_conversations(request: Request):
    """List the logged-in user's Genie conversations (native history, via OBO)."""
    try:
        user_token = request.headers.get("x-forwarded-access-token")
        conversations = await genie_mcp_list_conversations(user_token=user_token)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/genie-mcp/conversations/{conversation_id}")
async def genie_mcp_conversation(conversation_id: str, request: Request):
    """Return a past conversation's turns (question + answer + SQL)."""
    try:
        user_token = request.headers.get("x-forwarded-access-token")
        turns = await genie_mcp_get_conversation(conversation_id, user_token=user_token)
        return {"turns": turns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/genie-mcp/history")
async def genie_mcp_history(request: Request):
    """Return the user's saved Genie One conversations (durable, per-user)."""
    try:
        conversations = await list_history(_user_email(request))
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/genie-mcp/history")
async def genie_mcp_history_save(req: HistorySaveRequest, request: Request):
    """Persist one Genie One turn for the logged-in user."""
    try:
        await history_save_turn(
            _user_email(request),
            req.conversation_id,
            req.title or req.question,
            req.question,
            req.response_id,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/genie-mcp/rpc")
async def genie_mcp_rpc(req: GenieMcpRpcRequest, request: Request):
    """Bridge relay for the Genie One interactive View (MCP Apps host).

    The browser forwards the View iframe's JSON-RPC messages here; we attach
    the user's forwarded token and the MCP session id and pass them to the
    Genie One MCP server.
    """
    try:
        user_token = request.headers.get("x-forwarded-access-token")
        return await genie_mcp_relay(req.body, session_id=req.session_id, user_token=user_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge")
async def knowledge_query(req: KnowledgeRequest):
    """Query the Knowledge Agent (RAG) endpoint."""
    try:
        result = await query_knowledge_agent(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/supervisor")
async def supervisor_query(req: SupervisorRequest):
    """Query the Multi-Agent Supervisor (Genie + KA)."""
    try:
        result = await query_supervisor(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge/stream")
async def knowledge_query_stream(req: KnowledgeRequest):
    """Query the Knowledge Agent with streaming response."""
    try:
        async def generate():
            async for chunk in query_knowledge_agent(req.question, stream=True):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Serve React frontend ---

frontend_dist = Path(__file__).parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
