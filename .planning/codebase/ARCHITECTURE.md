# Architecture

**Analysis Date:** 2026-05-19

## Pattern Overview

**Overall:** Multi-Agent Script-Based Pipeline (Plan-Analyze-Code-Debug Pipeline).

**Key Characteristics:**
- **Sequential Stage Orchestration:** Execution moves through distinct, sequential phases where each agent writes its state to the filesystem.
- **File-Based State:** No database is used. The state passes from one script to the next via structured JSON files in `outputs/`.
- **Unified Client Interface:** All LLM calls are routed through a single entry point `unified_api_call` inside `codes/utils.py`, allowing transparent runtime switching between OpenAI and Anthropic SDK protocols.

## Layers

**Pipeline Script Layer (Agents):**
- Purpose: Orchestrate a specific phase of the codebase generation process.
- Location:
  - `codes/1_planning.py` - Planning Agent (sets up high-level implementation strategy).
  - `codes/2_analyzing.py` - Analysis Agent (identifies necessary algorithms, files, and classes).
  - `codes/3_coding.py` / `codes/3.1_coding_sh.py` - Coding Agent (generates files and trajectory scripts).
  - `codes/4_debugging.py` - Debugging Agent (iteratively audits and patches errors).
  - `codes/eval.py` - Evaluation Agent (runs reference-free and reference-based reviews).

**Utility & Core Interface Layer:**
- Purpose: Handle data processing, parsing, tokenization, cost calculations, and direct LLM API calls.
- Location: `codes/utils.py`
- Used by: All Pipeline Scripts.

**Shell Orchestration Layer:**
- Purpose: Execute and chain the sequential Python scripts with appropriate arguments.
- Location: `scripts/*.sh` (e.g., `scripts/run.sh`, `scripts/run_latex.sh`).

## Data Flow

**General Generation Pipeline:**

```
[Paper JSON/LaTeX]
       │
       ▼
 1_planning.py  ──► Writes outputs/{paper}/planning_artifacts/
       │
       ▼
 2_analyzing.py ──► Writes outputs/{paper}/analyzing_artifacts/
       │
       ▼
 3_coding.py    ──► Writes outputs/{paper}/coding_artifacts/ & drafts codes in outputs/{repo}/
       │
       ▼
 4_debugging.py ──► Runs verification & writes patches into outputs/{repo}/
```

**State Management:**
- **Stateless Modules:** Every python script runs in its own process.
- **Accumulated Costs:** The script `codes/utils.py` loads and updates `outputs/{paper}/accumulated_cost.json` at the end of each stage.

## Key Abstractions

**unified_api_call:**
- Purpose: Gateway function for all LLM completions. Switches between standard OpenAI and Anthropic clients, handles MiniMax routing, and parses native reasoning (`<thinking>`) blocks.
- Location: `codes/utils.py`

**MockCompletion / MockChoice / MockMessage:**
- Purpose: Wrap Anthropic message responses to look like standard OpenAI `chat.completions` objects so that downstream parsers remain compatible.
- Location: `codes/utils.py`

**convert_to_anthropic_messages:**
- Purpose: Standardize messages history arrays to support Anthropic API constraints (such as alternate role blocks and system prompt extraction).
- Location: `codes/utils.py`

## Entry Points

**Pipeline Shell Wrapper:**
- Location: `scripts/run.sh`
- Triggers: User execution via `uv run bash run.sh`.
- Responsibilities: Loads `.env` file, sets up the workspace, and runs python scripts sequentially.

**Evaluation Script:**
- Location: `codes/eval.py`
- Triggers: User execution via `uv run python eval.py`.
- Responsibilities: Measures code correctness compared to reference solutions.

## Error Handling

**Strategy:**
- Core script exceptions are caught and reported directly to the console.
- Generated code errors (syntax, import, structural issues) are actively caught in `4_debugging.py` by compiling and testing the output repository and using a separate LLM feedback loop to apply diff-patches dynamically.

## Cross-Cutting Concerns

**Token & Cost Accounting:**
- `load_accumulated_cost` and `update_accumulated_cost` calculate tokens using `tiktoken` (for OpenAI) and model-specific pricing dictionaries.

**Environment Loading:**
- All scripts load environment configuration using `load_dotenv()` from `python-dotenv`.

---

*Architecture analysis: 2026-05-19*
