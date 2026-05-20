# Paper2Code-Enhanced

## What This Is

Paper2Code-Enhanced is a modernized, robust paper-to-code reasoning pipeline designed to parse deep learning research papers (JSON or LaTeX format) and automatically generate, compile, and self-debug working PyTorch source code. It is designed to act as a core domain in a larger agentic ecosystem, created via `meta-harness` and optimized/executed by `OrCAID` and a `hermes` agent harness.

## Core Value

Automate the conversion of research papers into compilation-clean, production-ready PyTorch implementations using a safe, persisted, and meta-harness-interoperable agentic reasoning pipeline.

## Requirements

### Validated

- ✓ **LLM-01**: Centralized unified LLM client interface (`unified_api_call` in `codes/utils.py`) supports runtime routing to OpenAI, Anthropic, and MiniMax endpoints.
- ✓ **LLM-02**: Native Anthropic SDK support for MiniMax M2.7 thinking blocks to preserve downstream reasoning transparency.
- ✓ **ENV-01**: Centralized virtual environment and dependency management powered by `uv`.
- ✓ **EXEC-01**: SubprocessExecutor sets memory boundaries using the Linux `resource` module when memory limits are specified.
- ✓ **EXEC-02**: DockerExecutor provides isolated containerized execution with mount support and optional NVIDIA GPU capabilities.
- ✓ **EXEC-03**: The pipeline's self-debugging loop (`4_debugging.py`) runs generated code exclusively through sandboxed executors rather than raw local subprocesses.
- ✓ **DB-01**: SQLModel-based SQLite database schemas capture `Run`, `StageResult`, and `ExecutionTrial` rows.
- ✓ **DB-02**: Main stage scripts (`1_planning.py`, `2_analyzing.py`, `3_coding.py`, `4_debugging.py`) write progress, tokens, costs, and trial results to the database.
- ✓ **DB-03**: Idempotent run initialization detects incomplete runs to enable resume-on-failure.
- ✓ **DB-04**: DB query utilities provide insight into historical runs and Reasoning Loop Methodology (RLM) efficiency.
- ✓ **CLI-01**: Pipeline CLI supports `--output-format json` which redirects debugging logs to `stderr` and dumps final execution statistics as clean machine-readable JSON to `stdout` for `meta-harness` ingestion.
- ✓ **CLI-02**: CLI supports executing subsets of stages (e.g. `--stages coding,debugging`) and runtime model overrides.

### Active

<!-- Current scope: Modernization & Refinement Milestone -->

#### Phase 4: Programmatic Pipeline Orchestration
- [ ] **PIPE-01**: `pipeline.py` integrates all reasoning stage functions in-memory, avoiding subprocess spawning overhead.
- [ ] **PIPE-02**: The project registers as a global CLI (`paper2code`) under `console_scripts` in `pyproject.toml`.

### Out of Scope

- **PDF Visual Layout Parsing** — Defer to downstream tools; input is assumed to be parsed LaTeX or structured JSON.
- **Multilingual Support** — Limited to English research papers for the initial release.

## Context

- **Technical Ecosystem**: Python 3.13+, `uv` for dependency/project virtual environment management.
- **Agent Ecosystem**: Intended to be invoked as a domain task by `meta-harness`, and audited/orchestrated by `OrCAID` and `hermes` agent harnesses.
- **Database**: Local SQLite database located at `DB_PATH` in `.env` (default: `outputs/paper2code.db`).

## Constraints

- **Execution Safety**: Dynamic PyTorch execution must be strictly isolated to avoid code injection or system compromise on the host.
- **Interoperability**: Strict split of logs (`stderr`) vs. outputs (`stdout`) in JSON mode to prevent parser poisoning in downstream harnesses.
- **Performance**: Heavy model generation requires cost and token tracking across all API calls.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Native Anthropic SDK for MiniMax | Bypasses LiteLLM middleware to ensure perfect capture of `<thinking>` blocks | ✓ Good |
| SQLModel for Persistence | Combines SQLAlchemy ORM with Pydantic type safety for lightweight SQLite access | ✓ Completed |
| Dual Sandboxed Executors | Provides Subprocess (speed/local) and Docker (isolation/GPU) execution strategies | ✓ Completed |
| Stream Isolation for CLI Interop | Diverts diagnostic logs to stderr to keep stdout purely for structured JSON | ✓ Completed |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-20 after Phase 3 completion*
