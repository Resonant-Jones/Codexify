# C04 Decision Log: Pi/Coder Invocation Boundary

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C04-D001 | 2026-06-20 | `go` — C04 Pi/Coder invocation boundary seam audit complete; all Pi types are contract-only, no runtime execution found, 15 surfaces classified, 10 risks registered, 8-task backlog, C04-T002 next | active |

---

### Decision: C04-D001

- **Decision ID**: C04-D001
- **Date**: 2026-06-20
- **Decision**: `go`. C04 Pi/Coder invocation boundary seam audit complete. All Pi/Coder types exist as contract-only dataclasses/enums — no live Pi SDK calls, no Coder execution, no autonomous dispatch, no recursive tool loops. Agent orchestration route is a scaffold (creates deployment + run, delegates to worker). 15 surfaces inspected and classified. 10 risks registered. 8-task backlog defined. No backend, frontend, test, or runtime changes made. Release boundary preserved.
- **Reason**:
  - 17 search terms + 12 directories/files inspected across codebase.
  - `guardian/pi/`: contracts.py/tokens.py/validation.py — all contract-only, no execution.
  - `guardian/agents/coding_agent_contracts.py` — contract dataclasses only.
  - `guardian/routes/agent_orchestration.py` — scaffold route, not execution.
  - No Pi SDK calls, no Coder execution, no autonomous dispatch found anywhere.
  - No `tests/pi/` directory — no Pi-specific tests exist.
  - Frontend has no Pi/Coder execution controls.
  - C03/C05/C06 infrastructure is proven and available for C04 reuse.
  - 10 risks registered with severity + mitigation.
  - 8-task C04 backlog: contracts first, then UI, then integration proof.
- **Evidence**:
  - `seam-audit.md` — 17-section comprehensive audit.
  - `backlog.md` — 8-task sequence.
  - `proof-pack.md` — C04-T001 evidence.
- **Consequence**:
  - C04 campaign active. C04-T002 (acceptance contract) is next.
  - No Pi/Coder implementation until contracts are defined and gated.
  - All Pi/Coder types remain contract-only until governed implementation.
- **Revisit Trigger**:
  - C04-T002 acceptance contract defines governed behavior — revisit risk register.
  - Any new Pi SDK or Coder execution code appears in the codebase — re-audit.
  - C04-T005 result return governance — wire receipt linkage if C05 receipt linkage is completed.

---

### Decision: C04-D002

- **Decision ID**: C04-D002
- **Date**: 2026-06-20
- **Decision**: `go`. C04 Pi/Coder invocation boundary acceptance contract defined. 8-state acceptance model, 14 invocation boundary criteria, 18-row proof surface matrix, 13 prohibited acceptance shortcuts, 7 required runtime proof classes, result return/lineage requirements, receipt/artifact acceptance rules, operator surface acceptance rules, 12 fail-closed blocker rules. No runtime behavior changed. Release boundary preserved.
- **Reason**:
  - Acceptance contract governs all future C04 implementation tasks.
  - 8-state acceptance model from `not_started` through `operator_visible_read_only`.
  - 14 invocation boundary criteria: envelope, permission, policy ownership, command bus authority, result return, transcript lineage, source-message lineage, receipt, artifact, provider lane, Minimax, bounded failure, no recursion, no autonomous dispatch, no hidden writes.
  - 18-row proof surface matrix: minimum acceptable evidence, insufficient shortcuts, blocker conditions.
  - 13 prohibited shortcuts: docs, types, routes, scaffolds, pointers, buttons, mocks, imports, CLI help, catalog presence, health endpoints.
  - 7 proof classes: from static inspection to supported-path proof.
  - Docs validation is explicitly not runtime proof.
  - 12 fail-closed conditions with gate rules.
  - No live Pi SDK behavior. No live Coder execution. No autonomous dispatch.
  - No backend, frontend, test, or runtime changes.
- **Evidence**:
  - `acceptance-contract.md` — 17-section governing contract.
  - `backlog.md` — C04-T002 `go`, C04-T003 named next.
- **Consequence**:
  - C04-T002 accepted. C04-T003 (proof matrix) may proceed.
  - Future C04 implementation tasks must satisfy this contract before gating `go`.
- **Revisit Trigger**:
  - C04-T003 proof matrix — verify all acceptance criteria are mapped.
  - Any C04 implementation task — cross-reference against acceptance contract.
  - C04-T008 closeout — verify all acceptance criteria were satisfied or explicitly deferred.

---

### Decision: C04-D003

