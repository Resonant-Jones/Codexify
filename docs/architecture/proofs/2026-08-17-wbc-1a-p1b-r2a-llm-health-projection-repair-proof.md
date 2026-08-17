# WBC-1A-P1B-R2A — Canonical LLM-health projection repair

## Purpose and parent boundary

WBC-1A-P1B-R2 reached supported-runtime readiness on literal canonical `main`, but its canonical receipt failed because the collector read obsolete top-level LLM-health projections. This task repairs only that collector projection. It does not requalify the runtime, run a chat lifecycle, or alter the historical P1B-R2 proof.

| Parent observation | Value |
| --- | --- |
| Parent result | blocked at the canonical live-proof collector's LLM-health projection |
| Parent receipt ID | `live-proof-receipt-sha256-abd45ed63208d1b4c4a31e013c0acafd08c5f1031105271669972f1c949827c9` |
| Receipt authority / outcome | `CANONICAL` / `FAIL` |
| Parent reason codes | `llm_models_unavailable`, `provider_runtime_unavailable` |

P1B-R2 independently observed a healthy local Whoosh'd runtime, selected local provider, and exactly one expected model, `qwen3.8-27b-4bit`. Direct `/api/health/llm` observation reported outer `status=ok`, `details.status=online`, available models, and an enabled provider runtime. The failed receipt therefore did not prove a local provider or model outage.

## Current LLM-health contract

Repository source and focused route tests establish `/api/health/llm` as a health envelope. Its outer `status` is the normalized envelope health status; the current LLM facts consumed by the collector are inside `details`:

| Receipt fact | Current field location |
| --- | --- |
| LLM operational status | `details.status` |
| LLM check result | `details.ok` |
| Models availability | `details.models_available` |
| Provider-runtime availability | `details.provider_runtime.enabled` |
| Supported profile | `details.supported_profile` |
| Release hold | outer `release_hold`, with `details.release_hold` and profile-level mirror when present |

The previous collector read `payload.get("models_available")` and `payload.get("provider_runtime")`. The former test fixture also represented that obsolete top-level-only shape. Current route tests instead assert the nested `details` envelope.

## Repair and compatibility posture

`_normalize_llm_health_projection()` is the single bounded normalization seam for the `api_health_llm` probe. It requires `details` to be an object and projects the current fields above into the unchanged receipt vocabulary: `models_available`, `provider_runtime_available`, supported-profile fields, release hold, and probe `ok`.

The accepted precedence is:

1. current canonical nested `details` fields;
2. no standalone top-level LLM-health fallback; and
3. unknown and fail closed when the current projection is absent or malformed.

Matching top-level model, runtime, or profile values may coexist as diagnostic mirrors, but never override the nested projection. A material disagreement between a mirror and the nested fact, or between release-hold mirrors, emits `llm_health_projection_ambiguous` and prevents an optimistic receipt. Missing or malformed nested facts emit `llm_health_projection_invalid`; they no longer misstate a missing legacy path as either model or provider unavailability. Explicit current `False` values still retain the established reason semantics: `llm_models_unavailable` for unavailable models and `provider_runtime_unavailable` for an unavailable provider runtime.

## Changed files

- `scripts/audit/collect_canonical_live_proof_receipt.py` adds the bounded LLM-health normalization/projection helper and uses it only for the fixed `api_health_llm` probe. It preserves the fixed probe set, canonical-authority derivation, Docker command allowlist, loopback checks, secret handling, deterministic receipt construction, and schema validation.
- `tests/audit/test_collect_canonical_live_proof_receipt.py` updates the normal healthy fixture to the actual nested current envelope and covers healthy nested data, explicit nested model/runtime unavailability, top-level-only rejection, contradictory mirror handling, and malformed nested data.

No Guardian route, provider/runtime code, model configuration, Compose/profile source, migration, receipt schema, ADR, Campaign artifact, release claim, or historical P1B-R2 proof changed.

## Focused proof

The focused collector module passed with 53 tests. Its new regression cases proved that:

| Case | Observed collector behavior |
| --- | --- |
| Healthy current nested envelope | `pass`, receipt outcome `PASS`, both availability facts `True`, no false unavailable reasons |
| Nested `models_available=false` | fails with `llm_models_unavailable` |
| Nested `provider_runtime.enabled=false` | fails with `provider_runtime_unavailable` |
| Top-level-only obsolete shape | fails closed with `llm_health_projection_invalid` |
| Contradictory nested/top-level model facts | fails closed with `llm_health_projection_ambiguous`; nested fact remains authoritative |
| Missing or malformed `details` projection | fails closed with `llm_health_projection_invalid`, without inventing an unavailable reason |

Existing passing collector coverage also constructs and validates a schema-valid receipt. The repaired healthy nested-envelope case preserves the same receipt field names and receives a `PASS` execution outcome.

## Validation and limitations

Commands executed from the repository root:

```text
.venv/bin/python -m pytest -v tests/audit/test_collect_canonical_live_proof_receipt.py
# 53 passed; one existing pytest configuration warning

.venv/bin/ruff check scripts/audit/collect_canonical_live_proof_receipt.py tests/audit/test_collect_canonical_live_proof_receipt.py
# reports only three pre-existing collector findings from cfd5bd9796:
# two unused E402 noqa directives and one broad Exception catch

.venv/bin/ruff check --ignore RUF100 --ignore BLE001 scripts/audit/collect_canonical_live_proof_receipt.py tests/audit/test_collect_canonical_live_proof_receipt.py
# passes; the repository's existing Ruff-configuration deprecation warning remains
```

The repository-pinned Black 23.3.0 was installed into the local virtual environment for validation. Its scoped `--check --diff` exits nonzero because both files contain pre-existing baseline-wide formatting differences, beginning before this repair; it would reformat many unrelated lines. No formatter was applied. `git diff --check`, the proof-artifact/result check, and `make PYTHON=.venv/bin/python docs` passed. Worktree scope was verified before staging only the three task-owned paths.

This is test evidence for an operator-truth collector repair on a branch that contains the historical P1B-R2 proof. It is not a new canonical-main runtime receipt. The repair must land on canonical `main`, then P1B-R2 must be rerun from a fresh clean literal-main checkout before WBC-1A can begin.

## ADR impact

Aligned with existing ADR(s): ADR-041 (VaultNode canonical machine and audit authority), ADR-042 (canonical audit evidence), ADR-052 (supported Whoosh'd provider profile boundary), and ADR-069 (local-only Beta support boundary). No architectural or release decision changed.

**Final result: `LLM_PROJECTION_REPAIR_PROVEN`**
