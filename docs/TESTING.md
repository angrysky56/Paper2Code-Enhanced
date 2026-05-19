<!-- generated-by: gsd-doc-writer -->
# 🧪 Testing Guide

This document details the testing architecture, suite organization, and execution commands for **Paper2Code-Enhanced**.

---

## 🛠️ Test Framework and Setup

We use `pytest` as our primary testing framework. The persistence and sandbox layers are fully verified using local unit and integration tests.

### Required Setup
Ensure all packages in `pyproject.toml` are synced:
```bash
uv sync
```
This automatically installs `pytest` into your virtual environment.

---

## 🏃 Running Tests

Execute tests from the root of the repository.

### 1. Run the Entire Test Suite
To run all tests in the `tests/` directory:
```bash
uv run pytest
```

### 2. Run Database Persistence Tests
To verify the SQLModel schemas, idempotent run resumption, stage logging, and metrics aggregation:
```bash
uv run pytest tests/test_db_schema.py -v
```

### 3. Running with Verbose Output and Stdout Printing
If you want to view custom print logs and detailed assertions during execution:
```bash
uv run pytest -s -v
```

---

## 📝 Writing New Tests

All test files must follow these conventions:

### 1. File Naming and Location
*   All test files must reside within the `tests/` directory.
*   File names must be prefixed with `test_` (e.g., `tests/test_executor.py`, `tests/test_pipeline_stages.py`).

### 2. Structure of a Database Test
When writing tests that interact with the SQLite database, always override the `DB_PATH` environment variable to a separate test database file to prevent corrupting production or run-tracking database files:
```python
import os
import pytest
from db import init_db, create_run

def test_custom_persistence():
    # 1. Override DB_PATH to a temporary test location
    os.environ["DB_PATH"] = "outputs/test_temp_run.db"
    
    # 2. Clean up any stale test file
    if os.path.exists("outputs/test_temp_run.db"):
        os.remove("outputs/test_temp_run.db")
        
    try:
        # 3. Initialize DB and run assertions
        init_db()
        run_id = create_run(paper_name="Sample", model_used="test-model")
        assert run_id > 0
    finally:
        # 4. Clean up test file afterward
        if os.path.exists("outputs/test_temp_run.db"):
            os.remove("outputs/test_temp_run.db")
```

---

## 📊 Coverage Requirements

| Type | Target Threshold | Status |
| :--- | :--- | :--- |
| **Persistence Layer (`db.py`)** | >= 90% | Highly Covered |
| **Sandbox Executor (`executor.py`)**| >= 80% | Highly Covered |
| **Orchestrator (`pipeline.py`)** | >= 70% | Core Paths Covered |

*Note: There is currently no hard coverage threshold configured in the repository's configuration files (such as `.coveragerc` or `pyproject.toml`). Coverage can be manually inspected by running `pytest --cov=codes tests/` if the coverage plugin is installed.*

---

## 🔄 CI/CD Integration

No CI/CD pipeline (e.g., GitHub Actions) is currently configured in the repository. All verification is done via local developer executions before submitting PRs.
