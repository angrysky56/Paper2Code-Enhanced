# Codebase Structure

**Analysis Date:** 2026-05-19

## Directory Layout

```
Paper2Code-Enhanced/
├── .planning/          # GSD planning and design specifications
│   └── codebase/      # Codebase architectural and structural maps
├── assets/             # Media and images used in documentation
├── codes/              # Source code for pipeline execution scripts (agents)
│   └── utils.py       # Core utility functions and LLM integration client
├── data/               # Configuration data and evaluation prompts
│   ├── paper2code/    # Output folder for generated repos and trajectories
│   └── prompts/       # Evaluation templates for ref-free and ref-based UAT
├── examples/           # Sample input files (e.g. Transformer JSON/PDF/TEX)
├── scripts/            # Orchestrator shell scripts
├── pyproject.toml      # Modern `uv` dependency declaration
├── uv.lock             # Modern `uv` lockfile
├── .env.example        # Reference environment configuration
└── README.md           # Getting started and pipeline documentation
```

## Directory Purposes

**.planning/codebase/**
- Purpose: Architecture, Stack, Structure, Integration, Conventions, Testing, and Concerns definitions.
- Contains: Markdown documents mapped during codebase analysis.

**codes/**
- Purpose: Core Python scripts carrying out agent workflows.
- Contains:
  - `0_pdf_process.py` - Processes raw PDF content into raw text/structures.
  - `1_planning.py` / `1_planning_llm.py` - Synthesizes high-level developer design documents.
  - `1.1_extract_config.py` / `1.2_rag_config.py` - Context extraction and RAG search tuning.
  - `2_analyzing.py` / `2_analyzing_llm.py` - Pinpoints dependencies, schemas, and components.
  - `3_coding.py` / `3.1_coding_sh.py` - Generates individual code files and writes trajectories.
  - `4_debugging.py` - Audits, tests, and iteratively repairs compilation/syntax issues.
  - `eval.py` - Reference-based and reference-free scoring.
  - `utils.py` - Central gateway module for LLM interaction and pricing/token utilities.

**data/prompts/**
- Purpose: Prompt definitions for evaluation.
- Key files:
  - `ref_based.txt` - Prompt for evaluating output code using a ground truth reference code.
  - `ref_free.txt` - Prompt for evaluating output code independently based on requirements.

**examples/**
- Purpose: Initial dataset resources used to demonstrate, test, and run the pipeline.
- Contains:
  - `Transformer.pdf` - Original attention paper.
  - `Transformer.json` - Segmented raw paper JSON representation.
  - `Transformer_cleaned.json` / `Transformer_cleaned.tex` - Extracted tex syntax blocks.

**scripts/**
- Purpose: Automated terminal command sequences.
- Contains:
  - `run.sh` - Main runner scripting standard OpenAI completion formats.
  - `run_llm.sh` - Runner prioritizing custom open-source local server configurations.
  - `run_latex.sh` - Execution script utilizing LaTeX input documents directly.
  - `run_latex_llm.sh` - Execution script chaining LaTeX ingestion with LLM endpoints.

## Key File Locations

**Entry Points:**
- `scripts/run.sh`: Main entry shell runner for standard datasets.
- `scripts/run_latex.sh`: LaTeX parser runner pipeline.

**Configuration:**
- `pyproject.toml`: Dependency settings.
- `uv.lock`: Package lock tracking.
- `.env.example`: Template for environment setups.

**Core Logic:**
- `codes/utils.py`: Contains the `unified_api_call` routing wrapper.

**Testing & Evaluation:**
- `codes/eval.py`: Calculates trajectory fidelity scorecard.

## Naming Conventions

**Files:**
- `X.Y_camelCase.py` / `X_camelCase.py`: Step-numbered python code.
- `snake_case.py` / `snake_case.sh` / `snake_case.txt`: Helper files, shell scripts, and text files.

**Directories:**
- `snake_case`: Standard organization namespaces.

## Where to Add New Code

**Adding new agent pipeline phase:**
- Script: Create numbered python file in `codes/` (e.g. `codes/5_polishing.py`).
- Utilities: Bind custom helpers or pricing attributes to `codes/utils.py`.
- Execution: Append step call inside `scripts/run.sh`.

**Adding evaluation templates:**
- Path: `data/prompts/`

---

*Structure analysis: 2026-05-19*
