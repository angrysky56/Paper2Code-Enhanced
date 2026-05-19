# Technology Stack

**Analysis Date:** 2026-05-19

## Languages

**Primary:**
- Python (>=3.13) - All core multi-agent execution pipeline logic, utilities, and scripts under `codes/`.

**Secondary:**
- Bash / Shell - Runner scripts and setup automation under `scripts/`.

## Runtime

**Environment:**
- Python Virtual Environment, isolated locally in `.venv/`.
- Direct script-based execution (CLI).

**Package Manager:**
- `uv` (>=0.1.0) - Modern high-performance Python package manager.
- Package file: `pyproject.toml`
- Lockfile: `uv.lock` present

## Frameworks

**Core:**
- None (Standalone modular script architecture)

**Testing:**
- None configured in core.

**Build/Dev:**
- None required. Run natively using `uv run python`.

## Key Dependencies

**Critical:**
- `openai` (>=1.65.4) - OpenAI API client for standard model interaction.
- `anthropic` (>=0.103.1) - Anthropic SDK client specifically used to natively connect to MiniMax M2.7 endpoints and process thinking blocks.
- `python-dotenv` (>=1.2.2) - Loads environment variables from a local `.env` file.
- `tiktoken` (>=0.9.0) - Performs precise input/output token counting for LLM billing tracking.
- `transformers` (>=5.0.0) - Local tokenizers and neural network utilities.
- `vllm` (>=0.20.0) - Supports running large open-source language models locally.

## Configuration

**Environment:**
- Configured via a `.env` file in the workspace root.
- Required configurations:
  - `LLM_API_KEY` - Fallback standard API Key.
  - `LLM_MODEL` - Active LLM name (e.g. `o3-mini`, `MiniMax-M2.7`).
  - `LLM_BASE_URL` - Optional OpenAI API fallback base URL.
  - `LLM_TEMPERATURE` - Control generation temperature.
  - `LLM_REASONING_EFFORT` - Specific parameters for o-series models.
  - `ANTHROPIC_API_KEY` - MiniMax API key.
  - `ANTHROPIC_BASE_URL` - MiniMax Anthropic-compatible API endpoint (`https://api.minimax.io/anthropic`).

## Platform Requirements

**Development:**
- Linux / macOS (tested on Pop!_OS and Ubuntu).
- Python 3.13 or newer.
- Git for version tracking.

---

*Stack analysis: 2026-05-19*
