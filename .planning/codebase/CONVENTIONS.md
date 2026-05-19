# Coding Conventions

**Analysis Date:** 2026-05-19

## Naming Patterns

**Files:**
- Step-prefixed snake_case names for execution agents (e.g. `1_planning.py`, `3.1_coding_sh.py`).
- Lowercase snake_case for general utility files (e.g. `utils.py`, `eval.py`).

**Functions:**
- Lowercase snake_case for all functions (e.g. `unified_api_call`, `convert_to_anthropic_messages`).
- Meaningful verb prefixes (e.g. `load_`, `extract_`, `get_`, `parse_`).

**Variables:**
- Lowercase snake_case for standard variables (e.g. `model_name`, `thinking_block`).
- UPPERCASE_SNAKE_CASE for constants (e.g. `OPENAI_PRICING`, `MINIMAX_PRICING`).

## Code Style

**Formatting:**
- Standard Python 4-space indentation.
- Double quotes for string literals, especially when containing nested JSON keys or CLI flags.
- Max line length generally targeted at 100 characters.

**Linting:**
- Handled via Ruff/Black-compatible standard formatting when run via `uv`.

## Import Organization

**Order:**
1. Standard library imports (e.g. `os`, `sys`, `json`, `time`, `re`).
2. Third-party packages (e.g. `openai`, `anthropic`, `dotenv`, `tiktoken`).
3. Local utilities (e.g. `from utils import ...`).

**Path Aliases:**
- Standard direct directory imports (e.g. `import utils` when inside the `codes/` execution context).

## Error Handling

**Patterns:**
- Core API exceptions (OpenAI APIError, Anthropic APIError) are caught using target-specific try-catch wrappers, printing descriptive error logs to stdout.
- Program compilation or formatting errors are captured, parsed, and fed back into debugging prompts inside `4_debugging.py` rather than halting execution.

**Logging:**
- Styled stdout logging with bold/colored console headers.
- Persistent logging of agent trajectories and code modifications inside local JSON files under `outputs/`.
- Consolidated cost tracking written into `accumulated_cost.json`.

---

*Convention analysis: 2026-05-19*
