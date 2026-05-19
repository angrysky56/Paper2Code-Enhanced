# External Integrations

**Analysis Date:** 2026-05-19

## APIs & External Services

**LLM Providers (Commercial):**
- **OpenAI API** - Used for planning, analysis, coding, debugging, and evaluation stages.
  - SDK/Client: `openai` Python SDK (v1.65.x)
  - Auth: API key stored in `OPENAI_API_KEY` or `LLM_API_KEY` environment variables.
  - Endpoints used: Chat Completions API (`v1/chat/completions`).
- **MiniMax API** - Optimized reasoning model interface for planning, analyzing, coding, and debugging.
  - SDK/Client: `anthropic` Python SDK (v0.103.x) targeting the Anthropic-compatible MiniMax endpoint.
  - Auth: API key stored in `ANTHROPIC_API_KEY` or `LLM_API_KEY`.
  - Endpoint: `https://api.minimax.io/anthropic` (overridden via `ANTHROPIC_BASE_URL` or `LLM_BASE_URL` env vars).

**LLM Providers (Local/Open Source):**
- **vLLM / Hugging Face local servers** - Run open-source models like DeepSeek Coder.
  - SDK/Client: `openai` Python SDK (pointing to local endpoint) and `transformers` SDK.
  - Connection: via custom `LLM_BASE_URL` (e.g. `http://localhost:8000/v1`).
  - Auth: Custom token or key if authentication is enabled on local port.

## Data Storage

**Databases:**
- None (File-based storage only).

**File Storage:**
- All artifacts, trajectories, plans, and output code repositories are written directly to the local filesystem:
  - `outputs/{paper_name}/` - Contains planning, analyzing, and coding JSON files and reports.
  - `outputs/{paper_name}_repo/` - The generated repository itself.
  - `outputs/{paper_name}/accumulated_cost.json` - Tracking of overall API usage and pricing metrics.

## Authentication & Identity

- None (Single-user CLI/script execution context, authorization keys loaded via environment variables).

## Monitoring & Observability

- **Console Logging / Cost Tracking** - Real-time tracking of token counts (input/cached/output tokens) and financial costs.
  - Tooling: custom calculations inside `codes/utils.py` leveraging precise multipliers per model.
  - Storage: persisted across stages in `outputs/{paper_name}/accumulated_cost.json`.

## CI/CD & Deployment

- **Version Control:** Managed via local Git repository.
- **Dependency Management & Sync:** Handled via `uv sync` locally.

## Environment Configuration

**Development & Production:**
- Environment variables are read from a gitignored `.env` file in the workspace root.
- Required variables:
  - `LLM_API_KEY` / `OPENAI_API_KEY`
  - `LLM_MODEL`
  - `LLM_BASE_URL` (optional)
  - `LLM_TEMPERATURE` (optional)
  - `LLM_REASONING_EFFORT` (optional)
  - `ANTHROPIC_API_KEY` (optional)
  - `ANTHROPIC_BASE_URL` (optional)
- Example configuration file provided in `.env.example`.

---

*Integration audit: 2026-05-19*
