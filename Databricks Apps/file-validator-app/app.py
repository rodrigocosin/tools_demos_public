"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.db import init_tables
from server.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if needed
    try:
        init_tables()
        print("Database tables initialized.")
    except Exception as e:
        print(f"Warning: Could not initialize tables: {e}")
    yield


app = FastAPI(title="File Validator", lifespan=lifespan)
app.include_router(router)

# Serve React frontend
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    # Serve static assets (js, css, images)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't catch API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404
        # Try to serve the exact file first
        file_path = frontend_dist / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Default: serve index.html for SPA routing
        return FileResponse(str(frontend_dist / "index.html"))
