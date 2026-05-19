<!-- generated-by: gsd-doc-writer -->
# 🛠️ Development Guide

This guide is for developers looking to modify the Paper2Code-Enhanced codebase, add new pipeline stages, or improve persistence and sandboxed execution components.

---

## 💻 Local Setup for Development

To configure the repository for active development, follow these additional steps beyond the standard installation:

### 1. Set Up Dev Dependencies
When setting up your environment, make sure you have dev packages such as `pytest` and `black` installed. If you synchronize using `uv`, these are automatically managed under your environment.

### 2. Copy the Environment Configuration
Copy the sample environment file to configure your local test variables:
```bash
cp .env.example .env
```
For local dev and testing, you can override `DB_PATH` to point to a local sandbox database, like `outputs/test_paper2code.db`.

---

## ⚙️ Development and Build Commands

Since Paper2Code-Enhanced is a Python project, development tasks are run via `uv` or directly from the virtual environment:

| Task / Command | Description |
| :--- | :--- |
| `uv run python codes/pipeline.py` | Invokes the programmatic pipeline orchestrator. |
| `uv run python codes/db_query.py --stats` | Launches the terminal dashboard to view global metrics. |
| `uv run python codes/db_query.py --runs` | Displays detailed pipeline execution runs in a table. |
| `uv run pytest` | Runs the complete unit and integration test suite. |
| `uv run pytest tests/test_db_schema.py` | Runs isolated tests against the SQLModel persistence layer. |
| `uv run python tests/mock_db_populate.py` | Populates the database with realistic mock data for testing. |

---

## 🎨 Code Style and Quality Standards

We maintain high standards of code hygiene, readability, and type safety:

### 1. Type Hints and Annotations
*   All new functions, classes, and variables must include explicit **PEP 484 type hints**.
*   Import `annotations` from `__future__` at the top of files to support modern type syntax.
```python
from __future__ import annotations
from typing import Literal, Optional
```

### 2. Docstrings and Comments
*   Write clear, explanatory docstrings for all public modules, classes, and functions.
*   We use the **Google style** for docstrings:
```python
def create_run(
    paper_name: str,
    model_used: str,
    output_dir: str = "",
    executor_type: str = "subprocess",
) -> int:
    """
    Insert a new Run record and return its integer ID.

    Args:
        paper_name: The name of the scientific paper.
        model_used: The LLM model name.
        output_dir: Output directory path.
        executor_type: The sandbox execution mechanism.

    Returns:
        The generated unique integer ID of the Run.
    """
```

### 3. Linting and Formatting
*   We recommend linting your code before committing.
*   Format Python files using `black` or `ruff` to ensure a consistent, clean style.

---

## 🎋 Branch and Commit Conventions

To maintain a clean and readable git history, all developers must adhere to the following standards:

### 1. Branch Naming
Name branches clearly according to the type of work being done:
*   `feat/` — for new features (e.g., `feat/docker-gpu-passthrough`)
*   `fix/` — for bug fixes (e.g., `fix/sqlite-concurrent-writes`)
*   `docs/` — for documentation improvements (e.g., `docs/add-api-walkthrough`)
*   `refactor/` — for non-functional code changes (e.g., `refactor/executor-factory`)

### 2. Commit Messages (Conventional Commits)
All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:
```
<type>(<scope>): <description>

[optional body]
```
Example types:
*   `feat`: Add new feature or pipeline capability.
*   `fix`: Solve a bug or executor crash.
*   `docs`: Update documentation files or comments.
*   `refactor`: Rework code structure without altering external behavior.

---

## 🚀 Pull Request (PR) Process

Before submitting a Pull Request for review, ensure you have completed this checklist:

1.  **Format Verification**: Run your formatting tools to ensure compliance.
2.  **Test Execution**: Run `pytest` to make sure all existing tests pass.
3.  **Schema Consistency**: If you altered any SQLModel schemas in `codes/db.py`, write a corresponding test in `tests/` and verify that the migration path is clean.
4.  **No GSD References**: Ensure that no GSD methodology, phase details, or GSD CLI commands are committed to the codebase or documentation.
5.  **Submit PR**: Push your branch to GitHub and create a Pull Request detailing the changes, context, and verification steps.
