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
| YAML test suite format | M2 |
| Multi-model parallel execution (OpenAI + Anthropic) | M3 |
| LLM-as-judge scoring (1–5 + rationale) | M3 |
| FastAPI + HTMX web dashboard | M4 |
| HTML report export | M4 |
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
python main.py run --suite examples/sentiment_suite.yaml

# 6. Open the dashboard (available from M4 onwards)
python main.py serve
# → http://localhost:8000
```

---

## Test suite format (M2)

```yaml
suite_name: sentiment_analysis
models:
  - gpt-4o-mini
  - claude-haiku-4-5

cases:
  - name: positive_review
    prompt: "Classify the sentiment of the following text: {text}"
    input_variables:
      text: "I absolutely loved this product!"
    expected_output: "positive"
    rubric: "Output must be one of: positive, negative, neutral."

  - name: ambiguous_review
    prompt: "Classify the sentiment of the following text: {text}"
    input_variables:
      text: "It arrived on time."
    rubric: "Output must be one of: positive, negative, neutral. Ambiguous cases should be neutral."
```

---

## Roadmap

| Milestone | Description | Status |
|---|---|---|
| M1 | Scaffold + README | ✅ Done |
| M2 | YAML parser + test suite schema | Pending |
| M3 | Multi-model runner + LLM judge | Pending |
| M4 | FastAPI dashboard + HTML export | Pending |
| M5 | CLI entrypoint + CI integration | Pending |

---

## Project structure

```
prompt-eval-studio/
├── src/
│   ├── __init__.py
│   └── prompt_eval_studio/
│       └── __init__.py       # package root, exposes __version__
├── tests/
│   ├── __init__.py
│   └── test_placeholder.py   # smoke test for M1
├── examples/
│   └── README.md             # example suites live here from M2
├── requirements.txt          # pinned: fastapi, uvicorn, openai, anthropic, pyyaml, jinja2, httpx
├── pyproject.toml            # requires-python = ">=3.11", pytest config
├── .gitignore
├── LICENSE
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE).
