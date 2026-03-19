"""Jobs API routes."""

from fastapi import APIRouter, Query, Request
from typing import Optional
from server.config import get_workspace_client

router = APIRouter(prefix="/api", tags=["jobs"])


def _client(request: Request):
    token = request.headers.get("X-Forwarded-Access-Token")
    return get_workspace_client(user_token=token)


@router.get("/jobs")
async def list_jobs(
    request: Request,
    name: Optional[str] = Query(None, description="Filter by job name (substring match)"),
    limit: int = Query(100, description="Max jobs to return"),
):
    """List all jobs with latest run status."""
    w = _client(request)

    # Fetch latest run state per job (2 calls: active + recent completed)
    latest_run_per_job: dict = {}
    for run in w.jobs.list_runs(active_only=True, expand_tasks=False):
        jid = run.job_id
        latest_run_per_job[jid] = {"state": _get_run_state(run), "run_id": run.run_id, "start_time": run.start_time, "params": _extract_params(run)}
    scanned = 0
    for run in w.jobs.list_runs(expand_tasks=False):
        jid = run.job_id
        if jid not in latest_run_per_job:
            latest_run_per_job[jid] = {"state": _get_run_state(run), "run_id": run.run_id, "start_time": run.start_time, "params": _extract_params(run)}
        scanned += 1
        if scanned >= 500:
            break

    jobs = []
    count = 0
    for job in w.jobs.list(expand_tasks=False):
        job_dict = {
            "job_id": job.job_id,
            "name": job.settings.name if job.settings else f"Job {job.job_id}",
            "created_time": job.created_time,
            "creator_user_name": getattr(job, "creator_user_name", None),
            "latest_run": latest_run_per_job.get(job.job_id),
        }
        if name and name.lower() not in job_dict["name"].lower():
            continue
        jobs.append(job_dict)
        count += 1
        if count >= limit:
            break
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/jobs/{job_id}/runs")
async def get_job_runs(
    request: Request,
    job_id: int,
    limit: int = Query(25, description="Max runs to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get all runs for a specific job, including parameters."""
    w = _client(request)
    runs = []
    count = 0
    for run in w.jobs.list_runs(job_id=job_id, expand_tasks=True):
        run_dict = _serialize_run(run)
        if status and run_dict["state"] != status.upper():
            continue
        runs.append(run_dict)
        count += 1
        if count >= limit:
            break
    return {"runs": runs, "job_id": job_id, "total": len(runs)}


@router.get("/stats")
async def get_stats(request: Request):
    """Get summary statistics scoped to existing jobs only (excludes deleted jobs)."""
    w = _client(request)

    # Scope all counts to currently existing jobs — excludes runs from deleted jobs
    existing_job_ids = {job.job_id for job in w.jobs.list(expand_tasks=False)}
    total_jobs = len(existing_job_ids)

    running = 0
    pending = 0
    for run in w.jobs.list_runs(active_only=True, expand_tasks=False):
        if run.job_id not in existing_job_ids:
            continue
        state = _get_run_state(run)
        if state == "RUNNING":
            running += 1
        elif state in ("PENDING", "QUEUED", "BLOCKED"):
            pending += 1

    failed = 0
    success = 0
    total_runs = 0
    scanned = 0
    for run in w.jobs.list_runs(completed_only=True, expand_tasks=False):
        scanned += 1
        if run.job_id in existing_job_ids:
            total_runs += 1
            state = _get_run_state(run)
            if state == "FAILED":
                failed += 1
            elif state == "SUCCESS":
                success += 1
        if scanned >= 500:
            break

    return {
        "total_jobs": total_jobs,
        "total_runs": total_runs + running + pending,
        "running": running,
        "failed": failed,
        "success": success,
        "pending": pending,
    }


@router.get("/jobs/tasks")
async def list_jobs_tasks(request: Request):
    """List all jobs with their configured task definitions (job settings, not run tasks)."""
    w = _client(request)
    jobs_tasks = []
    for job in w.jobs.list(expand_tasks=True):
        tasks = []
        if job.settings and job.settings.tasks:
            for t in job.settings.tasks:
                task_type = "unknown"
                for attr in ("notebook_task", "spark_jar_task", "spark_python_task",
                             "python_wheel_task", "dbt_task", "sql_task", "pipeline_task",
                             "run_job_task", "spark_submit_task"):
                    if getattr(t, attr, None):
                        task_type = attr.replace("_task", "")
                        break
                tasks.append({
                    "task_key": t.task_key,
                    "task_type": task_type,
                    "depends_on": [d.task_key for d in (t.depends_on or [])],
                    "description": getattr(t, "description", None),
                })
        jobs_tasks.append({
            "job_id": job.job_id,
            "name": job.settings.name if job.settings else f"Job {job.job_id}",
            "creator_user_name": getattr(job, "creator_user_name", None),
            "tasks": tasks,
        })
    return {"jobs": jobs_tasks, "total": len(jobs_tasks)}


@router.get("/runs/active")
async def list_active_runs(request: Request):
    """List all currently active (running/pending) runs, enriched with job names."""
    w = _client(request)
    # Build job name map upfront
    job_names = {
        job.job_id: (job.settings.name if job.settings else f"Job {job.job_id}")
        for job in w.jobs.list(expand_tasks=False)
    }
    runs = []
    for run in w.jobs.list_runs(active_only=True, expand_tasks=True):
        r = _serialize_run(run)
        r["job_name"] = job_names.get(run.job_id, f"Job {run.job_id}")
        runs.append(r)
    return {"runs": runs, "total": len(runs)}


def _get_run_state(run) -> str:
    """Extract meaningful state from a run object."""
    if run.state:
        if run.state.life_cycle_state:
            lcs = str(run.state.life_cycle_state.value) if hasattr(run.state.life_cycle_state, "value") else str(run.state.life_cycle_state)
            if lcs in ("RUNNING", "PENDING", "BLOCKED", "QUEUED"):
                return lcs
            if lcs in ("TERMINATED", "TERMINATING"):
                if run.state.result_state:
                    rs = str(run.state.result_state.value) if hasattr(run.state.result_state, "value") else str(run.state.result_state)
                    return rs
                return "TERMINATED"
            if lcs == "SKIPPED":
                return "SKIPPED"
            if lcs == "INTERNAL_ERROR":
                return "FAILED"
            return lcs
    return "UNKNOWN"


def _extract_params(run) -> dict:
    """Extract all parameter types from a run."""
    params = {}
    if hasattr(run, "overriding_parameters") and run.overriding_parameters:
        op = run.overriding_parameters
        if hasattr(op, "jar_params") and op.jar_params:
            params["jar_params"] = list(op.jar_params)
        if hasattr(op, "notebook_params") and op.notebook_params:
            params["notebook_params"] = dict(op.notebook_params)
        if hasattr(op, "python_params") and op.python_params:
            params["python_params"] = list(op.python_params)
        if hasattr(op, "spark_submit_params") and op.spark_submit_params:
            params["spark_submit_params"] = list(op.spark_submit_params)
        if hasattr(op, "python_named_params") and op.python_named_params:
            params["python_named_params"] = dict(op.python_named_params)
        if hasattr(op, "pipeline_params") and op.pipeline_params:
            params["pipeline_params"] = str(op.pipeline_params)
        if hasattr(op, "sql_params") and op.sql_params:
            params["sql_params"] = dict(op.sql_params)
    if hasattr(run, "job_parameters") and run.job_parameters:
        params["job_parameters"] = [
            {"name": p.name, "default": p.default, "value": p.value}
            for p in run.job_parameters
        ] if hasattr(run.job_parameters[0], "name") else run.job_parameters
    if hasattr(run, "repair_history") and run.repair_history:
        params["has_repairs"] = True
    return params


def _serialize_task(task) -> dict:
    """Serialize a task object."""
    state = "UNKNOWN"
    if task.state:
        if task.state.life_cycle_state:
            lcs = str(task.state.life_cycle_state.value) if hasattr(task.state.life_cycle_state, "value") else str(task.state.life_cycle_state)
            if lcs in ("RUNNING", "PENDING", "BLOCKED", "QUEUED"):
                state = lcs
            elif lcs in ("TERMINATED", "TERMINATING"):
                if task.state.result_state:
                    rs = str(task.state.result_state.value) if hasattr(task.state.result_state, "value") else str(task.state.result_state)
                    state = rs
                else:
                    state = "TERMINATED"
            elif lcs == "INTERNAL_ERROR":
                state = "FAILED"
            elif lcs == "SKIPPED":
                state = "SKIPPED"
            else:
                state = lcs
    duration_ms = None
    if task.execution_duration:
        duration_ms = task.execution_duration
    elif task.start_time and task.end_time:
        duration_ms = task.end_time - task.start_time

    return {
        "task_key": task.task_key,
        "state": state,
        "start_time": task.start_time,
        "end_time": getattr(task, "end_time", None),
        "duration_ms": duration_ms,
        "attempt_number": getattr(task, "attempt_number", 0),
        "description": getattr(task, "description", None),
    }


def _serialize_run(run) -> dict:
    """Serialize a run object to dict."""
    state = _get_run_state(run)
    params = _extract_params(run)

    duration_ms = None
    if hasattr(run, "execution_duration") and run.execution_duration:
        duration_ms = run.execution_duration
    elif run.start_time and run.end_time:
        duration_ms = run.end_time - run.start_time

    tasks = []
    if hasattr(run, "tasks") and run.tasks:
        tasks = [_serialize_task(t) for t in run.tasks]

    state_message = None
    if run.state and hasattr(run.state, "state_message"):
        state_message = run.state.state_message

    return {
        "run_id": run.run_id,
        "job_id": run.job_id,
        "run_name": getattr(run, "run_name", None),
        "state": state,
        "state_message": state_message,
        "start_time": run.start_time,
        "end_time": getattr(run, "end_time", None),
        "duration_ms": duration_ms,
        "params": params,
        "tasks": tasks,
        "run_page_url": getattr(run, "run_page_url", None),
        "trigger": str(run.trigger.value) if hasattr(run, "trigger") and run.trigger and hasattr(run.trigger, "value") else str(getattr(run, "trigger", None)),
    }
