# Roadmap: Paper2Code-Enhanced Modernization

## Overview

This roadmap lays out the four key modernization phases to transition the **Paper2Code-Enhanced** repository into a robust, safe, persisted, and meta-harness-interoperable codebase. By introducing isolated sandboxed execution, an append-only persistence layer for Reasoning Loop Methodology (RLM) analysis, and a clean, structured CLI contract, Paper2Code will be fully optimized for programmatic consumption by `OrCAID`, `meta-harness`, and the `hermes` agent harness.

## Phases

- [ ] **Phase 1: Sandboxed Code Execution** - Secure generated PyTorch code execution using restricted Subprocess and Docker runtimes.
- [ ] **Phase 2: Database Persistence & RLM Logging** - Append-only SQLite/SQLModel logging of Runs, StageResults, and ExecutionTrials.
- [ ] **Phase 3: Structured CLI Interoperability** - Format CLI output to dump machine-readable JSON to `stdout` and redirect logging to `stderr`.
- [ ] **Phase 4: Programmatic Pipeline Orchestration** - Refactor and unify all reasoning stage functions in-memory and register a global CLI wrapper.

## Phase Details

### Phase 1: Sandboxed Code Execution
**Goal**: Secure and isolate PyTorch code execution in the self-debugging compiler loop.
**Mode**: mvp
**Depends on**: Nothing
**Requirements**: EXEC-01, EXEC-02, EXEC-03
**Success Criteria**:
  1. SubprocessExecutor successfully enforces RSS memory limits using the `resource` module in Linux when a limit is configured.
  2. DockerExecutor launches a container, mounts the workspace, runs generated code, captures outputs, and cleans up resource handles.
  3. The `4_debugging.py` loop executes code exclusively using `get_executor()` and never spawns raw subprocesses.
**Plans**: 3 plans

Plans:
**Wave 1**
- [x] 01-01: Implement memory constraints in `SubprocessExecutor` using resource setrlimits
- [ ] 01-02: Implement PyTorch/CUDA-capable containerised runtime in `DockerExecutor`

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01-03: Wire the sandboxed executor into `4_debugging.py` replacing raw shell executions

### Phase 2: Database Persistence & RLM Logging
**Goal**: Implement complete database auditing, metrics collection, and resume-on-failure.
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: DB-01, DB-02, DB-03, DB-04
**Success Criteria**:
  1. SQLModel database initializes successfully and creates all tables (Run, StageResult, ExecutionTrial).
  2. All stage scripts (planning, analyzing, coding, debugging) cleanly log API usage (tokens, cost, hashes) to the DB.
  3. The pipeline detects a stalled run in the database and resumes from the last completed stage.
  4. A dedicated `db_query.py` CLI provides formatted statistics on run counts, total costs, and compilation convergence rates.
**Plans**: 4 plans

Plans:
- [ ] 02-01: Finalize SQLModel SQLite engine wiring and verify schema initialization
- [ ] 02-02: Wire `init_db()` and `write_stage_result()` logging into planning, analyzing, and coding scripts
- [ ] 02-03: Wire `write_execution_trial()` logging into the debugging loop
- [ ] 02-04: Implement run-resume query logic and build the `db_query.py` analytics tool

### Phase 3: Structured CLI Interoperability
**Goal**: Standardize CLI outputs for programmatic integration into meta-harness.
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: CLI-01, CLI-02
**Success Criteria**:
  1. Spawning pipeline with `--output-format json` prints only a single machine-readable JSON block to `stdout` upon completion.
  2. All pipeline progress logs, warning notices, and debug traces are redirected strictly to `stderr` to prevent JSON pollution.
  3. Sub-stage selection via `--stages` (e.g. `--stages planning,coding`) works perfectly from the CLI.
**Plans**: 1 plan

Plans:
- [ ] 03-01: Standardize CLI arg parser, separate `stdout` vs `stderr` streams, and emit structured JSON results

### Phase 4: Programmatic Pipeline Orchestration
**Goal**: Package the entire execution pipeline as a clean Python library and global executable.
**Mode**: mvp
**Depends on**: Phase 3
**Requirements**: PIPE-01, PIPE-02
**Success Criteria**:
  1. `pipeline.py` executes all stages in-memory without invoking subprocess shells for python execution.
  2. All stage scripts expose a clear `run_stage(config)` programmatic API entry point.
  3. The project installs as a command-line script (`paper2code`) on the path via `pyproject.toml`.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Refactor stage scripts to expose `run_stage` functions and implement in-memory orchestrator
- [ ] 04-02: Register `console_scripts` in `pyproject.toml` and verify global PATH installation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Sandboxed Code Execution | 1/3 | In Progress|  |
| 2. Database Persistence & RLM Logging | 0/4 | Not started | - |
| 3. Structured CLI Interoperability | 0/1 | Not started | - |
| 4. Programmatic Pipeline Orchestration | 0/2 | Not started | - |
