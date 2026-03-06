"""Main FastAPI application for Clinical Exam Analysis."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from server.routes.upload import router as upload_router
from server.routes.exames import router as exames_router
from server.routes.pacientes import router as pacientes_router
from server.routes.reset import router as reset_router

app = FastAPI(
    title="Exames Clinicos - Analise de Exames",
    description="App para analise de exames clinicos com IA",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(upload_router)
app.include_router(exames_router)
app.include_router(pacientes_router)
app.include_router(reset_router)

# Health check
@app.get("/api/health")
async def health():
    return {"status": "healthy", "app": "exames-clinicos"}

# Dashboard embed config — token is not passed; the iframe uses the user's Databricks session
@app.get("/api/dashboard-token")
async def dashboard_token():
    from server.config import get_workspace_host
    return {
        "instanceUrl": get_workspace_host(),
        "workspaceId": "7474659847183384",
        "dashboardId": "01f118f425471937b8e9d41ccce94d47",
    }

# Serve React frontend
frontend_dist = Path(__file__).parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Catch-all for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Do not serve SPA for API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        # Check if a static file exists
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Frontend not built yet. Run: cd frontend && npm run build"}
