from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from prompt_eval_studio.models import JudgeResult, RunResult, Suite, TestCase
from prompt_eval_studio.webapp import JobState, app, jobs


@pytest_asyncio.fixture(autouse=True)
async def clear_jobs():
    """Reset job store before each test."""
    jobs.clear()
    yield
    jobs.clear()


@pytest.mark.asyncio
async def test_index_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "<form" in response.text


@pytest.mark.asyncio
async def test_post_run_redirects():
    async def _fake_run_job(*args, **kwargs):
        pass

    with patch("prompt_eval_studio.webapp._run_job", side_effect=_fake_run_job):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as client:
            response = await client.post(
                "/run",
                data={"suite_path": "examples/qa_suite.yaml", "models": "gpt-4o-mini", "threshold": "3"},
            )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/run/")


@pytest.mark.asyncio
async def test_status_running():
    job_id = "test-job-running-001"
    jobs[job_id] = JobState(
        status="running",
        suite_name="test_suite",
        models=["gpt-4o-mini"],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/run/{job_id}/status")

    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers


@pytest.mark.asyncio
async def test_status_done():
    job_id = "test-job-done-001"
    jr = JudgeResult(
        suite_name="test_suite",
        test_case_id="tc1",
        model="gpt-4o-mini",
        score=4,
        rationale="Good answer.",
        passed=True,
    )
    rr = RunResult(
        suite_name="test_suite",
        test_case_id="tc1",
        model="gpt-4o-mini",
        prompt_rendered="Hello world",
        completion="Hi there!",
        latency_ms=123.4,
    )
    jobs[job_id] = JobState(
        status="done",
        suite_name="test_suite",
        models=["gpt-4o-mini"],
        judge_results=[jr],
        run_results=[rr],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/run/{job_id}/status")

    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "jobDone"
    assert "score-high" in response.text or "4/5" in response.text


@pytest.mark.asyncio
async def test_export_html():
    job_id = "test-job-export-001"
    jr = JudgeResult(
        suite_name="test_suite",
        test_case_id="tc1",
        model="gpt-4o-mini",
        score=5,
        rationale="Perfect.",
        passed=True,
    )
    rr = RunResult(
        suite_name="test_suite",
        test_case_id="tc1",
        model="gpt-4o-mini",
        prompt_rendered="What is 2+2?",
        completion="4",
        latency_ms=88.0,
    )
    jobs[job_id] = JobState(
        status="done",
        suite_name="test_suite",
        models=["gpt-4o-mini"],
        judge_results=[jr],
        run_results=[rr],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/export/{job_id}/html")

    assert response.status_code == 200
    content_disp = response.headers.get("content-disposition", "")
    assert "attachment" in content_disp
    assert "report_" in content_disp
    # Self-contained: no external CSS or HTMX references
    assert "<style>" in response.text
    assert "htmx" not in response.text.lower()
