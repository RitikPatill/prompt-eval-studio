"""Tests for the CLI run subcommand (no real API calls)."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from prompt_eval_studio.models import JudgeResult, RunResult, Suite, TestCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_suite() -> Suite:
    return Suite(
        name="test_suite",
        test_cases=[
            TestCase(
                id="tc1",
                prompt="What is 2+2?",
                input_variables={},
                rubric="Answer must be 4.",
                expected_output="4",
            )
        ],
    )


def _make_run_result(suite: Suite) -> list[RunResult]:
    return [
        RunResult(
            suite_name=suite.name,
            test_case_id="tc1",
            model="gpt-4o-mini",
            prompt_rendered="What is 2+2?",
            completion="4",
            latency_ms=100.0,
            error=None,
        )
    ]


def _make_judge_result(passed: bool) -> list[JudgeResult]:
    return [
        JudgeResult(
            suite_name="test_suite",
            test_case_id="tc1",
            model="gpt-4o-mini",
            score=5 if passed else 1,
            rationale="Correct." if passed else "Wrong.",
            passed=passed,
            error=None,
        )
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_exits_zero_when_all_pass(monkeypatch, capsys):
    suite = _make_suite()
    run_results = _make_run_result(suite)
    judge_results = _make_judge_result(passed=True)

    monkeypatch.setattr(sys, "argv", ["prog", "run", "--suite", "fake.yaml"])

    with (
        patch("prompt_eval_studio.__main__.load_suite", return_value=suite),
        patch("prompt_eval_studio.__main__.run_suite", new=AsyncMock(return_value=run_results)),
        patch("prompt_eval_studio.__main__.judge_all", new=AsyncMock(return_value=judge_results)),
    ):
        from prompt_eval_studio.__main__ import main

        # Should not raise SystemExit (implicit exit 0)
        try:
            main()
        except SystemExit as exc:
            assert exc.code == 0 or exc.code is None, f"Expected exit 0, got {exc.code}"


def test_run_exits_one_when_any_fail(monkeypatch):
    suite = _make_suite()
    run_results = _make_run_result(suite)
    judge_results = _make_judge_result(passed=False)

    monkeypatch.setattr(sys, "argv", ["prog", "run", "--suite", "fake.yaml"])

    with (
        patch("prompt_eval_studio.__main__.load_suite", return_value=suite),
        patch("prompt_eval_studio.__main__.run_suite", new=AsyncMock(return_value=run_results)),
        patch("prompt_eval_studio.__main__.judge_all", new=AsyncMock(return_value=judge_results)),
    ):
        from prompt_eval_studio.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_run_passes_threshold_to_judge(monkeypatch):
    suite = _make_suite()
    run_results = _make_run_result(suite)
    judge_results = _make_judge_result(passed=True)

    monkeypatch.setattr(sys, "argv", ["prog", "run", "--suite", "fake.yaml", "--threshold", "4"])

    mock_judge_all = AsyncMock(return_value=judge_results)

    with (
        patch("prompt_eval_studio.__main__.load_suite", return_value=suite),
        patch("prompt_eval_studio.__main__.run_suite", new=AsyncMock(return_value=run_results)),
        patch("prompt_eval_studio.__main__.judge_all", new=mock_judge_all),
    ):
        from prompt_eval_studio.__main__ import main

        try:
            main()
        except SystemExit:
            pass

        _, kwargs = mock_judge_all.call_args
        assert kwargs.get("threshold") == 4


def test_run_default_model(monkeypatch):
    suite = _make_suite()
    run_results = _make_run_result(suite)
    judge_results = _make_judge_result(passed=True)

    # Omit --models
    monkeypatch.setattr(sys, "argv", ["prog", "run", "--suite", "fake.yaml"])

    mock_run_suite = AsyncMock(return_value=run_results)

    with (
        patch("prompt_eval_studio.__main__.load_suite", return_value=suite),
        patch("prompt_eval_studio.__main__.run_suite", new=mock_run_suite),
        patch("prompt_eval_studio.__main__.judge_all", new=AsyncMock(return_value=judge_results)),
    ):
        from prompt_eval_studio.__main__ import main

        try:
            main()
        except SystemExit:
            pass

        _, kwargs = mock_run_suite.call_args
        # run_suite is called as run_suite(suite, args.models) — positional
        args_positional = mock_run_suite.call_args[0]
        assert args_positional[1] == ["gpt-4o-mini"]
