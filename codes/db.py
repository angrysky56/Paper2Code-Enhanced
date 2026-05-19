"""
db.py — SQLite persistence layer for Paper2Code-Enhanced.

Phase 2 of the meta-harness integration plan.
Tracks pipeline runs, per-stage LLM results, and code execution trials.
Enables resume-on-failure, RLM analysis, and audit history.

Database file location: DB_PATH in .env (default: ../outputs/paper2code.db)

Schema:
    Run              — top-level pipeline run record
    StageResult      — one record per LLM stage call (planning, analyzing, coding, debugging)
    ExecutionTrial   — one record per code execution attempt in the sandbox

Design rules:
    - Append-only: never UPDATE rows, always INSERT new ones.
    - All timestamps are UTC ISO-8601 strings.
    - All writes are wrapped in get_session() context manager.
    - Scripts import write_* helpers; they never touch SQLModel directly.

Usage:
    from db import init_db, create_run, write_stage_result, write_execution_trial
    init_db()
    run_id = create_run(paper_name="Transformer", model_used="MiniMax-M2.7")
    write_stage_result(run_id, stage_name="planning", success=True, tokens_in=1200, ...)

TODO(phase-2): Call init_db() at the top of each stage script after load_dotenv().
TODO(phase-2): Call create_run() in run.sh equivalent / pipeline.py entry point.
TODO(phase-2): Call write_stage_result() after every LLM api_call() in each stage script.
TODO(phase-2): Call write_execution_trial() in 4_debugging.py after each subprocess run.
TODO(phase-2): Add resume logic — check for existing Run with status='running' and
    re-use its run_id instead of creating a new one (idempotent pipeline re-entry).
TODO(phase-2): Add a CLI query tool (db_query.py) for inspecting run history / RLM stats.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Optional SQLModel import — gracefully degrade if not installed yet
# ---------------------------------------------------------------------------
try:
    from sqlmodel import Field, Session, SQLModel, create_engine, select
    _SQLMODEL_AVAILABLE = True
except ImportError:
    _SQLMODEL_AVAILABLE = False
    print(
        "[db] WARNING: sqlmodel not installed. Persistence is disabled. "
        "Run: pip install sqlmodel"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_str(s: str) -> str:
    """Short SHA-256 hex digest for content-addressing code/input snapshots."""
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _get_db_path() -> str:
    return os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "outputs", "paper2code.db"))


# ---------------------------------------------------------------------------
# SQLModel table definitions
# ---------------------------------------------------------------------------

if _SQLMODEL_AVAILABLE:

    class Run(SQLModel, table=True):
        """
        Top-level record for a single end-to-end pipeline execution.
        One Run per invocation of run.sh / pipeline.run_pipeline().
        """
        id: Optional[int] = Field(default=None, primary_key=True)
        paper_name: str
        model_used: str
        executor_type: str = "subprocess"
        status: str = "running"          # running | completed | failed | interrupted
        started_at: str = Field(default_factory=_utcnow)
        completed_at: Optional[str] = None
        output_dir: str = ""
        notes: str = ""                  # free-form, e.g. git commit or experiment tag

        # TODO(phase-2): Add foreign key to a future Project table once
        #   meta-harness domain tracking is introduced.

    class StageResult(SQLModel, table=True):
        """
        One record per LLM call within a pipeline stage.
        Append-only — re-runs create new rows, not updates.
        """
        id: Optional[int] = Field(default=None, primary_key=True)
        run_id: int = Field(foreign_key="run.id")
        stage_name: str                  # planning | analyzing | coding | debugging | rag_config | eval
        input_hash: str = ""             # hash of prompt/messages for dedup / caching analysis
        output_path: str = ""            # path to saved JSON/artifact for this stage
        tokens_in: int = 0
        tokens_out: int = 0
        cost_usd: float = 0.0
        success: bool = False
        error_text: str = ""
        model_used: str = ""             # may differ from Run if overridden per-stage
        created_at: str = Field(default_factory=_utcnow)

        # TODO(phase-2): Store compressed prompt/response snapshots as BLOB
        #   for full RLM replay. Use zlib.compress(json.dumps(messages).encode()).

    class ExecutionTrial(SQLModel, table=True):
        """
        One record per sandboxed code execution attempt.
        Used by 4_debugging.py to track iterations and convergence.
        """
        id: Optional[int] = Field(default=None, primary_key=True)
        run_id: int = Field(foreign_key="run.id")
        attempt_num: int = 1
        code_hash: str = ""              # hash of the repo state being tested
        stdout: str = ""
        stderr: str = ""
        returncode: int = -1
        timed_out: bool = False
        elapsed_seconds: float = 0.0
        success: bool = False
        created_at: str = Field(default_factory=_utcnow)

        # TODO(phase-2): Link to the StageResult that generated this code version
        #   for end-to-end reasoning chain reconstruction.
        # coding_stage_result_id: Optional[int] = Field(default=None, foreign_key="stageresult.id")


# ---------------------------------------------------------------------------
# Engine / session management
# ---------------------------------------------------------------------------

_engine = None


def init_db() -> None:
    """
    Create the SQLite database file and all tables if they don't exist.
    Call once at startup (idempotent).

    TODO(phase-2): Add Alembic migration support for schema evolution
        so existing DB files don't need to be dropped on schema changes.
    """
    if not _SQLMODEL_AVAILABLE:
        return

    global _engine
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    _engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(_engine)
    print(f"[db] Initialized: {db_path}")


def get_session() -> "Session":
    """Return a live SQLModel Session. Use as a context manager."""
    if not _SQLMODEL_AVAILABLE or _engine is None:
        raise RuntimeError("[db] Database not initialized. Call init_db() first.")
    return Session(_engine)


# ---------------------------------------------------------------------------
# Write helpers — the only interface stage scripts should use
# ---------------------------------------------------------------------------

def create_run(
    paper_name: str,
    model_used: str,
    output_dir: str = "",
    executor_type: str = "subprocess",
    notes: str = "",
) -> int:
    """
    Insert a new Run record and return its integer ID.
    Pass this ID to all subsequent write_* calls for this pipeline execution.

    TODO(phase-2): Before inserting, check for a stale 'running' Run with the
        same paper_name + output_dir and return its ID instead (resume support).
    """
    if not _SQLMODEL_AVAILABLE or _engine is None:
        return -1  # persistence disabled — callers should handle -1 run_id gracefully

    run = Run(
        paper_name=paper_name,
        model_used=model_used,
        output_dir=output_dir,
        executor_type=executor_type,
        notes=notes,
    )
    with get_session() as session:
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id  # type: ignore[return-value]


def complete_run(run_id: int, status: str = "completed") -> None:
    """
    Mark a Run as completed (or failed/interrupted).
    Call at the end of each pipeline stage script or pipeline.py.

    TODO(phase-2): Compute aggregate cost/token totals from StageResult rows
        and write them back onto the Run record for quick dashboard queries.
    """
    if not _SQLMODEL_AVAILABLE or _engine is None or run_id < 0:
        return

    with get_session() as session:
        run = session.get(Run, run_id)
        if run:
            run.status = status
            run.completed_at = _utcnow()
            session.add(run)
            session.commit()


def write_stage_result(
    run_id: int,
    stage_name: str,
    *,
    success: bool = False,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    output_path: str = "",
    error_text: str = "",
    model_used: str = "",
    messages: list | None = None,     # pass raw messages list for input_hash
) -> int:
    """
    Append a StageResult row and return its ID.
    Call after every LLM api_call() in stage scripts.

    Example (in 1_planning.py, after api_call()):
        from db import write_stage_result
        write_stage_result(
            run_id, "planning",
            success=True,
            tokens_in=usage_info["actual_input_tokens"],
            tokens_out=usage_info["output_tokens"],
            cost_usd=usage_info["total_cost"],
            output_path=f"{output_dir}/planning_trajectories.json",
        )

    TODO(phase-2): Serialize and compress `messages` into a BLOB column for
        full prompt/response replay in RLM analysis.
    """
    if not _SQLMODEL_AVAILABLE or _engine is None or run_id < 0:
        return -1

    input_hash = _hash_str(str(messages)) if messages else ""
    record = StageResult(
        run_id=run_id,
        stage_name=stage_name,
        input_hash=input_hash,
        output_path=output_path,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        success=success,
        error_text=error_text,
        model_used=model_used,
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id  # type: ignore[return-value]


def write_execution_trial(
    run_id: int,
    attempt_num: int,
    *,
    stdout: str = "",
    stderr: str = "",
    returncode: int = -1,
    timed_out: bool = False,
    elapsed_seconds: float = 0.0,
    code_dir: str = "",               # hashed to track repo state
) -> int:
    """
    Append an ExecutionTrial row and return its ID.
    Call in 4_debugging.py after each executor.run() call.

    Example (in 4_debugging.py):
        from db import write_execution_trial
        from executor import get_executor
        executor = get_executor()
        result = executor.run(["python", "main.py"], cwd=debug_dir)
        write_execution_trial(
            run_id, attempt_num=args.save_num,
            stdout=result.stdout, stderr=result.stderr,
            returncode=result.returncode, timed_out=result.timed_out,
            elapsed_seconds=result.elapsed_seconds,
        )

    TODO(phase-2): Hash the directory contents of code_dir to produce code_hash
        so different code versions are distinguishable in RLM replay.
    """
    if not _SQLMODEL_AVAILABLE or _engine is None or run_id < 0:
        return -1

    code_hash = _hash_str(code_dir) if code_dir else ""
    record = ExecutionTrial(
        run_id=run_id,
        attempt_num=attempt_num,
        code_hash=code_hash,
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        timed_out=timed_out,
        elapsed_seconds=elapsed_seconds,
        success=(returncode == 0 and not timed_out),
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Simple query helpers (for future db_query.py / dashboard)
# ---------------------------------------------------------------------------

def get_run_summary(run_id: int) -> dict:
    """
    Return a summary dict for a single Run including stage count and total cost.

    TODO(phase-2): Implement fully — currently returns empty shell.
    TODO(phase-2): Add get_all_runs(), get_failed_runs(), get_runs_by_paper() helpers.
    """
    # TODO(phase-2): Implement this query.
    return {"run_id": run_id, "status": "not_implemented"}
