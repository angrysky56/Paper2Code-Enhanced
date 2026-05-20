---
phase: 03-structured-cli-interoperability
plan: 03-01
subsystem: cli
tags: [argparse, subprocess, stdout, stderr, json]

# Dependency graph
requires: [02-database-persistence-rlm-logging]
provides:
  - Structured CLI contract with json output mode
  - Standardized argument parser
  - Robust subprocess stage orchestration
affects: [03-structured-cli-interoperability, codes/pipeline.py, tests/test_cli_interop.py]

# Tech tracking
tech-stack:
  added: []
  patterns: [stdout/stderr stream isolation for machine readability]

key-files:
  created: [tests/test_cli_interop.py]
  modified: [codes/pipeline.py]

key-decisions:
  - "Redirected sys.stdout to sys.stderr at main() initialization when json output format is active, and restored original sys.stdout before printing the final JSON results, ensuring zero logs contaminate standard output."
  - "Configured spawned child processes to redirect both stdout and stderr to sys.stderr to keep pipeline stdout completely clean."

patterns-established:
  - "Pattern 1: Stream isolation for CLI machine readability: Diverting diagnostic logs to stderr to keep stdout purely for structured, parseable JSON payloads."
  - "Pattern 2: Sequential subprocess stage orchestration: Executing isolated pipeline stage scripts via subprocesses while aggregate database metrics are retrieved to yield final execution results."

requirements-completed: [CLI-01, CLI-02]

# Metrics
duration: 15 min
completed: 2026-05-20
---

# Phase 3 Plan 1: CLI Interoperability Summary

**Standardized the command-line interface in `codes/pipeline.py` with argument parsing, stream isolation (stdout/stderr separation), sequential subprocess stage orchestration, database metrics integration, and a comprehensive pytest integration suite.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-05-20T00:00:00Z
- **Completed:** 2026-05-20T00:02:46Z
- **Tasks:** 4
- **Files modified:** 1
- **Files created:** 1

## Accomplishments

- Extended CLI argument parsing in `codes/pipeline.py` to support `--stages`, `--model`, `--output-format`, `--resume`, `--error-file`, and other configuration parameters.
- Implemented `stdout`/`stderr` stream separation to cleanly direct progress and diagnostic logging to `stderr` when `--output-format json` is requested.
- Programmed sequential stage orchestration inside `run_pipeline(config)` to execute stages (`1_planning.py`, `2_analyzing.py`, `3_coding.py`, `4_debugging.py`) as subprocesses.
- Connected the orchestration logic to the SQLite database via `db.py` to persist runs, stages, and fetch consolidated cost and token metrics.
- Created `tests/test_cli_interop.py` containing a comprehensive pytest suite to assert correct CLI parsing, stream separation, failure resilience, and JSON payload format.

## Task Commits

1. **Phase 3 CLI and Stream Separation** - `feat(03-01): implement CLI interoperability, stream isolation, subprocess orchestration, and pytest test suite`

## Files Created/Modified

- `codes/pipeline.py` - Extended argument parser, implemented stdout/stderr stream isolation, and added subprocess orchestration.
- `tests/test_cli_interop.py` - Created robust CLI parsing and stream isolation tests.

## Decisions Made

- Redirected spawned stage scripts to `sys.stderr` to avoid any possibility of console output pollution.
- Used pytest-mock to mock out database operations (`init_db`, `create_run`, `complete_run`) and `subprocess.run` calls, ensuring rapid, reliable test execution without requiring actual LLM credentials or database changes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Mock Target Paths:** Standard python mock target gotchas (e.g. patching `db.init_db` instead of `codes.pipeline.init_db` where it's imported and used). Resolved by patching `codes.pipeline.*` references directly.

## User Setup Required

None.

## Next Phase Readiness

- The modern CLI interface and stream isolation are fully verified and tested.
- Ready to proceed to **Phase 4: Programmatic Pipeline Orchestration** to enable in-memory execution of the stage scripts without subprocess overhead.

---
*Phase: 03-structured-cli-interoperability*
*Completed: 2026-05-20*
