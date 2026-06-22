# Personal Facts Guardrails — Campaign Proof Packet

## Purpose

This document records the current state of the Personal Facts Guardrails campaign: what was built, what is proven by tests, what is deferred, and what the next steps are. It is a proof-of-completion boundary, not a release claim. It does not change runtime behavior.

## Campaign status

- **Campaign**: Personal Facts Guardrails (per `docs/Campaign/personal-facts-guardrails-campaign-index.md`)
- **Status**: core loop complete; explicit override lane implemented; ready for PR review or live validation
- **Branch**: `personal-facts-guardrails`
- **Last updated**: 2026-06-22

## What was built

### 1. Architecture doctrine (docs-only)

| Document | Purpose |
|---|---|
| `docs/Campaign/personal-facts-guardrails-campaign-index.md` | Campaign scope, guardrail domains, proposed task sequence, invariants |
| `docs/architecture/personal-facts-guardrails-contract.md` | Canonical candidate-policy contract: lifecycle, source-role policy, candidate shape policy, reason taxonomy, promotion eligibility, runtime eligibility, evidence requirements, import-aware policy, UI review policy, override semantics |
| `docs/architecture/scout-vault-operator-surface-baseline.md` | Six-tab navigation baseline — defers Activity surfaces so campaign stays scoped |

### 2. Backend guardrail infrastructure

| Module | What it provides |
|---|---|
| `guardian/personal_facts/__init__.py` | Package marker |
| `guardian/personal_facts/guardrail_tokens.py` | 15 canonical `GuardrailReason` enum values |
| `guardian/personal_facts/guardrail_policy.py` | `classify_personal_fact_candidate()` — pure classifier with shape, source-role, evidence, confidence, import-noise, and sensitive-claim checks |
| `guardian/db/models.py` | `guardrail_metadata` JSONB column on `PersonalFact` |
| Alembic migration `a3b4c5d6e7f8` | Adds/drops `guardrail_metadata` column |

### 3. Import candidate guardrails

| Integration point | What it does |
|---|---|
| `backend/rag/chatgpt_migration.py` | `_classify_import_candidates()` classifies and filters candidates at persistence boundary; discard candidates are skipped; quarantine/reviewable candidates carry `_guardrail_*` metadata |
| `backend/rag/personal_fact_extraction.py` | `_extract_guardrail_metadata()` builds persistence payload from classifier output; `persist_personal_fact_candidates()` passes it to `create_fact()` |

### 4. Approval guardrails

| Route / helper | What it enforces |
|---|---|
| `guardian/routes/personal_facts.py` | `_is_guardrail_approval_blocked()` blocks direct approval for promotion-blocked candidates; `_is_guardrail_override_allowed()` validates explicit override intent; `approve_candidate()` enforces both gates |

### 5. Frontend review UI

| Component | What it shows |
|---|---|
| `FactCandidateReview.tsx` | `GuardrailBlock` renders disposition badge, promotion-blocked indicator, review-required indicator, runtime posture text, and reason labels; blocked notice and override reason input for promotion-blocked candidates; `override_guardrail` + `override_note` sent on override approval |

## What is proven by tests

### Backend test suites (5 files, 1,598 lines)

| Test file | Count | What it proves |
|---|---|---|
| `test_guardrail_policy.py` | 33 tests | Pure classifier: clean candidates survive, assistant-authored quarantined, ambiguous role blocked, fragment/shape detection, confidence non-override, prompt-like discard, all return `runtime_eligible=false` |
| `test_import_guardrail_integration.py` | 14 tests | Import boundary: `_classify_import_candidates` filters discards, attaches guardrail metadata to kept candidates, preserves original fields, handles mixed batches |
| `test_guardrail_persistence.py` | 11 tests | `_extract_guardrail_metadata`: correct shape, canonical tokens preserved, runtime_eligible always false, confidence non-override, missing/null returns None |
| `test_guardrail_approval.py` | 14 tests | `_is_guardrail_approval_blocked`: blocks `promotion_blocked=true`, blocks `source_role_assistant/ambiguous/system_like`, blocks `missing_evidence` and `quoted_or_hypothetical`, malformed metadata fails closed, clean candidates pass, non-blocking reasons don't block |
| `test_guardrail_override.py` | 12 tests | `_is_guardrail_override_allowed`: requires `override_guardrail=true` + edit or note, blocks malformed metadata, allows clean candidates, allows non-blocking metadata passthrough |

### Frontend test suite

| Test file | Count | What it proves |
|---|---|---|
| `FactCandidateReview.test.tsx` | 39 tests | Guardrail metadata rendering (disposition, blocked, review-required, runtime posture, reasons), missing/malformed metadata safety, override UI (blocked notice, override note input, `override_guardrail=true` payload, clean candidate preserves ordinary approve), cleanup actions remain available |

### Cross-suite consistency

- All 84 backend + 39 frontend tests pass.
- Protocol token tests (25) remain green.
- No existing Personal Facts route, CRUD, or import tests were broken.

## What is deferred

These tasks from the original campaign proposal remain unbuilt:

| Task | Status |
|---|---|
| Task 6: Import-aware regression proof with live imported-history fixtures | **Deferred** — requires Docker/Postgres/Redis environment or a test DB fixture not yet available |
| Task 7: Lifecycle proof for approve/edit/dispute/retire across all states | **Partially addressed** — approval gating is tested; dispute/reject/delete are confirmed available; full lifecycle state-machine tests are deferred |

These items from prior closeouts also remain deferred:

| Item | Status |
|---|---|
| Contradiction detection | Token exists (`contradiction_possible`) but no existing-fact comparison is implemented |
| Fact domain taxonomy validation | Token exists (`invalid_fact_domain`) but no domain registry is wired |
| Staleness heuristic | Token exists (`stale_or_time_sensitive`) but no timestamp-age check is implemented |
| Discard audit logging | Discarded candidates are silently dropped; no audit trail |
| Existing fact metadata update on reuse | When a candidate's key collides with an existing fact, new guardrail metadata is not backfilled |



## Decision point

The core guardrail loop is complete:

1. **Classify** — pure classifier with 15 canonical reason tokens ✅
2. **Persist** — guardrail metadata on candidate rows via JSONB column ✅
3. **Display** — review UI shows disposition, reasons, blocked status, runtime posture ✅
4. **Block** — direct approval rejected for promotion-blocked candidates ✅
5. **Override** — explicit override lane with edit + note requirement ✅

Two paths forward:

### Path A: Open PR from this branch

The branch is complete enough for review. The interleaved Scout baseline commits are harmless docs/UI work that don't conflict with the guardrails campaign. A single PR captures the full campaign arc.

### Path B: Create a clean PR branch later

Cherry-pick only the guardrails commits onto a fresh branch from `origin/main`. This produces a narrower PR but requires more git surgery. Do this after the proof packet lands if review hygiene demands it.

## Suggested next step

**Path A** — open a PR from `personal-facts-guardrails` into `main`. The campaign loop is closed enough to review. Live import validation (Task 6) and full lifecycle proof (Task 7) can be follow-up PRs without blocking this one.
