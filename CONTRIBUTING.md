<!-- generated-by: gsd-doc-writer -->
# 🤝 Contributing to Paper2Code-Enhanced

We are thrilled that you want to contribute to **Paper2Code-Enhanced**! Whether you are helping to refine our persistent SQLModel auditing layer, improving the sandboxed `DockerExecutor`, or tuning RLM debugging convergence models, your help is highly appreciated.

---

## 🛠️ Development Setup

To get your workspace configured, please refer to our dedicated guides rather than duplicate their contents:
1.  See [GETTING-STARTED.md](docs/GETTING-STARTED.md) for quick-start installation, package synchronization using `uv`, and mock environment verification.
2.  See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for local dev commands, test execution details, and branch naming conventions.

---

## 🎨 Coding and Documentation Standards

All contributions must follow these primary rules to maintain the quality and reliability of the codebase:

*   **Type Safety**: Every new Python function and class must include complete, clear type annotations.
*   **Documentation Quality**: Add PEP 257-compliant docstrings to explain complex logic, reasoning loops, and module API boundaries.
*   **Decoupled Architecture**: Keep execution stages isolated. Stage scripts should write metadata through the `codes/db.py` write helpers rather than interacting with the database engine or models directly.
*   **No GSD References**: Ensure that any planning commits, `/gsd-` task files, or `PLAN.md`/`ROADMAP.md` internal workflow artifacts are not pushed to the repository or listed in documentation.

---

## 🚀 Pull Request (PR) Guidelines

When you are ready to submit a contribution, please ensure you satisfy this procedure:

1.  **Branch Conventions**: Name your branch using the appropriate prefix (`feat/`, `fix/`, `docs/`, `refactor/`).
2.  **Lint and Format**: Format your code before committing (e.g., using `black` or `ruff`).
3.  **Run Test Suite**: Run all tests via `uv run pytest` and ensure they pass.
4.  **Describe Changes**: In your PR description, explain *what* you changed, *why* the change was made, and *how* you verified it. Include terminal outputs or db_query tables if relevant.

---

## 🐛 Issue Reporting

If you encounter any bug, sandbox executor crash, or API rate limiting issues:
1.  Search our existing GitHub Issues list to see if the problem has already been reported.
2.  If creating a new issue, please include:
    *   **Environment Context**: Python version, `uv` configuration, OS, and LLM model selected.
    *   **Steps to Reproduce**: The exact CLI command or pipeline configuration that triggered the failure.
    *   **Tracebacks / Logs**: Copy-paste the relevant stderr stack traces or `ExecutionTrial` database reports to facilitate diagnosing.
