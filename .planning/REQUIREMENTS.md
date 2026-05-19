# Requirements: Paper2Code-Enhanced Modernization

**Defined:** 2026-05-19
**Core Value:** Automate the conversion of research papers into compilation-clean, production-ready PyTorch implementations using a safe, persisted, and meta-harness-interoperability reasoning pipeline.

## v1 Requirements

### Sandboxed Code Execution (EXEC)

- [ ] **EXEC-01**: SubprocessExecutor sets memory boundaries using the Linux `resource` module when memory limits are specified.
- [ ] **EXEC-02**: DockerExecutor provides isolated containerized execution with mount support and optional NVIDIA GPU capabilities.
- [ ] **EXEC-03**: The pipeline's self-debugging loop (`4_debugging.py`) runs generated code exclusively through sandboxed executors rather than raw local subprocesses.

### Database Persistence & RLM Logging (DB)

- [ ] **DB-01**: SQLModel-based SQLite database schemas capture `Run`, `StageResult`, and `ExecutionTrial` rows.
- [ ] **DB-02**: Main stage scripts (`1_planning.py`, `2_analyzing.py`, `3_coding.py`, `4_debugging.py`) write progress, tokens, costs, and trial results to the database.
- [ ] **DB-03**: Idempotent run initialization detects incomplete runs to enable resume-on-failure.
- [ ] **DB-04**: DB query utilities provide insight into historical runs and Reasoning Loop Methodology (RLM) efficiency.

### Structured CLI Interoperability (CLI)

- [ ] **CLI-01**: Pipeline CLI supports `--output-format json` which redirects debugging logs to `stderr` and dumps final execution statistics as clean machine-readable JSON to `stdout` for `meta-harness` ingestion.
- [ ] **CLI-02**: CLI supports executing subsets of stages (e.g. `--stages coding,debugging`) and runtime model overrides.

### Programmatic Pipeline Orchestration (PIPE)

- [ ] **PIPE-01**: `pipeline.py` integrates all reasoning stage functions in-memory, avoiding subprocess spawning overhead.
- [ ] **PIPE-02**: The project registers as a global CLI (`paper2code`) under `console_scripts` in `pyproject.toml`.

## v2 Requirements

### Analytics & Dashboard

- **ANLT-01**: Web-based frontend dashboard for viewing historical execution runs, cost summaries, and code-patch convergence rates.
- **ANLT-02**: Visual comparison of patch trials across different LLM backends (OpenAI, Anthropic, MiniMax).

### Complex Multi-Repository Context

- **MREP-01**: Multi-repository tracking where generated code is automatically distributed across separate backend/frontend sub-repositories.

## Out of Scope

| Feature | Reason |
|---------|--------|
| PDF Visual Layout Parsing | Inputs are restricted to LaTeX sources or cleaned structured JSON. |
| Non-Python Target Code | The pipeline focuses exclusively on PyTorch and standard Python machine learning codebases. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXEC-01 | Phase 1 | Pending |
| EXEC-02 | Phase 1 | Pending |
| EXEC-03 | Phase 1 | Pending |
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| DB-04 | Phase 2 | Pending |
| CLI-01 | Phase 3 | Pending |
| CLI-02 | Phase 3 | Pending |
| PIPE-01 | Phase 4 | Pending |
| PIPE-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-19*
*Last updated: 2026-05-19 after initial definition*
