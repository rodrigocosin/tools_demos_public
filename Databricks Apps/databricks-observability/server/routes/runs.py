"""Runs API routes."""

from fastapi import APIRouter, Query, Request
from typing import Optional
from server.config import get_workspace_client
from server.routes.jobs import _serialize_run

router = APIRouter(prefix="/api", tags=["runs"])


def _client(request: Request):
    token = request.headers.get("X-Forwarded-Access-Token")
    return get_workspace_client(user_token=token)


@router.get("/runs")
async def list_runs(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by state"),
    job_id: Optional[int] = Query(None, description="Filter by job_id"),
    limit: int = Query(50, description="Max runs"),
):
    """List recent runs across all jobs."""
    w = _client(request)
    kwargs = {"expand_tasks": True}
    if job_id:
        kwargs["job_id"] = job_id

    runs = []
    count = 0
    for run in w.jobs.list_runs(**kwargs):
        run_dict = _serialize_run(run)
        if status and run_dict["state"] != status.upper():
            continue
        runs.append(run_dict)
        count += 1
        if count >= limit:
            break
    return {"runs": runs, "total": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: int):
    """Get full details for a single run including tasks and parameters."""
    w = _client(request)
    run = w.jobs.get_run(run_id=run_id)
    return _serialize_run(run)
