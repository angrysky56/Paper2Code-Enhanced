# codes/server.py
"""
server.py — FastAPI backend server for Paper2Code-Enhanced.

Exposes PaperCoder's pipeline, PDF cleaning, evaluation, andSQLite database run
history as REST endpoints. Designed to be consumed by the Go CLI/MCP server.
"""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

# Ensure the parent and current directory are on PATH for proper imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from db import (  # type: ignore
    DB_PATH,
    get_all_runs,
    get_run_summary,
    get_session,
    init_db,
)

try:
    from db import ExecutionTrial, Run, StageResult  # type: ignore
    from sqlmodel import select

    _SQLMODEL_AVAILABLE = True
except ImportError:
    _SQLMODEL_AVAILABLE = False

import importlib

import codes.eval as eval_module
from codes.pipeline import PipelineConfig, run_pipeline

pdf_process = importlib.import_module("codes.0_pdf_process")

app = FastAPI(
    title="Paper2Code-Enhanced API Server",
    description="Local API backend for executing and auditing PaperCoder's academic code generation pipeline.",
    version="0.1.0",
    servers=[
        {"url": "http://localhost:8000", "description": "Local development server"}
    ],
)


# Initialize database at startup
@app.on_event("startup")
def startup_event():
    try:
        init_db(quiet=True)
    except Exception as e:
        print(f"[server] Error initializing database: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    db_path: str
    db_available: bool


class PDFProcessRequest(BaseModel):
    input_json_path: str = Field(..., description="Path to input PDF or Grobid JSON.")
    output_json_path: str = Field(
        ..., description="Path to save processed and cleaned JSON."
    )
    mode: str = Field("auto", description="Processing mode: auto, vlm, olmocr, local.")
    gpt_version: str | None = Field(None, description="VLM model choice override.")
    paper_name: str | None = Field(None, description="Name of the paper.")


class PDFProcessResponse(BaseModel):
    status: str
    message: str
    output_json_path: str


class PipelineRunRequest(BaseModel):
    paper_name: str = Field(..., description="Name of the paper.")
    pdf_json_path: str = Field(..., description="Path to the PDF-based JSON format.")
    output_dir: str = Field(..., description="Directory to save generated artifacts.")
    output_repo_dir: str = Field(
        ..., description="Directory to save final output repository."
    )
    model: str | None = Field(None, description="Model override (e.g. MiniMax-M2.7).")
    run_planning: bool = Field(True, description="Execute planning stage.")
    run_analyzing: bool = Field(True, description="Execute analyzing stage.")
    run_coding: bool = Field(True, description="Execute coding stage.")
    run_debugging: bool = Field(False, description="Execute debugging stage.")
    error_file_path: str = Field(
        "", description="Path to error message file for debugging."
    )
    debug_save_num: int = Field(1, description="Backups index for debugging.")
    paper_format: Literal["JSON", "LaTeX"] = Field(
        "JSON", description="Input paper format."
    )
    pdf_latex_path: str = Field(
        "", description="Path to LaTeX source files if paper-format is LaTeX."
    )
    resume: bool = Field(False, description="Resume from an interrupted or failed run.")


class PipelineRunResponse(BaseModel):
    run_id: int
    paper_name: str
    status: str
    message: str


class EvalRunRequest(BaseModel):
    paper_name: str = Field(..., description="Name of the paper.")
    pdf_json_path: str = Field(..., description="Path to the PDF-based JSON.")
    data_dir: str = Field("../data", description="Data directory path.")
    output_dir: str = Field(..., description="Artifact directory of the pipeline.")
    target_repo_dir: str = Field(..., description="Generated repository directory.")
    gold_repo_dir: str = Field("", description="Official gold repository directory.")
    eval_result_dir: str = Field(
        ..., description="Directory to save evaluation results."
    )
    eval_type: Literal["ref_free", "ref_based"] = Field(
        "ref_free", description="Evaluation type."
    )
    generated_n: int = Field(8, description="Number of evaluation samples to average.")
    gpt_version: str | None = Field(None, description="Model choice override.")
    papercoder: bool = Field(True, description="Evaluate as PaperCoder generated repo.")


class EvalRunResponse(BaseModel):
    status: str
    paper_name: str
    eval_type: str
    score: float
    valid_samples: str
    output_file: str


class RunStageSummary(BaseModel):
    stage_name: str
    success: bool
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: str


class RunTrialSummary(BaseModel):
    attempt_num: int
    returncode: int | None
    success: bool
    elapsed_seconds: float
    created_at: str


class RunDetailResponse(BaseModel):
    run_id: int
    paper_name: str
    model_used: str | None
    executor_type: str | None
    status: str
    started_at: str
    completed_at: str | None
    output_dir: str | None
    notes: str | None
    total_cost: float
    total_tokens_in: int
    total_tokens_out: int
    stages: list[RunStageSummary]
    trials: list[RunTrialSummary]


class RunListItem(BaseModel):
    id: int
    paper_name: str
    model_used: str | None
    status: str
    started_at: str
    completed_at: str | None
    total_cost: float


class StatsResponse(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    running_runs: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    total_trials: int
    debug_convergence_rate: float | None


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------


def execute_pipeline_background(config: PipelineConfig):
    """Worker function to run the pipeline synchronously in a background thread."""
    try:
        run_pipeline(config)
    except Exception as e:
        print(f"[server] Background pipeline execution failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health_check():
    db_ok = os.path.exists(os.path.dirname(os.path.abspath(DB_PATH)))
    return HealthResponse(
        status="ok",
        db_path=DB_PATH,
        db_available=db_ok,
    )


@app.post("/pdf/process", response_model=PDFProcessResponse)
def process_pdf(req: PDFProcessRequest):
    """Processes PDF input into clean, structured S2ORC JSON."""
    try:
        # Build arguments object like argparse namespace
        args = SimpleNamespace(
            input_json_path=req.input_json_path,
            output_json_path=req.output_json_path,
            mode=req.mode,
            gpt_version=req.gpt_version or os.environ.get("LLM_MODEL", "MiniMax-M2.7"),
            paper_name=req.paper_name,
        )
        pdf_process.main(args)
        return PDFProcessResponse(
            status="success",
            message="PDF successfully parsed and cleaned.",
            output_json_path=req.output_json_path,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"PDF processing failed: {str(e)}"
        ) from e


@app.post("/pipeline/run", response_model=PipelineRunResponse)
def run_pipeline_endpoint(req: PipelineRunRequest, background_tasks: BackgroundTasks):
    """Starts the PaperCoder pipeline in the background and returns the run ID."""
    # Ensure directories exist
    os.makedirs(req.output_dir, exist_ok=True)
    os.makedirs(req.output_repo_dir, exist_ok=True)

    # 1. Instantiate the pipeline config
    model = req.model or os.environ.get("LLM_MODEL", "MiniMax-M2.7")
    config = PipelineConfig(
        paper_name=req.paper_name,
        pdf_json_path=req.pdf_json_path,
        output_dir=req.output_dir,
        output_repo_dir=req.output_repo_dir,
        model=model,
        run_planning=req.run_planning,
        run_analyzing=req.run_analyzing,
        run_coding=req.run_coding,
        run_debugging=req.run_debugging,
        error_file_path=req.error_file_path,
        debug_save_num=req.debug_save_num,
        paper_format=req.paper_format,
        pdf_latex_path=req.pdf_latex_path,
        resume=req.resume,
    )

    # 2. Pre-initialize/verify DB run and get a run ID (idempotent resume check)
    from db import create_run  # type: ignore

    try:
        run_id = create_run(
            paper_name=req.paper_name,
            model_used=model,
            output_dir=req.output_dir,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database run initialization failed: {str(e)}"
        ) from e

    if run_id <= 0:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve run_id from SQLite DB."
        )

    config.run_id = run_id

    # 3. Add to background task queue to execute concurrently
    background_tasks.add_task(execute_pipeline_background, config)

    return PipelineRunResponse(
        run_id=run_id,
        paper_name=req.paper_name,
        status="running",
        message=f"PaperCoder pipeline started in background. Monitor via run ID {run_id}.",
    )


@app.post("/eval/run", response_model=EvalRunResponse)
def run_evaluation(req: EvalRunRequest):
    """Runs programmatic reference-free/reference-based evaluation on the generated repo."""
    try:
        # Load environment defaults if none provided
        gpt = req.gpt_version or os.environ.get("LLM_MODEL", "MiniMax-M2.7")
        args = SimpleNamespace(
            paper_name=req.paper_name,
            pdf_json_path=req.pdf_json_path,
            data_dir=req.data_dir or "../data",
            output_dir=req.output_dir,
            target_repo_dir=req.target_repo_dir,
            gold_repo_dir=req.gold_repo_dir,
            eval_result_dir=req.eval_result_dir,
            eval_type=req.eval_type,
            generated_n=req.generated_n,
            gpt_version=gpt,
            papercoder=req.papercoder,
            selected_file_path="",
        )

        # Execute eval
        eval_module.main(args)

        # Find latest output file
        eval_files = [
            f
            for f in os.listdir(req.eval_result_dir)
            if f.startswith(f"{req.paper_name}_eval_{req.eval_type}_")
        ]
        latest_file = ""
        score = 0.0
        valid_n = 0
        if eval_files:
            eval_files.sort(reverse=True)
            latest_file = os.path.join(req.eval_result_dir, eval_files[0])
            with open(latest_file) as f:
                res = json.load(f)
                score = res["eval_result"]["score"]
                valid_n = res["eval_result"]["valid_n"]

        return EvalRunResponse(
            status="success",
            paper_name=req.paper_name,
            eval_type=req.eval_type,
            score=score,
            valid_samples=f"{valid_n}/{req.generated_n}",
            output_file=latest_file,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Evaluation failed: {str(e)}"
        ) from e


@app.get("/runs", response_model=list[RunListItem])
def list_runs():
    """Queries all run records from the SQLite database."""
    try:
        runs = get_all_runs()
        return [
            RunListItem(
                id=r.id,
                paper_name=r.paper_name,
                model_used=r.model_used,
                status=r.status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                total_cost=r.total_cost or 0.0,
            )
            for r in runs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query database runs: {str(e)}"
        ) from e


@app.get("/runs/{run_id}", response_model=RunDetailResponse)
def run_detail(run_id: int):
    """Queries full status details and stage steps for a specific run ID."""
    try:
        summary = get_run_summary(run_id)
        if summary.get("status") in ("not_found", "disabled"):
            raise HTTPException(
                status_code=404,
                detail=f"Run ID {run_id} not found or database is disabled.",
            )

        return RunDetailResponse(
            run_id=summary["run_id"],
            paper_name=summary["paper_name"],
            model_used=summary["model_used"],
            executor_type=summary["executor_type"],
            status=summary["status"],
            started_at=summary["started_at"],
            completed_at=summary["completed_at"],
            output_dir=summary["output_dir"],
            notes=summary.get("notes", ""),
            total_cost=summary["total_cost"],
            total_tokens_in=summary["total_tokens_in"],
            total_tokens_out=summary["total_tokens_out"],
            stages=[
                RunStageSummary(
                    stage_name=s["stage_name"],
                    success=s["success"],
                    tokens_in=s["tokens_in"],
                    tokens_out=s["tokens_out"],
                    cost_usd=s["cost_usd"],
                    created_at=s["created_at"],
                )
                for s in summary["stages"]
            ],
            trials=[
                RunTrialSummary(
                    attempt_num=t["attempt_num"],
                    returncode=t.get("returncode"),
                    success=t["success"],
                    elapsed_seconds=t["elapsed_seconds"],
                    created_at=t["created_at"],
                )
                for t in summary["trials"]
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query run details: {str(e)}"
        ) from e


@app.get("/stats", response_model=StatsResponse)
def aggregate_stats():
    """Calculates global performance convergence rates, costs, and token consumption aggregates."""
    if not _SQLMODEL_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="SQLModel is not available. Persistence is disabled.",
        )

    try:
        with get_session() as session:
            total_runs = session.exec(select(Run)).all()
            if not total_runs:
                return StatsResponse(
                    total_runs=0,
                    completed_runs=0,
                    failed_runs=0,
                    running_runs=0,
                    total_tokens_in=0,
                    total_tokens_out=0,
                    total_cost_usd=0.0,
                    total_trials=0,
                    debug_convergence_rate=None,
                )

            total_stages = session.exec(select(StageResult)).all()
            total_trials = session.exec(select(ExecutionTrial)).all()

            runs_count = len(total_runs)
            completed_runs = sum(1 for r in total_runs if r.status == "completed")
            failed_runs = sum(1 for r in total_runs if r.status == "failed")
            running_runs = sum(1 for r in total_runs if r.status == "running")

            total_tokens_in = sum(s.tokens_in for s in total_stages)
            total_tokens_out = sum(s.tokens_out for s in total_stages)
            total_cost = sum(s.cost_usd for s in total_stages)

            # Group trials by run_id
            trials_by_run = {}
            for t in total_trials:
                trials_by_run.setdefault(t.run_id, []).append(t)

            resolved_runs_trial_counts = []
            for _rid, run_trials in trials_by_run.items():
                if any(t.success for t in run_trials):
                    resolved_runs_trial_counts.append(len(run_trials))

            avg_trials_to_converge = (
                sum(resolved_runs_trial_counts) / len(resolved_runs_trial_counts)
                if resolved_runs_trial_counts
                else None
            )

            return StatsResponse(
                total_runs=runs_count,
                completed_runs=completed_runs,
                failed_runs=failed_runs,
                running_runs=running_runs,
                total_tokens_in=total_tokens_in,
                total_tokens_out=total_tokens_out,
                total_cost_usd=total_cost,
                total_trials=len(total_trials),
                debug_convergence_rate=avg_trials_to_converge,
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query database statistics: {str(e)}"
        ) from e
