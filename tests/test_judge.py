from unittest.mock import AsyncMock, MagicMock

import pytest

from prompt_eval_studio.judge import judge_all, judge_result
from prompt_eval_studio.models import JudgeResult, RunResult, Suite, TestCase


def _make_run_result(
    test_case_id: str = "tc1",
    completion: str = "Paris is the capital of France.",
    error: str | None = None,
) -> RunResult:
    return RunResult(
        suite_name="test_suite",
        test_case_id=test_case_id,
        model="claude-haiku-4-5-20251001",
        prompt_rendered="What is the capital of France?",
        completion=completion,
        latency_ms=100.0,
        error=error,
    )


def _make_test_case(tc_id: str = "tc1") -> TestCase:
    return TestCase(
        id=tc_id,
        prompt="What is the capital of {country}?",
        input_variables={"country": "France"},
        rubric="Must say Paris.",
        expected_output="Paris",
    )


def _make_anthropic_judge_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


@pytest.mark.asyncio
async def test_judge_pass(monkeypatch):
    """score=4, threshold=3 → passed=True, fields populated."""
    anthropic_create = AsyncMock(
        return_value=_make_anthropic_judge_response(
            '{"score": 4, "rationale": "Correctly identifies Paris."}'
        )
    )
    anthropic_instance = MagicMock()
    anthropic_instance.messages.create = anthropic_create

    monkeypatch.setattr("prompt_eval_studio.judge.anthropic.AsyncAnthropic", lambda: anthropic_instance)
    monkeypatch.setattr("prompt_eval_studio.judge.openai.AsyncOpenAI", lambda: MagicMock())

    result = await judge_result(
        _make_run_result(),
        _make_test_case(),
        judge_model="claude-haiku-4-5-20251001",
        threshold=3,
    )

    assert isinstance(result, JudgeResult)
    assert result.score == 4
    assert result.rationale == "Correctly identifies Paris."
    assert result.passed is True
    assert result.error is None
    anthropic_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_judge_fail_threshold(monkeypatch):
    """score=2, threshold=3 → passed=False."""
    anthropic_create = AsyncMock(
        return_value=_make_anthropic_judge_response(
            '{"score": 2, "rationale": "Mostly incorrect."}'
        )
    )
    anthropic_instance = MagicMock()
    anthropic_instance.messages.create = anthropic_create

    monkeypatch.setattr("prompt_eval_studio.judge.anthropic.AsyncAnthropic", lambda: anthropic_instance)
    monkeypatch.setattr("prompt_eval_studio.judge.openai.AsyncOpenAI", lambda: MagicMock())

    result = await judge_result(
        _make_run_result(),
        _make_test_case(),
        judge_model="claude-haiku-4-5-20251001",
        threshold=3,
    )

    assert result.score == 2
    assert result.passed is False
    assert result.error is None


@pytest.mark.asyncio
async def test_judge_error_run_result_skipped(monkeypatch):
    """run_result.error set → no API call, JudgeResult.error propagated."""
    anthropic_create = AsyncMock()
    anthropic_instance = MagicMock()
    anthropic_instance.messages.create = anthropic_create

    monkeypatch.setattr("prompt_eval_studio.judge.anthropic.AsyncAnthropic", lambda: anthropic_instance)
    monkeypatch.setattr("prompt_eval_studio.judge.openai.AsyncOpenAI", lambda: MagicMock())

    run_result = _make_run_result(error="API down")
    result = await judge_result(run_result, _make_test_case(), judge_model="claude-haiku-4-5-20251001")

    assert result.score == 0
    assert result.passed is False
    assert result.error == "API down"
    anthropic_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_judge_malformed_json(monkeypatch):
    """mock returns 'not json' → JudgeResult.error set, score=0."""
    anthropic_create = AsyncMock(
        return_value=_make_anthropic_judge_response("not json")
    )
    anthropic_instance = MagicMock()
    anthropic_instance.messages.create = anthropic_create

    monkeypatch.setattr("prompt_eval_studio.judge.anthropic.AsyncAnthropic", lambda: anthropic_instance)
    monkeypatch.setattr("prompt_eval_studio.judge.openai.AsyncOpenAI", lambda: MagicMock())

    result = await judge_result(
        _make_run_result(),
        _make_test_case(),
        judge_model="claude-haiku-4-5-20251001",
    )

    assert result.score == 0
    assert result.passed is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_judge_all_parallel(monkeypatch):
    """2 RunResults × 1 model → 2 JudgeResults, API called twice."""
    anthropic_create = AsyncMock(
        return_value=_make_anthropic_judge_response(
            '{"score": 5, "rationale": "Perfect answer."}'
        )
    )
    anthropic_instance = MagicMock()
    anthropic_instance.messages.create = anthropic_create

    monkeypatch.setattr("prompt_eval_studio.judge.anthropic.AsyncAnthropic", lambda: anthropic_instance)
    monkeypatch.setattr("prompt_eval_studio.judge.openai.AsyncOpenAI", lambda: MagicMock())

    suite = Suite(
        name="test_suite",
        test_cases=[_make_test_case("tc1"), _make_test_case("tc2")],
    )
    run_results = [
        _make_run_result(test_case_id="tc1"),
        _make_run_result(test_case_id="tc2"),
    ]

    results = await judge_all(
        run_results,
        suite,
        judge_model="claude-haiku-4-5-20251001",
        threshold=3,
    )

    assert len(results) == 2
    assert all(isinstance(r, JudgeResult) for r in results)
    assert all(r.score == 5 for r in results)
    assert all(r.passed is True for r in results)
    assert anthropic_create.await_count == 2
