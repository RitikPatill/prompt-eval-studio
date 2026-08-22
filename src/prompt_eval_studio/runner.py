from __future__ import annotations

import asyncio
import time

import anthropic
import openai

from .models import RunResult, Suite, TestCase


async def _call_model(
    rendered_prompt: str,
    model: str,
    test_case_id: str,
    suite_name: str,
    openai_client: openai.AsyncOpenAI,
    anthropic_client: anthropic.AsyncAnthropic,
) -> RunResult:
    start = time.perf_counter()
    try:
        if model.startswith("gpt-"):
            response = await openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": rendered_prompt}],
                max_tokens=512,
                temperature=0,
            )
            completion = response.choices[0].message.content or ""
        elif model.startswith("claude-"):
            response = await anthropic_client.messages.create(
                model=model,
                messages=[{"role": "user", "content": rendered_prompt}],
                max_tokens=512,
                temperature=0,
            )
            completion = response.content[0].text
        else:
            raise ValueError(f"Unsupported model: {model}")

        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            suite_name=suite_name,
            test_case_id=test_case_id,
            model=model,
            prompt_rendered=rendered_prompt,
            completion=completion,
            latency_ms=latency_ms,
            error=None,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            suite_name=suite_name,
            test_case_id=test_case_id,
            model=model,
            prompt_rendered=rendered_prompt,
            completion="",
            latency_ms=latency_ms,
            error=str(exc),
        )


async def run_suite(suite: Suite, models: list[str]) -> list[RunResult]:
    """Run all test cases in a suite against all specified models in parallel."""
    openai_client = openai.AsyncOpenAI()
    anthropic_client = anthropic.AsyncAnthropic()

    async def _error_result(tc: TestCase, model: str, error: str) -> RunResult:
        return RunResult(
            suite_name=suite.name,
            test_case_id=tc.id,
            model=model,
            prompt_rendered=tc.prompt,
            completion="",
            latency_ms=0.0,
            error=error,
        )

    tasks = []
    for test_case in suite.test_cases:
        try:
            rendered_prompt = test_case.prompt.format(**test_case.input_variables)
        except KeyError as exc:
            for model in models:
                tasks.append(_error_result(test_case, model, f"Missing template variable: {exc}"))
            continue
        for model in models:
            tasks.append(
                _call_model(
                    rendered_prompt=rendered_prompt,
                    model=model,
                    test_case_id=test_case.id,
                    suite_name=suite.name,
                    openai_client=openai_client,
                    anthropic_client=anthropic_client,
                )
            )

    results: list[RunResult] = await asyncio.gather(*tasks)
    return results
