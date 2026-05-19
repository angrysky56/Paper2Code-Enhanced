<!-- generated-by: gsd-doc-writer -->
# ⚙️ Configuration

This document defines all configuration settings, environment variables, and execution modes for **Paper2Code-Enhanced**.

---

## 🔑 Environment Variables

The pipeline reads configuration variables from environment variables or from a local `.env` file situated in the project root.

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `LLM_MODEL` | Optional | `MiniMax-M2.7` | The model to use for all pipeline stages. Can be overridden with any Anthropic or OpenAI model (e.g., `o3-mini`, `o1`). |
| `ANTHROPIC_API_KEY` | Conditional | *None* | Required if utilizing the Anthropic SDK or MiniMax models. Represents the API authorization key. |
| `ANTHROPIC_BASE_URL`| Optional | `https://api.minimax.io/anthropic` | The base API gateway endpoint for MiniMax's Anthropic-compatible routing. |
| `OPENAI_API_KEY` | Conditional | *None* | Required if executing pipeline stages with OpenAI models (e.g., `o3-mini`, `o1-preview`). |
| `DB_PATH` | Optional | `../outputs/paper2code.db` | The filesystem path where the SQLite persistence database is created. |
| `EXECUTOR_TYPE` | Optional | `subprocess` | Sandbox execution sandbox type. Options are `subprocess` (local running) or `docker` (containerized isolation). |
| `DOCKER_IMAGE` | Optional | `python:3.11-slim` | The base docker container image to spin up for code execution sandboxing if `docker` executor is selected. |

---

## 📄 Config File Formats

Beyond environment variables, the Paper2Code-Enhanced system utilizes YAML and JSON configs during intermediate stage processes:

### 1. Planning Configurations
The `1.1_extract_config.py` stage extracts config attributes directly from the ML papers and saves them in the output directories (e.g., `outputs/Transformer/planning_artifacts/`). These specify model hyperparameters, architectures, optimizer configs, and training variables that are injected during later code writing.

### 2. accumulated_cost.json
Logged inside the individual paper run folders, this JSON tracking file acts as a legacy cost-aggregator for stages prior to the SQLModel database persistence layer.

---

## 🚨 Required vs. Optional Settings

*   **API Authentication**: You must provide *either* `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` depending on the model chosen in `LLM_MODEL`. Failure to do so will cause immediate stage crashes with missing API key exceptions.
*   **Database Initializing**: The database engine automatically creates the SQLite file at `DB_PATH`. Ensure the parent folder has appropriate write permissions.

---

## 🔄 Per-Environment Overrides

To easily configure different targets (development vs. production runs):
1.  **Development**: Keep `EXECUTOR_TYPE` as `subprocess` to speed up initial stage testing, and point `DB_PATH` to a test file (e.g. `outputs/test.db`).
2.  **Production / Batch Runs**: Set `EXECUTOR_TYPE` to `docker` to enforce secure sandboxed isolation on CUDA-enabled servers, and use a production-grade database location to persist runs for the analytics CLI dashboard.
