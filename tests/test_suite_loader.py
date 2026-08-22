import pytest

from prompt_eval_studio.suite_loader import load_suite


def _write_yaml(tmp_path, content: str):
    p = tmp_path / "suite.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_valid_suite(tmp_path):
    yaml_content = """
name: test_suite
test_cases:
  - id: case_1
    prompt: "What is {x}?"
    input_variables:
      x: life
    expected_output: "42"
    rubric: Must mention 42.
  - id: case_2
    prompt: "Hello world."
    rubric: Should greet.
"""
    path = _write_yaml(tmp_path, yaml_content)
    suite = load_suite(path)

    assert suite.name == "test_suite"
    assert len(suite.test_cases) == 2

    first = suite.test_cases[0]
    assert first.id == "case_1"
    assert first.prompt == "What is {x}?"
    assert first.input_variables == {"x": "life"}
    assert first.expected_output == "42"
    assert first.rubric == "Must mention 42."


def test_missing_name(tmp_path):
    yaml_content = """
test_cases:
  - id: case_1
    prompt: "Hello"
    rubric: "Say hello."
"""
    path = _write_yaml(tmp_path, yaml_content)
    with pytest.raises(ValueError, match="name"):
        load_suite(path)


def test_missing_rubric(tmp_path):
    yaml_content = """
name: suite
test_cases:
  - id: case_1
    prompt: "Hello"
"""
    path = _write_yaml(tmp_path, yaml_content)
    with pytest.raises(ValueError, match="rubric"):
        load_suite(path)


def test_defaults(tmp_path):
    yaml_content = """
name: suite
test_cases:
  - id: case_1
    prompt: "Hello world."
    rubric: "Should say hello."
"""
    path = _write_yaml(tmp_path, yaml_content)
    suite = load_suite(path)

    case = suite.test_cases[0]
    assert case.input_variables == {}
    assert case.expected_output is None
