# Phase 02: Database Persistence & RLM Logging - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase implements database auditing, execution persistence, and resume-on-failure capabilities for the Paper2Code-Enhanced pipeline. It integrates SQLModel/SQLite into all stage scripts to store execution trajectories and reasoning loop history, and introduces database query utilities.

Deliverables:
- Stable database initialization (`init_db`) and migration-ready schema using SQLModel and SQLite.
- Seamless logging of stage outputs, tokens, costs, and execution details to `Run`, `StageResult`, and `ExecutionTrial` tables across all pipeline scripts.
- Idempotent pipeline re-entry and resume-on-failure capability that detects active/failed runs.
- A functional analytics command-line query tool (`db_query.py`) summarizing run stats, token consumption, total cost, and convergence rates.
</domain>

<decisions>
## Implementation Decisions

### DB-01: SQLModel Engine & Schema Wiring
- Use `sqlmodel` for SQLite ORM operations.
- Ensure database initializes gracefully and tables (`Run`, `StageResult`, `ExecutionTrial`) are auto-created when `init_db()` is called.
- Gracefully handle situations where `sqlmodel` is not installed or SQLite fails, falling back to warning logs and dummy run IDs so execution is not blocked.

### DB-02: Pipeline Stage Logging
- Integrate `init_db()` and `write_stage_result()` or `write_execution_trial()` calls in:
  - `codes/1_planning.py`
  - `codes/2_analyzing.py`
  - `codes/3_coding.py`
  - `codes/4_debugging.py`
  - `codes/pipeline.py`
- Track API metadata: input/output tokens, cost in USD, LLM model used, prompt hashes, output file paths, and execution trial statuses.

### DB-03: Resume-on-Failure and Idempotency
- Modify run initialization logic (`create_run()`) to check for an existing incomplete/active run (e.g., status is `"running"` or `"interrupted"`) matching the same paper name and output directory.
- If a stale or active run is detected, reuse the existing `run_id` to ensure idempotent resume-on-failure.

### DB-04: db_query.py CLI Tool
- Create a dedicated CLI query tool at `codes/db_query.py` that queries SQLite to provide clear statistics:
  - Summary of runs (dates, models, status).
  - Total tokens used and aggregate costs.
  - Convergence rates of debugging iterations (trials per run).

### the agent's Discretion
- Database Schema: Keep the `db.py` schema strictly append-only.
- Resume heuristics: Determine matching criteria for a resume run based on `paper_name` and `output_dir`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Persistence Configuration
- `codes/db.py` — Database models, SQLite initialization, and append-only write helpers.
- `codes/pipeline.py` — Pipeline execution and orchestration entry point.

### Pipeline Stage Scripts
- `codes/1_planning.py` — LLM paper planning script.
- `codes/2_analyzing.py` — LLM architecture analysis script.
- `codes/3_coding.py` — LLM PyTorch coding script.
- `codes/4_debugging.py` — Loop compiler self-debugging loop.
</canonical_refs>

<specifics>
## Specific Ideas
- The SQLite file is located at `outputs/paper2code.db` by default (defined in `DB_PATH` in `.env`).
- In `codes/4_debugging.py`, replace raw subprocess run logs with `write_execution_trial()` calls after sandbox execution.
</specifics>

<deferred>
## Deferred Ideas
- Multi-repository project tracking (v2).
- Web dashboard/visualization for runs (ANLT-01, ANLT-02).
</deferred>
