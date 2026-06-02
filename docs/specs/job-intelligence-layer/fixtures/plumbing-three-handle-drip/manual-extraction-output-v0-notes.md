# Manual Extraction Output v0 Notes

This is a docs-local, synthetic-only, manual, non-runtime sample artifact.
It references `source-interaction.txt` and `prompts/extraction-v0.md`, and it
can be checked with `scripts/job_intelligence/validate_extraction_output.py`.
This output is not operational truth, not model-quality proof, not production
readiness proof, and no real customer data was used.

## Purpose

The manual extraction output exists as a captured sample for future comparison
between prompt-shaped extraction output and the expected extraction artifact.
It gives the proof lane one concrete manual sample while keeping prompt
execution and model behavior outside the current task.

## Comparison Posture

- `expected-extraction.json` remains the docs-local expected fixture artifact.
- `manual-extraction-output-v0.json` is an experimental sample.
- The manual sample may be compared to expected extraction in future tasks.
- This sample can now be compared to `expected-extraction.json` with `scripts/job_intelligence/compare_extraction_outputs.py`.
- The comparison is field-level only.
- It is not semantic grading.
- It is not model-quality proof.

## Safety Boundary

- no real customer data
- no pricing commitments
- no dispatch commitments
- no subjective customer labels
- no sensitive trait inference
- human review remains required

## Non-Goals

- no model execution
- no prompt registry integration
- no automated prompt execution
- no output comparison harness
- no canonical schema
- no runtime behavior
- no persistence
- no review UI
- no transcription, consent, or retention policy
- no pricing automation
- no dispatch automation

## Open Questions

- Should manual samples be retained after automated model-output capture exists?
- Should future samples be grouped by prompt version?
- Should sample comparison be exact, semantic, or field-level?
- Should the next task add a deterministic comparison script?
- What delta from expected extraction is acceptable for prompt iteration?
