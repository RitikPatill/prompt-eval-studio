# PromptEval Studio


> **Video walkthrough:** https://youtu.be/oLaIZTfdlc8
> **60-second overview:** https://youtu.be/8tbVENTGs2w

> A local web tool to run, judge, and compare LLM prompt test suites — evals-as-code with an LLM-as-judge scorer.

<!-- TODO: replace with a 5-10 second demo gif. Record with ScreenToGif on
     Windows or peek on macOS. Save to docs/demo.gif and update path here. -->
![demo](docs/demo.gif)

## What it is

PromptEval Studio is a self-hosted evaluation harness for LLM prompts. You define test cases in plain YAML, run them against any combination of OpenAI and Anthropic models in parallel, and score each output with a configurable LLM-as-judge that returns a 1–5 score and a one-sentence rationale. Results appear in a minimal FastAPI + HTMX dashboard — no build step, no Node.

It exists because every serious LLM application eventually needs a regression suite: did my latest prompt change break something? Is GPT-4o better than Claude for this task? Existing solutions are either too heavy or JavaScript-only. PromptEval Studio is the five-minute Python alternative.

## Quickstart

```bash
git clone https://github.com/RitikPatill/prompt-eval-studio.git
cd prompt-eval-studio

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Run the example suite from the terminal
PYTHONPATH=src python -m prompt_eval_studio run --suite examples/qa_suite.yaml

# Or launch the web dashboard
PYTHONPATH=src python -m prompt_eval_studio serve
# then open http://localhost:8000
```

## Usage

**CLI mode** — useful in CI pipelines:

```bash
# Compare two models, require score >= 4 to pass
PYTHONPATH=src python -m prompt_eval_studio run \
  --suite examples/qa_suite.yaml \
  --models gpt-4o-mini claude-haiku-4-5-20251001 \
  --threshold 4

# Exit code 0 = all cases passed, 1 = at least one score below threshold
```

**Web dashboard** — for interactive exploration:

1. Run `make dev` and open `http://localhost:8000`.
2. Enter a suite path, pick one or more models, set a pass threshold, and click **Run Eval**.
3. The results table populates in real time via HTMX polling — score badges (green/yellow/red), latency, and expandable rationale per cell.
4. Click **Export HTML** to download a self-contained report for sharing.

**YAML suite format:**

```yaml
name: basic_qa

test_cases:
  - id: capital_france
    prompt: "What is the capital of {country}?"
    input_variables:
      country: France
    expected_output: Paris
    rubric: The answer must name Paris as the capital of France.
```

## Architecture

```
YAML suite file
     │
     ▼
suite_loader.py          parse + validate test cases
     │
     ▼
runner.py ──────────►  OpenAI API   ┐
     │          └──►  Anthropic API ┘  (parallel async)
     ▼
judge.py ───────────►  LLM judge (any gpt-* or claude-* model)
     │                 returns score 1–5 + rationale per result
     ▼
┌─────────────┐     ┌─────────────────────┐
│ CLI / stdout│     │ FastAPI + HTMX UI   │
│ rich table  │     │ + HTML report export│
└─────────────┘     └─────────────────────┘
```

## Project structure

```
prompt-eval-studio/
├── src/prompt_eval_studio/   core package
│   ├── __main__.py           CLI entrypoint: run / serve subcommands
│   ├── models.py             shared dataclasses: TestCase, RunResult, JudgeResult
│   ├── suite_loader.py       YAML parsing and validation
│   ├── runner.py             parallel async model dispatch
│   ├── judge.py              LLM-as-judge scoring
│   ├── webapp.py             FastAPI app, job queue, HTMX polling routes
│   └── templates/            Jinja2 templates (index, results, report)
├── tests/                    pytest suite — loader, runner, judge, webapp, CLI
├── examples/
│   └── qa_suite.yaml         runnable 3-case QA example
├── Makefile                  make dev / make test
├── requirements.txt          pinned dependencies
└── pyproject.toml            requires-python = ">=3.11"
```

## Roadmap

- [ ] Support local models via Ollama (OpenAI-compatible endpoint)
- [ ] Diff view: highlight score changes between two suite runs
- [ ] Persistent run history stored in SQLite
- [ ] GitHub Actions workflow template for CI eval gating
- [ ] Configurable judge prompt per suite

## License

MIT — see [LICENSE](LICENSE).

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
