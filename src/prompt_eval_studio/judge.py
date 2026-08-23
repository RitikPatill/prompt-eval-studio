from __future__ import annotations

import asyncio
import json

import anthropic
import openai

from .models import JudgeResult, RunResult, Suite, TestCase

JUDGE_PROMPT_TEMPLATE = """\
You are an impartial evaluator of LLM outputs.

## Prompt given to the model
{prompt}

## Model output
{completion}

## Evaluation rubric
{rubric}
{expected_block}
Score the output on a scale of 1–5:
  1 = Completely wrong or irrelevant
  2 = Mostly wrong, minor relevant elements
  3 = Partially correct with significant gaps
  4 = Mostly correct with minor issues
  5 = Fully correct and well-formed

Respond with ONLY a JSON object, no markdown fences:
{{"score": <integer 1-5>, "rationale": "<one concise sentence>"}}\
"""


async def _call_judge(
    user_message: str,
    judge_model: str,
    openai_client: openai.AsyncOpenAI,
    anthropic_client: anthropic.AsyncAnthropic,
) -> str:
    """Raw LLM call; returns the completion string. Raises on API error."""
    if judge_model.startswith("gpt-"):
        response = await openai_client.chat.completions.create(
            model=judge_model,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=256,
            temperature=0,
        )
        return response.choices[0].message.content or ""
    elif judge_model.startswith("claude-"):
        response = await anthropic_client.messages.create(
            model=judge_model,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=256,
            temperature=0,
        )
        return response.content[0].text
    else:
        raise ValueError(f"Unsupported judge model: {judge_model}")


def _parse_judge_response(raw: str) -> tuple[int, str]:
    """Extract (score, rationale) from the LLM JSON response."""
    text = raw.strip()
    # Strip markdown fences if present
    if "{" in text:
        text = text[text.index("{") : text.rindex("}") + 1]
    data = json.loads(text)
    score = data["score"]
    rationale = data["rationale"]
    if not isinstance(score, int) or score < 1 or score > 5:
        raise ValueError(f"Score out of range: {score!r}")
    if not isinstance(rationale, str) or not rationale:
        raise ValueError("Rationale must be a non-empty string")
    return score, rationale


async def judge_result(
    run_result: RunResult,
    test_case: TestCase,
    judge_model: str = "claude-haiku-4-5-20251001",
    threshold: int = 3,
    *,
    openai_client: openai.AsyncOpenAI | None = None,
    anthropic_client: anthropic.AsyncAnthropic | None = None,
) -> JudgeResult:
    """Score a single RunResult. Short-circuits if run_result.error is set."""
    if run_result.error is not None:
        return JudgeResult(
            suite_name=run_result.suite_name,
            test_case_id=run_result.test_case_id,
            model=run_result.model,
            score=0,
            rationale="",
            passed=False,
            error=run_result.error,
        )

    if openai_client is None:
        openai_client = openai.AsyncOpenAI()
    if anthropic_client is None:
        anthropic_client = anthropic.AsyncAnthropic()

    expected_block = (
        f"## Expected output\n{test_case.expected_output}\n"
        if test_case.expected_output is not None
        else ""
    )
    user_message = JUDGE_PROMPT_TEMPLATE.format(
        prompt=run_result.prompt_rendered,
        completion=run_result.completion,
        rubric=test_case.rubric,
        expected_block=expected_block,
    )

    try:
        raw = await _call_judge(user_message, judge_model, openai_client, anthropic_client)
        score, rationale = _parse_judge_response(raw)
    except Exception as exc:
        return JudgeResult(
            suite_name=run_result.suite_name,
            test_case_id=run_result.test_case_id,
            model=run_result.model,
            score=0,
            rationale="",
            passed=False,
            error=str(exc),
        )

    return JudgeResult(
        suite_name=run_result.suite_name,
        test_case_id=run_result.test_case_id,
        model=run_result.model,
        score=score,
        rationale=rationale,
        passed=score >= threshold,
        error=None,
    )


async def judge_all(
    run_results: list[RunResult],
    suite: Suite,
    judge_model: str = "claude-haiku-4-5-20251001",
    threshold: int = 3,
) -> list[JudgeResult]:
    """Score all RunResults in parallel."""
    case_map = {tc.id: tc for tc in suite.test_cases}
    oa_client = openai.AsyncOpenAI()
    an_client = anthropic.AsyncAnthropic()

    async def _judge_one(rr: RunResult) -> JudgeResult:
        tc = case_map.get(rr.test_case_id)
        if tc is None:
            return JudgeResult(
                suite_name=rr.suite_name,
                test_case_id=rr.test_case_id,
                model=rr.model,
                score=0,
                rationale="",
                passed=False,
                error="TestCase not found",
            )
        return await judge_result(
            rr,
            tc,
            judge_model=judge_model,
            threshold=threshold,
            openai_client=oa_client,
            anthropic_client=an_client,
        )

    return list(await asyncio.gather(*[_judge_one(rr) for rr in run_results]))
