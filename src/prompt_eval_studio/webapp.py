from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from .judge import judge_all
from .models import JudgeResult, RunResult
from .runner import run_suite
from .suite_loader import load_suite

app = FastAPI(title="PromptEval Studio")

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

AVAILABLE_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
]


@dataclass
class JobState:
    status: Literal["running", "done", "error"]
    suite_name: str
    models: list[str]
    judge_results: list[JudgeResult] = field(default_factory=list)
    run_results: list[RunResult] = field(default_factory=list)
    error: str | None = None


# In-memory job store — asyncio is single-threaded, no locking needed
jobs: dict[str, JobState] = {}


async def _render_template(template_response: HTMLResponse) -> bytes:
    """Render a Starlette TemplateResponse to bytes."""
    messages: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    await template_response(scope, receive, send)
    for msg in messages:
        if msg.get("type") == "http.response.body":
            return msg.get("body", b"")
    return b""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"models": AVAILABLE_MODELS},
    )


@app.post("/run")
async def post_run(
    suite_path: str = Form(...),
    models: list[str] = Form(default=[]),
    threshold: int = Form(default=3),
) -> RedirectResponse:
    if not models:
        models = [AVAILABLE_MODELS[0]]

    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState(
        status="running",
        suite_name=suite_path,
        models=models,
    )
    asyncio.create_task(_run_job(job_id, suite_path, models, threshold))
    return RedirectResponse(url=f"/run/{job_id}", status_code=303)


@app.get("/run/{job_id}", response_class=HTMLResponse)
async def run_page(request: Request, job_id: str) -> HTMLResponse:
    job = jobs.get(job_id)
    if job is None:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)
    return templates.TemplateResponse(
        request,
        "run.html",
        {"job_id": job_id, "suite_name": job.suite_name},
    )


@app.get("/run/{job_id}/status")
async def run_status(request: Request, job_id: str) -> Response:
    job = jobs.get(job_id)
    if job is None:
        return HTMLResponse("<p>Job not found</p>", status_code=404)

    template_response = templates.TemplateResponse(
        request,
        "results_fragment.html",
        {"job": job, "job_id": job_id},
    )
    body = await _render_template(template_response)

    response_headers: dict[str, str] = {}
    if job.status == "done":
        response_headers["HX-Trigger"] = "jobDone"

    return Response(content=body, media_type="text/html", headers=response_headers)


@app.get("/export/{job_id}/html")
async def export_html(request: Request, job_id: str) -> Response:
    job = jobs.get(job_id)
    if job is None:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    template_response = templates.TemplateResponse(
        request,
        "report.html",
        {"job": job, "job_id": job_id},
    )
    body = await _render_template(template_response)

    return Response(
        content=body,
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename=report_{job_id[:8]}.html"
        },
    )


async def _run_job(
    job_id: str,
    suite_path: str,
    models: list[str],
    threshold: int,
) -> None:
    try:
        suite = await asyncio.to_thread(load_suite, suite_path)
        jobs[job_id].suite_name = suite.name

        run_results = await run_suite(suite, models)
        jobs[job_id].run_results = run_results

        judge_results = await judge_all(run_results, suite, threshold=threshold)
        jobs[job_id].judge_results = judge_results
        jobs[job_id].status = "done"
    except Exception as exc:
        jobs[job_id].status = "error"
        jobs[job_id].error = str(exc)
