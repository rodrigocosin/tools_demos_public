import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from server.config import get_workspace_host, get_auth_headers
from server.genie import start_conversation, post_message, poll_message_result
from server.knowledge import query_knowledge_agent
from server.supervisor import query_supervisor
import json

app = FastAPI(title="IT Support Workshop")

# --- Models ---

class GenieRequest(BaseModel):
    question: str
    conversation_id: str = None

class KnowledgeRequest(BaseModel):
    question: str

class SupervisorRequest(BaseModel):
    question: str

# --- API Routes ---

@app.get("/api/health")
async def health():
    return {"status": "healthy"}


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
