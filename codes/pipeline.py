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
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

try:
    from db import init_db, create_run, complete_run, get_run_summary
except ImportError:
    from codes.db import init_db, create_run, complete_run, get_run_summary


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

    # Resume flag
    resume: bool = False

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
# Dynamic module loader
# ---------------------------------------------------------------------------

def load_stage_module(name: str, filename: str):
    """Dynamically loads a stage script module from the same directory as pipeline.py."""
    import importlib.util
    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir_path, filename)
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec for {name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """
    Execute the full Paper2Code pipeline for a single paper.

    Returns a PipelineResult regardless of success/failure.
    Writes all stage records to the SQLite DB if available.
    """
    try:
        init_db(quiet=True)
    except Exception as e:
        print(f"[pipeline] Warning: Database initialization failed: {e}", file=sys.stderr)

    # 1. Create or resume DB run
    run_id = -1
    try:
        run_id = create_run(
            paper_name=config.paper_name,
            model_used=config.model,
            output_dir=config.output_dir,
            executor_type=config.executor_type,
        )
    except Exception as e:
        print(f"[pipeline] Warning: Database run creation failed: {e}", file=sys.stderr)

    # Inject run_id into config if it was dynamically created
    if run_id > 0:
        config.run_id = run_id

    completed_stages = []
    stages_to_skip = set()

    if config.resume and run_id > 0:
        try:
            summary = get_run_summary(run_id)
            if summary and "stages" in summary:
                for s in summary["stages"]:
                    if s["success"]:
                        stages_to_skip.add(s["stage_name"])
        except Exception as e:
            print(f"[pipeline] Warning: failed to query stage success for resume: {e}", file=sys.stderr)

    # 2. Run planning stage
    if config.run_planning:
        current_stage = "planning"
        if current_stage in stages_to_skip:
            print(f"[pipeline] Stage '{current_stage}' already completed. Skipping.", file=sys.stderr)
            completed_stages.append(current_stage)
        else:
            print(f"[pipeline] Executing planning stage (in-memory)...", file=sys.stderr)
            try:
                planning = load_stage_module("planning", "1_planning.py")
                planning.run_stage(config)
                completed_stages.append(current_stage)
            except Exception as e:
                print(f"❌ Stage '{current_stage}' failed: {e}", file=sys.stderr)
                try:
                    complete_run(run_id, status="failed")
                except Exception:
                    pass
                return PipelineResult(
                    status="failed",
                    paper_name=config.paper_name,
                    output_dir=config.output_dir,
                    output_repo_dir=config.output_repo_dir,
                    run_id=run_id,
                    stages_completed=completed_stages,
                    stages_failed=[current_stage],
                    error=f"Stage '{current_stage}' failed: {e}",
                )

        # Run 1.1_extract_config.py (config YAML extraction)
        current_stage_extract = "extract_config"
        if current_stage_extract in stages_to_skip:
            print(f"[pipeline] Step '{current_stage_extract}' already completed. Skipping.", file=sys.stderr)
        else:
            print(f"[pipeline] Extracting config (in-memory)...", file=sys.stderr)
            try:
                extract = load_stage_module("extract_config", "1.1_extract_config.py")
                extract.run_stage(config)
            except Exception as e:
                print(f"❌ Step '{current_stage_extract}' failed: {e}", file=sys.stderr)
                try:
                    complete_run(run_id, status="failed")
                except Exception:
                    pass
                return PipelineResult(
                    status="failed",
                    paper_name=config.paper_name,
                    output_dir=config.output_dir,
                    output_repo_dir=config.output_repo_dir,
                    run_id=run_id,
                    stages_completed=completed_stages,
                    stages_failed=[current_stage_extract],
                    error=f"Extract config step failed: {e}",
                )

        # Copy config to output_repo_dir
        try:
            os.makedirs(config.output_repo_dir, exist_ok=True)
            shutil.copy2(
                os.path.join(config.output_dir, "planning_config.yaml"),
                os.path.join(config.output_repo_dir, "config.yaml")
            )
            print(f"[pipeline] Copied planning_config.yaml to {config.output_repo_dir}/config.yaml", file=sys.stderr)
        except Exception as e:
            print(f"[pipeline] Warning: failed to copy config.yaml to repo dir: {e}", file=sys.stderr)

    # 3. Run analyzing stage
    if config.run_analyzing:
        current_stage = "analyzing"
        if current_stage in stages_to_skip:
            print(f"[pipeline] Stage '{current_stage}' already completed. Skipping.", file=sys.stderr)
            completed_stages.append(current_stage)
        else:
            print(f"[pipeline] Executing analyzing stage (in-memory)...", file=sys.stderr)
            try:
                analyzing = load_stage_module("analyzing", "2_analyzing.py")
                analyzing.run_stage(config)
                completed_stages.append(current_stage)
            except Exception as e:
                print(f"❌ Stage '{current_stage}' failed: {e}", file=sys.stderr)
                try:
                    complete_run(run_id, status="failed")
                except Exception:
                    pass
                return PipelineResult(
                    status="failed",
                    paper_name=config.paper_name,
                    output_dir=config.output_dir,
                    output_repo_dir=config.output_repo_dir,
                    run_id=run_id,
                    stages_completed=completed_stages,
                    stages_failed=[current_stage],
                    error=f"Stage '{current_stage}' failed: {e}",
                )

    # 4. Run coding stage
    if config.run_coding:
        current_stage = "coding"
        if current_stage in stages_to_skip:
            print(f"[pipeline] Stage '{current_stage}' already completed. Skipping.", file=sys.stderr)
            completed_stages.append(current_stage)
        else:
            print(f"[pipeline] Executing coding stage (in-memory)...", file=sys.stderr)
            try:
                coding = load_stage_module("coding", "3_coding.py")
                coding.run_stage(config)
                completed_stages.append(current_stage)
            except Exception as e:
                print(f"❌ Stage '{current_stage}' failed: {e}", file=sys.stderr)
                try:
                    complete_run(run_id, status="failed")
                except Exception:
                    pass
                return PipelineResult(
                    status="failed",
                    paper_name=config.paper_name,
                    output_dir=config.output_dir,
                    output_repo_dir=config.output_repo_dir,
                    run_id=run_id,
                    stages_completed=completed_stages,
                    stages_failed=[current_stage],
                    error=f"Stage '{current_stage}' failed: {e}",
                )

    # 5. Run debugging stage
    if config.run_debugging:
        current_stage = "debugging"
        if not config.error_file_path:
            try:
                complete_run(run_id, status="failed")
            except Exception:
                pass
            return PipelineResult(
                status="failed",
                paper_name=config.paper_name,
                output_dir=config.output_dir,
                output_repo_dir=config.output_repo_dir,
                run_id=run_id,
                stages_completed=completed_stages,
                stages_failed=[current_stage],
                error="Debugging stage requires --error-file to be set.",
            )

        print(f"[pipeline] Executing debugging stage (in-memory)...", file=sys.stderr)
        try:
            debugging = load_stage_module("debugging", "4_debugging.py")
            debugging.run_stage(config)
            completed_stages.append(current_stage)
        except Exception as e:
            print(f"❌ Stage '{current_stage}' failed: {e}", file=sys.stderr)
            try:
                complete_run(run_id, status="failed")
            except Exception:
                pass
            return PipelineResult(
                status="failed",
                paper_name=config.paper_name,
                output_dir=config.output_dir,
                output_repo_dir=config.output_repo_dir,
                run_id=run_id,
                stages_completed=completed_stages,
                stages_failed=[current_stage],
                error=f"Stage '{current_stage}' failed: {e}",
            )

    # 6. Complete DB run and compile stats
    try:
        complete_run(run_id, status="completed")
    except Exception as e:
        print(f"[pipeline] Warning: failed to complete run in DB: {e}", file=sys.stderr)

    try:
        summary = get_run_summary(run_id)
        if summary and summary.get("status") not in ("disabled", "not_found"):
            return PipelineResult(
                status="success",
                paper_name=config.paper_name,
                output_dir=config.output_dir,
                output_repo_dir=config.output_repo_dir,
                run_id=run_id,
                stages_completed=completed_stages,
                stages_failed=[],
                cost_usd=summary.get("total_cost", 0.0),
                tokens_in=summary.get("total_tokens_in", 0),
                tokens_out=summary.get("total_tokens_out", 0),
                error=None,
            )
    except Exception as e:
        print(f"[pipeline] Warning: failed to fetch run summary from DB: {e}", file=sys.stderr)

    return PipelineResult(
        status="success",
        paper_name=config.paper_name,
        output_dir=config.output_dir,
        output_repo_dir=config.output_repo_dir,
        run_id=run_id,
        stages_completed=completed_stages,
        stages_failed=[],
        error=None,
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Check for and resume an incomplete or failed run.",
    )
    parser.add_argument(
        "--error-file",
        type=str,
        default="",
        help="Path to error message file for debugging stage.",
    )
    parser.add_argument(
        "--debug-save-num",
        type=int,
        default=1,
        help="Backups index for debugging (default: 1)",
    )
    parser.add_argument(
        "--paper-format",
        choices=["JSON", "LaTeX"],
        default="JSON",
        help="Input paper format (default: JSON)",
    )
    parser.add_argument(
        "--pdf-latex-path",
        type=str,
        default="",
        help="Path to LaTeX source files if paper-format is LaTeX",
    )
    return parser


def main() -> None:
    """
    CLI entry point.
    """
    parser = _build_arg_parser()
    args = parser.parse_args()

    # Capture original stdout and redirect all output to stderr if JSON format is requested
    original_stdout = sys.stdout
    if args.output_format == "json":
        sys.stdout = sys.stderr

    try:
        stages = [s.strip().lower() for s in args.stages.split(",")]
        config = PipelineConfig(
            paper_name=args.paper_name,
            pdf_json_path=args.pdf_json_path,
            output_dir=args.output_dir,
            output_repo_dir=args.output_repo_dir,
            model=args.model,
            run_planning="planning" in stages,
            run_analyzing="analyzing" in stages,
            run_coding="coding" in stages,
            run_debugging="debugging" in stages,
            error_file_path=args.error_file,
            debug_save_num=args.debug_save_num,
            paper_format=args.paper_format,
            pdf_latex_path=args.pdf_latex_path,
            output_format=args.output_format,
            resume=args.resume,
        )

        result = run_pipeline(config)
    finally:
        # Always restore stdout
        sys.stdout = original_stdout

    if config.output_format == "json":
        print(result.to_json())
    else:
        print(f"[pipeline] status={result.status}  paper={result.paper_name}")
        if result.error:
            print(f"[pipeline] error: {result.error}", file=sys.stderr)

    sys.exit(0 if result.status == "success" else 1)


if __name__ == "__main__":
    main()
