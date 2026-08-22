from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestCase:
    id: str
    prompt: str
    input_variables: dict[str, str]
    rubric: str
    expected_output: str | None = None


@dataclass
class Suite:
    name: str
    test_cases: list[TestCase]


@dataclass
class RunResult:
    suite_name: str
    test_case_id: str
    model: str
    prompt_rendered: str
    completion: str
    latency_ms: float
    error: str | None = None