- **Decision ID**: C04-D003
- **Date**: 2026-06-20
- **Decision**: `go`. C04 Pi/Coder invocation boundary proof matrix defined. 8-state proof ladder, 27-row core boundary matrix with current/target states, 10-class evidence matrix, 15-condition gate outcome matrix, reusable future-task proof-row template, lineage/receipt/artifact/operator/redaction proof requirements. No runtime behavior changed. Release boundary preserved.
- **Reason**:
  - Proof matrix translates C04-T002 acceptance contract into task-by-task rubric.
  - 27-row core boundary matrix: every Pi/Coder surface from envelope through release support.
  - Current states: contract_only (majority), scaffold (orchestration route, id generation), missing (receipt, artifact, validation result, policy decision), deferred (artifact lineage, receipt lineage, Minimax).
  - Target states for C04-T003: contract_only (verified) — no implementation yet.
  - 10 evidence classes: static inspection, contract tests, route tests, dry-run, internal runtime, operator read-only, supported-path, docs validation, git diff hygiene, release proof.
  - 15 gate conditions: `hold` for safety-critical (lineage, policy, permission, authority bypass, raw payload, release claim), `next-proof-needed` for insufficient evidence.
  - Future task proof-row template: 12 required fields.
  - Lineage: 10 elements with gate rules. Receipt/artifact: 6 proof rows. Operator surface: 12 rows + prohibited controls. Redaction: 11 items.
  - No live Pi SDK behavior. No live Coder execution. No autonomous dispatch.
- **Evidence**:
  - `proof-matrix.md` — 17-section rubric.
  - `backlog.md` — C04-T003 `go`, C04-T004 named next.
- **Consequence**:
  - C04-T003 accepted. C04-T004 (repair receipt + artifact contract gaps) may proceed.
  - Future C04 implementation tasks must satisfy this proof matrix.
- **Revisit Trigger**:
  - C04-T004 receipt + artifact contract repair — verify against proof matrix.
  - Any C04 implementation task — cross-reference proof rows.
  - C04-T008 closeout — verify all proof matrix rows satisfied or explicitly deferred.

---

### Decision: C04-D004

- **Decision ID**: C04-D004
- **Date**: 2026-06-20
- **Decision**: `go`. C04-T001 audit categorized Pi/Coder contracts + validation + tests as `missing` in error. All contracts, validation helpers, and tests already existed. 15 original + 8 new boundary tests pass (23 total). No code behavior changed. Proof state corrected from `missing` to `contract_only (verified)`.
- **Reason**:
  - `guardian/pi/contracts.py`: `PiInvocationReceipt`, `PiInvocationArtifact`, `PiInvocationValidationResult`, `PiHarnessResult` — all present.
  - `guardian/pi/validation.py`: `validate_invocation_envelope()`, `validate_receipt_against_envelope()`, `validate_harness_result_against_receipt()` — all present, deterministic.
  - `tests/pi/test_pi_invocation_contracts.py`: 15 tests covering envelope, receipt, harness result, lineage, permissions, linkage, determinism, side-effect freedom, round-trip — all passing.
  - Added 8 boundary tests: forbidden metadata, missing lineage fields, artifact shape, no-runtime-import, determinism.
  - 23 tests total. No routes, persistence, execution, or frontend changes.
- **Evidence**:
  - `tests/pi/test_invocation_receipt_artifact_contracts.py` — 8 new tests.
  - `pytest -v tests/pi/` — 23 passed.
- **Consequence**:
  - C04-T004 accepted. Core contracts are verified, not missing.
  - C04-T005 (policy decision contract) may proceed.
- **Revisit Trigger**:
  - C04-T005 policy decision contract — define Guardian-owned decision semantics.

---

### Decision: C04-D006-R1

- **Decision ID**: C04-D006-R1
- **Date**: 2026-06-20
- **Decision**: `go`. C04-T006 result return contract validation closeout complete. Prior missing `git diff --check` and docs validator results now recorded. 22 focused + 66 full Pi tests pass. `guardian.pi` import ok. `git diff --check` clean. Docs validator passed. No runtime behavior changed. Release boundary preserved.
- **Reason**: Prior C04-T006 output omitted validation hygiene. All validation commands now pass. No code changes required.
- **Evidence**:
  - `pytest tests/pi/` — 66 passed.
  - `python -c "import guardian.pi"` — ok.
  - `git diff --check` — clean.
  - `python3 scripts/validate_docs.py` — passed.
- **Consequence**: C04-T006 fully accepted. C04-T007 may proceed.
- **Revisit Trigger**: None — validation closeout is final.

---

### Decision: C04-D008b-R1

