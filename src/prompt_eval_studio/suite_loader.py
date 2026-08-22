from __future__ import annotations

from pathlib import Path

import yaml

from .models import Suite, TestCase


def load_suite(path: str | Path) -> Suite:
    """Parse and validate a YAML test suite file, returning a Suite dataclass."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Suite YAML must be a mapping at the top level.")

    if "name" not in data:
        raise ValueError("Suite YAML missing required key: 'name'.")
    if "test_cases" not in data:
        raise ValueError("Suite YAML missing required key: 'test_cases'.")

    name = data["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Suite 'name' must be a non-empty string.")

    raw_cases = data["test_cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("'test_cases' must be a list.")

    test_cases: list[TestCase] = []
    for i, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise ValueError(f"test_cases[{i}] must be a mapping.")

        for required_key in ("id", "prompt", "rubric"):
            if required_key not in raw:
                raise ValueError(
                    f"test_cases[{i}] missing required key: '{required_key}'."
                )
            if not isinstance(raw[required_key], str) or not raw[required_key].strip():
                raise ValueError(
                    f"test_cases[{i}].{required_key} must be a non-empty string."
                )

        input_variables = raw.get("input_variables") or {}
        if not isinstance(input_variables, dict):
            raise ValueError(f"test_cases[{i}].input_variables must be a mapping.")

        test_cases.append(
            TestCase(
                id=raw["id"],
                prompt=raw["prompt"],
                input_variables=input_variables,
                rubric=raw["rubric"],
                expected_output=raw.get("expected_output"),
            )
        )

    return Suite(name=name, test_cases=test_cases)
