# Codebase Concerns

**Analysis Date:** 2026-05-19

## Tech Debt

**API Completion Parameter Standardization:**
- Issue: Custom params like `reasoning_effort` (specific to OpenAI o-series) are passed straight to standard LLM endpoints.
- File: `codes/utils.py` (inside `unified_api_call`)
- Why: Rapid integration of new models without building custom payload sanitizers per endpoint.
- Impact: Non-OpenAI providers (including Anthropic/MiniMax) will fail or throw errors if unrecognized parameters are present in the payload.
- Fix approach: Sanitize the `kwargs` payload in `unified_api_call` to filter out `reasoning_effort` and other model-exclusive attributes before routing to providers that do not support them.

**Fragile Markdown/JSON Extraction Regexes:**
- Issue: String parsers rely heavily on strict markdown backticks and regular expressions.
- File: `codes/utils.py` (inside `extract_json_from_string` and parsing helpers)
- Why: Easy string matching assuming correct structural formatting by LLM.
- Impact: If the LLM returns trailing text, slightly malformed JSON syntax, or doesn't close code fences properly, extraction will fail or raise parsing exceptions.
- Fix approach: Integrate robust, fault-tolerant parsers (like `json-repair`) to clean and decode LLM-returned JSON strings automatically.

## Known Bugs

- None currently active.

## Security Considerations

**Unsafe Code Execution during Debugging:**
- Risk: The Debugging Agent executes generated python files locally in a subprocess. If the scientific paper contains or triggers instructions that perform file deletions, system calls, or network downloads, they will run natively on the developer's host machine.
- File: `codes/4_debugging.py`
- Current mitigation: None.
- Recommendations: Execute generated script validation loops inside isolated sandboxes (Docker, WebAssembly, or firewalled sandboxed runtimes) instead of the bare host environment.

## Performance Bottlenecks

**Context Size Bloat:**
- Problem: Injecting large, raw paper PDFs or parsed LaTeX files directly into the prompt.
- Measurement: 10k-80k tokens per prompt depending on paper length.
- Cause: Chaining entire parsed paper structures across all agents instead of executing segmented RAG retrievals.
- Improvement path: Leverage the configuration extractor (`codes/1.1_extract_config.py` and `codes/1.2_rag_config.py`) to summarize and retrieve only relevant context segments for the Coding/Debugging steps.

## Fragile Areas

**Sequential Pipeline Coupling:**
- File: `scripts/run.sh`
- Why fragile: High coupling between consecutive steps. If step 1 fails, step 2 cannot run due to missing planning artifact outputs.
- Common failures: Rate limits or network dropouts halt execution completely without checkpoint resume options.
- Safe modification: Implement check-pointing so scripts can resume from the last successfully written JSON artifact.

## Scaling Limits

**MiniMax/Commercial Rate Limits:**
- Current capacity: Dependent on API Key tier limits (typically 3-10 RPM for reasoning APIs).
- Symptoms at limit: `429 Rate Limit Exceeded` exceptions.
- Scaling path: Implement exponential backoff retries within the `unified_api_call` wrapper to survive high concurrency or transient rate-limiting spikes.

---

*Concerns audit: 2026-05-19*
