from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prompt_eval_studio.models import RunResult, Suite, TestCase
from prompt_eval_studio.runner import run_suite


def _make_suite(cases: list[TestCase]) -> Suite:
    return Suite(name="test_suite", test_cases=cases)


def _make_openai_response(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_anthropic_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


@pytest.fixture()
def mock_clients(monkeypatch):
    openai_create = AsyncMock(return_value=_make_openai_response("openai answer"))
    anthropic_create = AsyncMock(return_value=_make_anthropic_response("claude answer"))

    openai_instance = MagicMock()
    openai_instance.chat.completions.create = openai_create

    anthropic_instance = MagicMock()
    anthropic_instance.messages.create = anthropic_create

    monkeypatch.setattr("prompt_eval_studio.runner.openai.AsyncOpenAI", lambda: openai_instance)
    monkeypatch.setattr("prompt_eval_studio.runner.anthropic.AsyncAnthropic", lambda: anthropic_instance)

    return openai_create, anthropic_create


async def test_run_returns_results_shape(mock_clients):
    suite = _make_suite([
        TestCase(
            id="q1",
            prompt="What is the capital of {country}?",
            input_variables={"country": "France"},
            rubric="Must say Paris.",
        )
    ])

    results = await run_suite(suite, ["gpt-4o-mini", "claude-haiku-4-5-20251001"])

    assert len(results) == 2
    models_returned = {r.model for r in results}
    assert "gpt-4o-mini" in models_returned
    assert "claude-haiku-4-5-20251001" in models_returned

    for r in results:
        assert isinstance(r, RunResult)
        assert r.completion != ""
        assert r.latency_ms > 0
        assert r.error is None


async def test_variable_substitution(mock_clients):
    suite = _make_suite([
        TestCase(
            id="q1",
            prompt="Hello, {name}!",
            input_variables={"name": "Alice"},
            rubric="Must greet Alice.",
        )
    ])

    results = await run_suite(suite, ["gpt-4o-mini"])

    assert len(results) == 1
    assert results[0].prompt_rendered == "Hello, Alice!"
    assert "{name}" not in results[0].prompt_rendered


async def test_error_captured(monkeypatch):
    openai_instance = MagicMock()
    openai_instance.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))

    monkeypatch.setattr("prompt_eval_studio.runner.openai.AsyncOpenAI", lambda: openai_instance)
    monkeypatch.setattr("prompt_eval_studio.runner.anthropic.AsyncAnthropic", lambda: MagicMock())

    suite = _make_suite([
        TestCase(
            id="q1",
            prompt="Hello world.",
            input_variables={},
            rubric="Should say hello.",
        )
    ])

    results = await run_suite(suite, ["gpt-4o-mini"])

    assert len(results) == 1
    assert results[0].error is not None
    assert results[0].completion == ""
