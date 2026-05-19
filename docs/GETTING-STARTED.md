<!-- generated-by: gsd-doc-writer -->
# 🚀 Getting Started

Welcome to **Paper2Code-Enhanced**! This guide will walk you through setting up your local environment and running your first machine learning paper-to-code generation.

---

## 📋 Prerequisites

Before you begin, ensure you have the following system requirements and software installed:

*   **Operating System**: Debian-based Linux (e.g., Pop!_OS, Ubuntu) or any modern Linux distribution.
*   **Python Runtime**: Python `>= 3.13` (managed via `uv` recommended).
*   **Package Manager**: `uv` (recommended for ultra-fast, clean environment synchronization).
*   **Containerization (Optional for Sandboxing)**: Docker (with NVIDIA container toolkit for GPU passthrough if running CUDA code).
*   **Database**: SQLite (built-in with Python, used for persistence).

---

## 🛠️ Installation Steps

Follow these steps to set up the codebase and verify the dependencies:

### 1. Clone the Repository
Clone this repository to your local workspace:
```bash
git clone https://github.com/going-doer/Paper2Code.git
cd Paper2Code
```

### 2. Synchronize Python Virtual Environment
Use `uv` to automatically create a virtual environment and install all lockfile dependencies:
```bash
# Install uv if you don't have it already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync packages defined in pyproject.toml
uv sync
```
*(Alternatively, you can install via `pip install -r requirements.txt`, though `uv` is highly recommended for reproducible runs.)*

### 3. Configure Environment Variables
Copy the `.env.example` template to `.env` and fill in your model configuration and API keys:
```bash
cp .env.example .env
```
Ensure you have configured:
*   `LLM_API_KEY` or `ANTHROPIC_API_KEY` (for MiniMax-M2.7 or OpenAI o3-mini)
*   `LLM_MODEL` (e.g., `MiniMax-M2.7` or `o3-mini`)
*   `DB_PATH` (defaults to `../outputs/paper2code.db`)
*   `EXECUTOR_TYPE` (`subprocess` or `docker`)

---

## ⚡ First Run

To verify that your installation is complete and the database persistence layer is working correctly, follow these steps:

### 1. Populate a Mock Database
Run the mock database population script to initialize the SQLite schema and insert analytics data:
```bash
uv run python tests/mock_db_populate.py
```

### 2. Inspect with the Analytics CLI
Query the database to confirm that the persistence layer is fully functional:
```bash
uv run python codes/db_query.py --stats
```
This should print a beautiful, styled analytics panel showing the mock runs, global resource footprint, and RLM debugging performance.

### 3. Execute a Sample Pipeline Run
To run the PaperCoder pipeline on the example **Attention Is All You Need** paper:
```bash
cd scripts
uv run bash run.sh
```

---

## 🩺 Common Setup Issues

Here are the most frequent issues encountered during initial setup and how to resolve them:

### 1. Model API Key Errors or Missing Env Variables
*   **Symptom**: `AuthenticationError` or `ApiKeyError` on pipeline execution.
*   **Solution**: Ensure you have loaded your environment variables. Run `source .env` or make sure `dotenv` is successfully parsing your local environment.

### 2. Docker Execution Permissions
*   **Symptom**: Sandbox executor fails to run or container creation fails with `PermissionDenied`.
*   **Solution**: Ensure your current user is in the `docker` group. Run `sudo usermod -aG docker $USER` and log out/in again to apply the changes.

### 3. SQLite Database Locked or Path Unreachable
*   **Symptom**: Database writes hang or throw `OperationalError: unable to open database file`.
*   **Solution**: Check that the parent directory of `DB_PATH` exists and is writable. The pipeline automatically attempts to create it, but restrictive system permissions can block it.

---

## 🗺️ Next Steps

Now that your environment is fully operational, dive deeper with these guides:

*   **System Architecture**: Understand the system components and key abstractions in [ARCHITECTURE.md](ARCHITECTURE.md).
*   **Development Guide**: Learn about branch naming, linting, formatting, and codebase contributions in [DEVELOPMENT.md](DEVELOPMENT.md).
*   **Testing Suites**: Discover how to run and write unit and schema tests in [TESTING.md](TESTING.md).
*   **Configuration Schema**: Read details about all environment variables and options in [CONFIGURATION.md](CONFIGURATION.md).
