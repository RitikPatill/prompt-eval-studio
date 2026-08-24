# PromptEval Studio

**A lightweight, self-hosted evaluation harness for LLM prompts.**

Define test cases in YAML, run them against OpenAI and Anthropic models in parallel, score outputs with an LLM-as-judge, and inspect results in a minimal web dashboard — all from a single command.

---

## Why it exists

Every serious LLM application eventually needs a regression test suite: *did my latest prompt change break something? Is GPT-4o better than Claude for this task?*

Existing solutions (PromptFoo, RAGAS, etc.) are either too heavy or JavaScript-only. PromptEval Studio fills the gap for Python developers who want something they can drop into any project in five minutes.

---

## How it works

```
YAML test suite
     │
     ▼
┌─────────────┐     parallel API calls     ┌──────────────────┐
│   Runner    │ ─────────────────────────► │  OpenAI / Claude │
└─────────────┘                            └──────────────────┘
     │                                              │
     │  raw outputs                                 │
     ▼                                              │
┌─────────────┐  ◄────────────────────────────────┘
│  LLM Judge  │  scores each output 1-5 with rationale
└─────────────┘
     │
     ▼
┌─────────────┐
│  Dashboard  │  FastAPI + HTMX results table
└─────────────┘
     │
     ▼
 HTML export  (self-contained file for sharing)
```

---

## Features

| Feature | Status |
|---|---|
| Python package scaffold (`src/`, `tests/`, `examples/`) | ✅ M1 |
| Pinned core dependencies (`requirements.txt`) | ✅ M1 |
| YAML test suite format + suite loader | ✅ M2 |
| Multi-model parallel runner (OpenAI + Anthropic, async) | ✅ M2 |
| LLM-as-judge scoring (1–5 + rationale) | ✅ M3 |
| FastAPI + HTMX web dashboard | ✅ M4 |
| HTML report export | ✅ M4 |
| CLI mode (`python main.py run`) with CI exit codes | M5 |

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/ritik/prompt-eval-studio.git
cd prompt-eval-studio

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API keys
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# 5. Run an example suite (available from M2 onwards)
python main.py run --suite examples/qa_suite.yaml

# 6. Open the dashboard (available from M4 onwards)
python main.py serve
# → http://localhost:8000
```

---

## Test suite format (YAML)

Each suite file has a top-level `name` and a list of `test_cases`. See `examples/qa_suite.yaml` for a runnable example.

```yaml
name: basic_qa

test_cases:
  - id: capital_france
    prompt: "What is the capital of {country}?"
    input_variables:
      country: France
    expected_output: Paris          # optional
    rubric: The answer must name Paris as the capital of France.

  - id: python_list_comprehension
    prompt: "Explain Python list comprehensions in one sentence."
    input_variables: {}             # empty is fine
    rubric: The answer should explain list comprehensions concisely.
```

### Loading a suite in Python

```python
from prompt_eval_studio.suite_loader import load_suite
from prompt_eval_studio.runner import run_suite
import asyncio

suite = load_suite("examples/qa_suite.yaml")
results = asyncio.run(run_suite(suite, models=["gpt-4o-mini", "claude-haiku-4-5-20251001"]))
for r in results:
    print(r.model, r.test_case_id, r.latency_ms, r.completion[:60])
```

---

## Scoring outputs with the judge

After running a suite, pass the results through `judge_all` to get structured scores. The judge calls an LLM (OpenAI or Anthropic) with a configurable rubric prompt and returns a `JudgeResult` per run result.

```python
from prompt_eval_studio.suite_loader import load_suite
from prompt_eval_studio.runner import run_suite
from prompt_eval_studio.judge import judge_all
import asyncio

suite = load_suite("examples/qa_suite.yaml")
run_results = asyncio.run(run_suite(suite, models=["gpt-4o-mini", "claude-haiku-4-5-20251001"]))

# Score all outputs in parallel; threshold sets the pass/fail boundary (default: 3)
judge_results = asyncio.run(
    judge_all(run_results, suite, judge_model="claude-haiku-4-5-20251001", threshold=3)
)

for jr in judge_results:
    status = "PASS" if jr.passed else "FAIL"
    print(f"[{status}] {jr.model} / {jr.test_case_id}  score={jr.score}  {jr.rationale}")
```

**`JudgeResult` fields:**

| Field | Type | Description |
|---|---|---|
| `score` | `int` (1–5) | 1 = completely wrong, 5 = fully correct; `0` if the judge itself errored |
| `rationale` | `str` | One-sentence explanation from the judge |
| `passed` | `bool` | `True` when `score >= threshold` |
| `error` | `str \| None` | Set if the runner or judge call failed |

The judge supports any `gpt-*` or `claude-*` model as `judge_model`. Temperature is fixed at 0 for deterministic scoring.

---

## Web dashboard (M4)

Start the dashboard with:

```bash
uvicorn prompt_eval_studio.webapp:app --reload
# → http://localhost:8000
```

The landing page (`GET /`) shows a form where you select a suite YAML path, the models to evaluate, and a pass threshold. On submit the app spawns a background evaluation job and redirects to a live results page that polls every 1.5 s using HTMX. The results table updates in place — showing model × test-case rows with colour-coded score badges (green ≥ 4, yellow = 3, red ≤ 2), latency, and expandable rationale text.

Once evaluation completes, an **Export HTML** button downloads a fully self-contained HTML report (no CDN links) suitable for sharing.

No Node.js or build step required. HTMX is loaded from CDN. All CSS is inline.

---

## Roadmap

| Milestone | Description | Status |
|---|---|---|
| M1 | Scaffold + README | ✅ Done |
| M2 | YAML suite loader + multi-model async runner | ✅ Done |
| M3 | LLM-as-judge scoring | ✅ Done |
| M4 | FastAPI dashboard + HTML export | ✅ Done |
| M5 | CLI entrypoint + CI integration | Pending |

---

## Project structure

```
prompt-eval-studio/
├── src/
│   ├── __init__.py
│   └── prompt_eval_studio/
│       ├── __init__.py       # package root, exposes __version__
│       ├── models.py         # shared dataclasses: TestCase, Suite, RunResult, JudgeResult
│       ├── suite_loader.py   # load_suite(path) -> Suite
│       ├── runner.py         # run_suite(suite, models) -> list[RunResult]
│       ├── judge.py          # judge_result / judge_all -> list[JudgeResult]
│       ├── webapp.py         # FastAPI app: job queue, routes, HTMX polling
│       └── templates/        # Jinja2 templates (base, index, run, fragment, report)
├── tests/
│   ├── __init__.py
│   ├── test_placeholder.py       # smoke test for M1
│   ├── test_suite_loader.py      # YAML parsing and validation
│   ├── test_runner.py            # parallel dispatch, variable rendering, error capture
│   ├── test_judge.py             # judge scoring: pass/fail, malformed JSON, error propagation
│   └── test_webapp.py            # FastAPI routes: index, run submit, status polling, export
├── examples/
│   └── qa_suite.yaml             # runnable 3-case QA example
├── requirements.txt          # pinned: fastapi, uvicorn, openai, anthropic, pyyaml, jinja2, httpx, pytest-asyncio
├── pyproject.toml            # requires-python = ">=3.11", pytest config
├── .gitignore
├── LICENSE
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE).
