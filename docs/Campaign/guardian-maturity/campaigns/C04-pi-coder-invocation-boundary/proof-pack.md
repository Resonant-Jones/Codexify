# C04 Proof Pack: Pi/Coder Invocation Boundary

---

## C04-T001: Seam Audit (2026-06-20 11:45 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `6a2556daf` | **Worktree**: clean
- All 36+ required pre-reads and inspection targets available. No missing inputs beyond directories/files that don't exist.

### Files Created
- `seam-audit.md` — 17 sections: gate, scope, inputs, search terms, contract surface, implementation surface (15 rows), runtime proven/not-proven (14 items each), authority boundaries (9), data/persistence (8), operator/observability (10 surfaces), test/proof (6), risk register (10 risks), backlog (8 tasks), release boundary, docs follow-through
- `backlog.md` — C04-T001 complete, C04-T002 named next, 8-task sequence
- `proof-pack.md` — this file
- `decision-log.md` — C04-D001 entry

### Search Terms Used
17 terms + 12 directories/files inspected.

### Existing Contract Surface
- `guardian/pi/`: contracts.py (dataclasses), tokens.py (enums), validation.py (functions) — **contract-only, no runtime**.
- `guardian/agents/coding_agent_contracts.py`: CodingAgentTaskEnvelope, CodingAgentResult, CodingAgentAdapterKind — **contract-only**.
- `guardian/routes/agent_orchestration.py`: POST `/api/agents/coding/execute` — **scaffold** (creates deployment + run, delegates to worker — no Pi SDK call).
- ADR-020, `pi-invocation-boundary-contract.md`: Normative contracts — **not runtime-proven**.

### Existing Implementation Surface
15 surfaces inspected. Key findings:
- `guardian/pi/`: `contract-only` — no Pi SDK calls, no execution, no routes.
- `PiInvocationEnvelope`: `contract-only` — dataclass, not wired.
- `execute_coding_task` route: `scaffold` — creates deployment/run records, no direct execution.
- Frontend operator surface: `read-only` — no Pi/Coder execution controls.
- Pi/Coder tests: `missing` — no `tests/pi/` directory.
- Pi/Coder receipts/artifacts: `missing`.

### Runtime Proven vs Not Proven
- **Proven**: Types exist as dataclasses/enums. Agent orchestration route exists as scaffold. Command bus and operator workspace are proven (C05/C06). No Pi SDK calls found.
- **Not proven**: Live Pi SDK call, live Coder execution, autonomous dispatch, recursive tool loop, Pi/Coder command execution, worker orchestration for Pi/Coder, sandbox execution, transcript persistence from Pi/Coder, receipt/artifact creation, frontend execution controls, release support.

### Authority Boundaries
9 boundaries checked — all preserved: Guardian policy ownership, command bus authority, transcript ownership, source-message lineage, result return control, provider lane separation, identity boundary, no token bypass, no export/restore lineage bypass.

### Data/Persistence
- ✅ No Pi/Coder-specific tables.
- ✅ No Pi/Coder migration files.
- ✅ C03 work-order/receipt/command-run tables exist but are not Pi/Coder-specific.
- ✅ Low schema drift risk.

### Operator/Observability
- ✅ Workspace is read-only — no Pi/Coder execution controls.
- ❌ No envelope preview UI.
- ❌ No validation-only run mode UI.
- ❌ No provider lane selection UI.
- ❌ EventConsole redaction not C06-ready.

### Risk Register
10 risks: accidental release-claim widening (HIGH), conflation of provider/Pi lanes (MED), treating command-run as completion proof (MED), treating receipt as completion proof (MED), hidden autonomous execution (HIGH), ungoverned result return (HIGH), lineage loss (MED), raw payload exposure (HIGH), schema drift (LOW), UI controls before governance (HIGH).

### Recommended Backlog
8 tasks: C04-T001 (audit), C04-T002 (acceptance contract), C04-T003 (envelope preview contract), C04-T004 (validation-only contract), C04-T005 (result return contract), C04-T006 (envelope preview UI), C04-T007 (validation-only UI), C04-T008 (integration proof + closeout).

### Release Boundary
No runtime, backend, frontend, test, migration, ADR, or current-state changes.

### Gate Decision
**`go`** — C04-T001 accepted. C04-T002 may proceed.

### Next Task
**C04-T002: Define Pi/Coder invocation boundary acceptance contract**

---

## C04-T002: Acceptance Contract (2026-06-20 12:00 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `e4b68e685` | **Worktree**: clean

### Files Created/Modified
- `acceptance-contract.md` — created (17 sections, 350+ lines)
- `backlog.md` — C04-T002 marked `go`

