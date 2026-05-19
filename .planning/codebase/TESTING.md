# Testing Patterns

**Analysis Date:** 2026-05-19

## Test Framework

**Runner:**
- There is no traditional test suite (e.g. `pytest`, `unittest`) in this repository.
- Testing is split into two advanced paradigms:
  1. **Dynamic Runtime & Compilation Debugging (`4_debugging.py`):** An iterative Python compiler and execution loop that runs the generated code, captures standard error, and feeds logs back to the LLM for self-correction.
  2. **LLM-Based Evaluation Scorecard (`eval.py`):** An LLM-in-the-loop evaluator that grades the generated codebase against the paper's specs (`ref_free`) or a gold-standard reference repository (`ref_based`).

## Run Commands

**Orchestrated Pipeline Execution:**
```bash
# Run the complete generation & compilation pipeline
uv run bash scripts/run.sh
```

**Evaluation Execution:**
```bash
# Run reference-free evaluation
uv run python codes/eval.py \
  --paper_name Transformer \
  --pdf_json_path examples/Transformer_cleaned.json \
  --output_dir data/paper2code/Transformer/gpt-4o \
  --target_repo_dir data/paper2code/Transformer/gpt-4o/Transformer_repo \
  --eval_result_dir data/paper2code/Transformer/gpt-4o \
  --gpt_version gpt-4o \
  --eval_type ref_free
```

## Debugging Loop Structure

**Iterative Compilation Validation (`4_debugging.py`):**
- **Syntax Check:** The script loads generated modules and runs basic python compilation checks:
  ```python
  # Abstract representation of compile check
  compile(source_code, filename, "exec")
  ```
- **Execution Trajectory Auditing:** If the generated project comes with execution shell commands or trajectories, they are executed in a safe subprocess wrapper:
  ```python
  # Subprocess runner inside debugging agent
  result = subprocess.run(["python", "-c", "import module; ..."], capture_output=True, text=True)
  ```
- **Dynamic Repair Feed:** In case of failure, standard error output is captured and sent back through `unified_api_call` with a patch prompt, generating a corrected diff file until compilation succeeds or retry limits are reached.

## Evaluation Archetypes

**Reference-Free (`ref_free`):**
- Compares generated repository files against the parsed JSON representation of the scientific paper.
- Uses `data/prompts/ref_free.txt` as the base instruction template.
- Scores the code on mathematical correctness, modular design, and completeness relative to the text.

**Reference-Based (`ref_based`):**
- Compares generated repository files against a ground-truth gold repository.
- Uses `data/prompts/ref_based.txt` as the base instruction template.
- Scores the code on exact API matching, configuration alignment, and architectural equivalence.

---

*Testing analysis: 2026-05-19*
