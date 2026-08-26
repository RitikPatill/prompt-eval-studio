from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .suite_loader import load_suite
from .runner import run_suite
from .judge import judge_all


def _score_colour(score: int) -> str:
    if score <= 2:
        return "red"
    if score == 3:
        return "yellow"
    return "green"


def _cmd_run(args: argparse.Namespace) -> None:
    suite = load_suite(args.suite)
    run_results = asyncio.run(run_suite(suite, args.models))
    judge_results = asyncio.run(
        judge_all(run_results, suite, judge_model=args.judge, threshold=args.threshold)
    )

    if args.output == "json":
        import json
        output = [
            {
                "test_case_id": jr.test_case_id,
                "model": jr.model,
                "score": jr.score,
                "passed": jr.passed,
                "rationale": jr.rationale,
                "error": jr.error,
            }
            for jr in judge_results
        ]
        print(json.dumps(output, indent=2))
    else:
        console = Console()
        table = Table(title=f"Eval results — {suite.name}", show_lines=True)
        table.add_column("Test Case", style="bold")
        table.add_column("Model")
        table.add_column("Score", justify="center")
        table.add_column("Passed", justify="center")
        table.add_column("Rationale")

        for jr in judge_results:
            colour = _score_colour(jr.score)
            score_text = Text(str(jr.score), style=colour)
            passed_text = Text("✓" if jr.passed else "✗", style="green" if jr.passed else "red")
            rationale = jr.error or jr.rationale
            table.add_row(jr.test_case_id, jr.model, score_text, passed_text, rationale)

        console.print(table)

    any_failed = any(not jr.passed for jr in judge_results)
    if any_failed:
        sys.exit(1)


def _cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn  # lazy import — avoid side-effects in tests

    uvicorn.run(
        "prompt_eval_studio.webapp:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="prompt_eval_studio",
        description="PromptEval Studio — LLM prompt evaluation harness",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- run subcommand --
    run_parser = subparsers.add_parser("run", help="Execute an eval suite and print results")
    run_parser.add_argument("--suite", required=True, metavar="PATH", help="Path to YAML suite file")
    run_parser.add_argument(
        "--models",
        nargs="+",
        default=["gpt-4o-mini"],
        metavar="MODEL",
        help="Models to evaluate (default: gpt-4o-mini)",
    )
    run_parser.add_argument(
        "--judge",
        default="claude-haiku-4-5-20251001",
        metavar="MODEL",
        help="Judge model (default: claude-haiku-4-5-20251001)",
    )
    run_parser.add_argument(
        "--threshold",
        type=int,
        default=3,
        metavar="INT",
        help="Minimum passing score 1-5 (default: 3)",
    )
    run_parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # -- serve subcommand --
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI web dashboard")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "serve":
        _cmd_serve(args)


if __name__ == "__main__":
    main()
