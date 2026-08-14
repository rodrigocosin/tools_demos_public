"""Databricks Observability Dashboard - FastAPI entry point."""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.routes.jobs import router as jobs_router
from server.routes.runs import router as runs_router
from server.config import get_workspace_client, IS_DATABRICKS_APP


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Databricks Observability Dashboard starting...")
    print(f"IS_DATABRICKS_APP={IS_DATABRICKS_APP}")
    yield
    print("Shutting down.")


app = FastAPI(title="Databricks Observability", lifespan=lifespan)

app.include_router(jobs_router)
app.include_router(runs_router)


@app.get("/api/debug")
async def debug(request: Request):
    """Debug endpoint - shows auth context and API connectivity."""
    token = request.headers.get("X-Forwarded-Access-Token")
    all_headers = {k: v[:20] + "..." if len(v) > 20 else v
                   for k, v in request.headers.items()
                   if k.lower() not in ("cookie", "authorization")}
    app_token = os.environ.get("APP_DATABRICKS_TOKEN")
    result = {
        "is_databricks_app": IS_DATABRICKS_APP,
        "has_forwarded_token": bool(token),
        "forwarded_token_prefix": token[:20] + "..." if token else None,
        "has_app_databricks_token": bool(app_token),
        "app_token_prefix": app_token[:10] + "..." if app_token else None,
        "headers": all_headers,
        "databricks_host_env": os.environ.get("DATABRICKS_HOST"),
        "jobs": [],
        "error": None,
    }
    try:
        w = get_workspace_client(user_token=token)
        for job in w.jobs.list(expand_tasks=False):
            result["jobs"].append({"job_id": job.job_id, "name": job.settings.name if job.settings else None})
    except Exception as e:
        result["error"] = str(e)
    return result

# Serve React frontend
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        return {"message": "Frontend not built. Run: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
