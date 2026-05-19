"""
pipeline.py — Programmatic Python API entry point for Paper2Code-Enhanced.

Phase 4 of the meta-harness integration plan.
Designed to be imported by OrCAID / meta-harness as a Python module,
or invoked directly for scripted multi-paper batch runs.

This module is a thin orchestration layer over the individual stage scripts.
It does NOT re-implement stage logic — it calls the same functions they use.

Usage (programmatic):
    from pipeline import run_pipeline, PipelineConfig, PipelineResult
    config = PipelineConfig(
        paper_name="Transformer",
        pdf_json_path="examples/Transformer_cleaned.json",
        output_dir="outputs/Transformer",
        output_repo_dir="outputs/Transformer_repo",
    )
    result = run_pipeline(config)
    print(result.status, result.output_repo_dir)

Usage (CLI — Phase 3 structured output):
    python pipeline.py \
        --paper_name Transformer \
        --pdf_json_path examples/Transformer_cleaned.json \
        --output_dir outputs/Transformer \
        --output_repo_dir outputs/Transformer_repo \
        --output-format json

TODO(phase-4): Implement run_pipeline() body — call stage functions sequentially,
    capture per-stage results, write to DB, handle stage failures gracefully.
TODO(phase-4): Add --output-format [human|json] CLI arg; emit final JSON to stdout,
    all logging to stderr. This is the meta-harness interop contract.
TODO(phase-4): Add --resume flag that checks DB for an interrupted run with the
    same paper_name + output_dir and skips completed stages.
TODO(phase-4): Add --stages flag to run a subset of stages (e.g. --stages coding,debugging).
TODO(phase-4): Emit a machine-readable final result JSON:
    {
      "stage": "pipeline",
      "status": "success" | "failed",
      "run_id": 42,
      "paper_name": "...",
      "output_dir": "...",
      "output_repo_dir": "...",
      "cost_usd": 0.0,
      "tokens": {"in": 0, "out": 0},
      "stages_completed": ["planning", "analyzing", "coding"],
      "error": null
    }
TODO(phase-4): Register pipeline.py as a console_script entry point in pyproject.toml
    so it's available as `paper2code` on the PATH after pip install.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Config dataclass — single source of truth for a pipeline run
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """All parameters needed to run an end-to-end Paper2Code pipeline."""

    paper_name: str
    pdf_json_path: str
    output_dir: str
    output_repo_dir: str

    # Optional overrides (defaults come from .env)
    model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "MiniMax-M2.7"))
    executor_type: str = field(default_factory=lambda: os.environ.get("EXECUTOR_TYPE", "subprocess"))
    paper_format: Literal["JSON", "LaTeX"] = "JSON"
    pdf_latex_path: str = ""

    # Stage toggles — set False to skip a stage (useful for partial re-runs)
    run_planning: bool = True
    run_analyzing: bool = True
    run_coding: bool = True
    run_debugging: bool = False    # off by default; requires an error file

    # Debugging-specific
    error_file_path: str = ""
    debug_save_num: int = 1

    # Output format for CLI interop
    output_format: Literal["human", "json"] = "human"

    # TODO(phase-4): Add fields for meta-harness task metadata:
    #   task_id: str = ""          # OrCAID task identifier
    #   domain_id: str = ""        # meta-harness domain identifier
    #   experiment_tag: str = ""   # for grouping runs in the DB


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Structured result returned by run_pipeline()."""

    status: Literal["success", "failed", "partial"]
    paper_name: str
    output_dir: str
    output_repo_dir: str
    run_id: int = -1
    stages_completed: list[str] = field(default_factory=list)
    stages_failed: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None

    def to_json(self) -> str:
        return json.dumps({
            "stage": "pipeline",
            "status": self.status,
            "run_id": self.run_id,
            "paper_name": self.paper_name,
            "output_dir": self.output_dir,
            "output_repo_dir": self.output_repo_dir,
            "cost_usd": self.cost_usd,
            "tokens": {"in": self.tokens_in, "out": self.tokens_out},
            "stages_completed": self.stages_completed,
            "stages_failed": self.stages_failed,
            "error": self.error,
        }, indent=2)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """
    Execute the full Paper2Code pipeline for a single paper.

    Returns a PipelineResult regardless of success/failure.
    Writes all stage records to the SQLite DB if available.

    TODO(phase-4): Implement stage orchestration:
        1. init_db() + create_run()
        2. If config.run_planning:   call planning stage, write StageResult
        3. Run 1.1_extract_config.py (config YAML extraction)
        4. If config.run_analyzing:  call analyzing stage, write StageResult
        5. If config.run_coding:     call coding stage, write StageResult
        6. If config.run_debugging:  call debugging stage, write StageResult + ExecutionTrial
        7. complete_run() with final status
        8. Return PipelineResult

    TODO(phase-4): Import stage functions directly rather than subprocess-calling
        the scripts, so the Python API avoids the CLI round-trip overhead.
        This requires refactoring each stage script to expose a run_stage(config) fn.
    """
    # TODO(phase-4): Remove this stub and implement the body above.
    print(
        f"[pipeline] run_pipeline() is not yet implemented.\n"
        f"  paper_name: {config.paper_name}\n"
        f"  model:      {config.model}\n"
        f"  output_dir: {config.output_dir}\n"
        f"Use scripts/run.sh directly until Phase 4 is complete.",
        file=sys.stderr,
    )
    return PipelineResult(
        status="failed",
        paper_name=config.paper_name,
        output_dir=config.output_dir,
        output_repo_dir=config.output_repo_dir,
        error="pipeline.run_pipeline() is not yet implemented (Phase 4 TODO).",
    )


# ---------------------------------------------------------------------------
# CLI interface (Phase 3)
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Paper2Code-Enhanced — end-to-end paper-to-code pipeline."
    )
    parser.add_argument("--paper_name", type=str, required=True)
    parser.add_argument("--pdf_json_path", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--output_repo_dir", type=str, required=True)
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("LLM_MODEL", "MiniMax-M2.7"),
        help="Model override (default: LLM_MODEL from .env)",
    )
    parser.add_argument(
        "--output-format",
        choices=["human", "json"],
        default="human",
        help="'json' emits a single JSON object to stdout; logs go to stderr.",
    )
    parser.add_argument(
        "--stages",
        type=str,
        default="planning,analyzing,coding",
        help="Comma-separated list of stages to run.",
    )
    # TODO(phase-4): Add --resume, --error-file, --debug-save-num, --paper-format flags.
    return parser


def main() -> None:
    """
    CLI entry point.

    TODO(phase-3): Wire this up once run_pipeline() is implemented.
        Until then, this prints a usage hint and exits cleanly.
    """
    parser = _build_arg_parser()
    args = parser.parse_args()

    stages = [s.strip() for s in args.stages.split(",")]
    config = PipelineConfig(
        paper_name=args.paper_name,
        pdf_json_path=args.pdf_json_path,
        output_dir=args.output_dir,
        output_repo_dir=args.output_repo_dir,
        model=args.model,
        run_planning="planning" in stages,
        run_analyzing="analyzing" in stages,
        run_coding="coding" in stages,
        output_format=args.output_format,  # type: ignore[arg-type]
    )

    result = run_pipeline(config)

    if config.output_format == "json":
        print(result.to_json())
    else:
        print(f"[pipeline] status={result.status}  paper={result.paper_name}")
        if result.error:
            print(f"[pipeline] error: {result.error}", file=sys.stderr)

    sys.exit(0 if result.status == "success" else 1)


if __name__ == "__main__":
    main()