- **Decision ID**: C04-D008b-R1
- **Date**: 2026-06-20
- **Decision**: `go`. C04-T008b route boundary proof closeout complete. 14 route tests + 90 Pi contract tests pass. `require_api_key` auth proven. Dry-run response contract safe and bounded. No Pi SDK, Coder, command bus, worker, transcript, receipt, artifact, DB, _store, _event_publisher, or frontend import. Release boundary preserved.
- **Reason**: Prior C04-T008b output omitted proof hygiene. Added 5 boundary tests (unauthenticated, no completion verdict, uses Pi validator, no command bus import, no frontend import). All validation passes.
- **Evidence**: 14 route tests + 90 Pi tests + import proof + git diff clean + docs validator passed.
- **Consequence**: C04-T008b fully accepted. C04-T008c may proceed.
- **Revisit Trigger**: None — closeout is final.

---

### Decision: C04-D008b-R3

- **Decision ID**: C04-D008b-R3
- **Date**: 2026-06-20
- **Decision**: `go`. C04-T008b governance closeout complete. R2 side-effect proofs accepted. Route remains `POST /api/agents/pi-invocation/dry-run`, validation-only, dry-run only. No Pi SDK, Coder, worker, transcript, receipt, artifact, DB, _store, _event_publisher, or frontend. Release boundary preserved. C04-T008c next.
- **Reason**: Prior R2 closeout omitted decision-log addendum and backlog consistency update. R3 records the missing governance metadata. No code or test changes.
- **Evidence**: 14 route tests + 90 Pi tests pass. `git diff --check` clean. Docs validator passed. C04-T008b-R2 proof-pack section already records full side-effect boundary.
- **Consequence**: C04-T008b fully accepted. C04-T008c may proceed.
- **Revisit Trigger**: None — governance closeout is final.

---

### Decision: C04-D009-R1

- **Decision ID**: C04-D009-R1
- **Date**: 2026-06-20
- **Decision**: `go`. C04-T009 Pi/Coder dry-run operator read surface proof closeout complete. Static card in Guardian Workspace. Truth labels: Validation only, No execution performed, No persistence performed, Release support: unsupported. Accepted means dry-run validation only. Interactive validation input deferred. No API helper. No execution controls. No raw payloads. 64 shell tests pass. `git diff --check` clean. Docs validator passed. Release boundary preserved.
- **Reason**: Prior C04-T009 output omitted proof hygiene. Card is static, read-only, correctly labeled, and already test-proven for forbidden controls and unsupported claims. No code changes needed.
- **Evidence**: 64 shell tests. `git diff --check` clean. `python3 scripts/validate_docs.py` passed.
- **Consequence**: C04-T009 fully accepted. C04-T010 may proceed.
- **Revisit Trigger**: None — proof closeout is final.

---

### Decision: C04-D010

- **Decision ID**: C04-D010
- **Date**: 2026-06-20
- **Decision**: `go`. Pi/Coder dry-run fixture pack complete. 7 fixture functions at `tests/fixtures/pi/__init__.py`. Valid fixture loads into `PiInvocationEnvelope` and passes `validate_invocation_envelope()`. Invalid fixtures fail validation. Response fixtures preserve dry-run truth. No raw payloads, execution controls, or completion verdicts. Route tests reuse the valid fixture. 103 Pi tests pass. `guardian.pi` import ok. Frontend fixture reuse deferred. No backend route, frontend, or runtime changes. Release boundary preserved.
- **Reason**: Prior C04-T010 output omitted governance closeout. Full Pi tests (103 passed including 13 fixture + 90 existing) and `guardian.pi` import confirmed. Decision-log and backlog now consistent.
- **Evidence**: 103 Pi tests pass. `guardian.pi` import ok. `git diff --check` clean. Docs validator passed.
- **Consequence**: C04-T010 fully accepted. C04-T011 may proceed.
- **Revisit Trigger**: None — governance closeout is final.

---

### Decision: C04-D011-R2

- **Decision ID**: C04-D011-R2
- **Date**: 2026-06-20
- **Decision**: `go`. C04-T011 API helper governance closeout complete. `validatePiCoderDryRun()` at `frontend/src/api/piCoderDryRun.ts`. Targets `POST /api/agents/pi-invocation/dry-run`. Validation-only. No forbidden exports. Card remains static/read-only, not wired. No runtime or frontend changes. Release boundary preserved. C04-T012 next.
- **Reason**: Prior R1 closeout omitted decision-log entry and backlog consistency update. R2 records the missing governance metadata. No code or test changes.
- **Evidence**: 66 shell tests pass. `git diff --check` clean. Docs validator passed.
- **Consequence**: C04-T011 fully accepted. C04-T012 may proceed.
- **Revisit Trigger**: None — governance closeout is final.