### Inputs Read
All 24 required pre-reads available. No missing inputs.

### Acceptance Contract Artifact
`acceptance-contract.md`: 17 sections — gate, scope, contract purpose, acceptance state model (8 states), invocation boundary acceptance criteria (14 criteria), proof surface matrix (18 rows), prohibited acceptance shortcuts (13), runtime proof classes (7 classes), result return and lineage requirements (10 fields), receipt and artifact acceptance rules (6 distinctions), operator surface acceptance rules (11 safe fields, 10 prohibited, 12 prohibited controls), failure and blocker rules (12 fail-closed conditions), release boundary.

### Gate Decision
**`go`** — C04-T002 accepted. C04-T003 may proceed.

### Next Task
**C04-T003: Define Pi/Coder invocation boundary proof matrix**

---

## C04-T003: Proof Matrix (2026-06-20 12:10 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `c5c0d5931` | **Worktree**: clean

### Files Created
- `proof-matrix.md` — 17 sections
- `backlog.md` — C04-T003 marked `go`

### Proof Matrix Artifact
`proof-matrix.md`: 17 sections — proof state ladder (8 states), core boundary proof matrix (27 rows), evidence class matrix (10 classes), gate outcome matrix (15 conditions), future task proof-row template, lineage requirements (10 elements), receipt/artifact requirements (6 rows), operator surface requirements (12 rows), redaction/safety requirements (11 items).

### Gate Decision
**`go`** — C04-T003 accepted. C04-T004 may proceed.

### Next Task
**C04-T004: Repair Pi/Coder invocation receipt and artifact contract gaps**

---

## C04-T004: Contract Gap Repair (2026-06-20 12:25 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `3cbd4ad8f` | **Worktree**: clean
- **Key finding**: `guardian/pi/contracts.py` + `guardian/pi/validation.py` already contain comprehensive Pi/Coder contract types and deterministic validation helpers. `tests/pi/test_pi_invocation_contracts.py` already contained 15 passing tests covering envelope validation, receipt/envelope matching, harness result/receipt matching, owner lineage, permission posture, command bus linkage, determinism, side-effect freedom, and round-trip serialization. C04-T001 audit categorized these as `missing` in error.

### Contract Gap Status
- `PiInvocationReceipt`: ✅ Already exists — 13 required fields, from_payload/to_payload
- `PiInvocationArtifact`: ✅ Already exists — 7 fields
- `PiInvocationValidationResult`: ✅ Already exists — structured outcome class
- `validate_invocation_envelope()`: ✅ Already exists — deterministic
- `validate_receipt_against_envelope()`: ✅ Already exists — cross-validates receipt against envelope
- `validate_harness_result_against_receipt()`: ✅ Already exists — cross-validates result against receipt

### New Work
Added `tests/pi/test_invocation_receipt_artifact_contracts.py` — 8 additional boundary tests:
- Receipt artifact metadata does not silently accept forbidden keys
- Receipt missing source_thread_id fails
- Receipt missing source_message_id fails
- Artifact with required fields passes construction
- Artifact no raw payload fields present in payload
- Importing guardian.pi does not import runtime routes
- Envelope validation is deterministic
- Receipt-against-envelope validation is deterministic

### Full Test Suite
```
tests/pi/test_pi_invocation_contracts.py            15 passed
tests/pi/test_invocation_receipt_artifact_contracts.py  8 passed
Total: 23 passed
```

### No Runtime Behavior
- No backend routes added.
- No persistence schema changed.
- No command invocation behavior added.
- No Pi SDK/Coder execution added.
- No frontend controls added.

### Gate Decision
**`go`** — C04-T004 accepted. C04-T005 may proceed.

### Next Task
**C04-T005: Define Pi/Coder policy decision contract**

---

## C06-T006-R1: Validation Closeout (2026-06-20 12:40 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `c4e63a55f` | **Worktree**: clean
- **Prior `next-proof-needed` reason**: `git diff --check` and `python3 scripts/validate_docs.py` not reported.

### Result Return Contract Verification
`PiInvocationResultReturn` dataclass present with 20 fields. `validate_pi_invocation_result_return()` helper present. 22 focused tests cover all contract states and edge cases.

### Validation
```
pytest tests/pi/test_invocation_result_return_contract.py  22 passed
pytest tests/pi/                                           66 passed
python -c "import guardian.pi"                             ok
git diff --check                                            clean
python3 scripts/validate_docs.py                            passed
```

### No Runtime
No result return runtime, no result reinjection, no transcript persistence, no backend routes, no frontend controls.

### Gate Decision
**`go`** — C04-T006-R1 accepted. C04-T007 may proceed.

### Next Task
**C04-T007: Define Pi/Coder operator evidence read model**
