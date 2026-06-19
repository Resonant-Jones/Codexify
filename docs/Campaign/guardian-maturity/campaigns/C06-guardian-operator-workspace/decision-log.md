# C06 Decision Log: Guardian Operator Workspace

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C06-D001 | 2026-06-19 | `go` — C06 seam audit complete; 8 operator surfaces, 5 backend surfaces, 8 gaps, workspace implementation not started, release boundary preserved, C06-T002 next | active |
| C06-D002 | 2026-06-19 | `go` — C06 surface contract defined; 19 sections, 8 zones, source-of-truth mapping, read-only rules, evidence states, redaction/truth-labeling, C06-T003 next | active |

---

### Decision: C06-D001

- **Decision ID**: C06-D001
- **Date**: 2026-06-19
- **Decision**: `go`. C06 Guardian Operator Workspace seam audit complete. C06-T001 accepted. Workspace implementation not started.
- **Reason**:
  - C03 and C05 are closed. Operator truth components exist across 4+ separate lenses.
  - Seam audit inspected 8 existing operator surfaces and 5 backend truth surfaces.
  - 10 workspace composition candidates evaluated — 5 safe to compose now, 2 conditional, 1 deferred for redaction review, 2 need UI.
  - 8 gaps recorded: receipt linkage deferred, no unified lens, no surface contract, tool-turn conditional, event console redaction, manifest not surfaced, bottom drawer placeholder, latest-run bridge not surfaced.
  - 9-task C06 backlog defined (C06-T001 through C06-T009).
  - Release boundary preserved — no runtime, backend, or persistence changes.
- **Evidence**:
  - `seam-audit.md` — 15-section audit (gate, scope, truth, 8 operator surfaces, 5 backend surfaces, 10 candidates, safety, non-goals, 8 gaps, 9-task backlog, release boundary, validation).
  - `backlog.md` — C06-T001 complete, C06-T002 named next.
  - `proof-pack.md` — C06-T001 section recorded.
- **Consequence**:
  - C06 campaign active. C06-T002 (surface contract) is next.
  - No workspace implementation until C06-T003+.
  - Receipt linkage, event console redaction review, and command manifest surfacing remain deferred within C06 scope.
- **Revisit Trigger**:
  - C06-T002 surface contract defines workspace layout — revisit if gaps need reclassification.
  - Assistant message ID becomes reliably available — revisit tool-turn composition readiness.
  - C05 receipt linkage is wired — revisit receipt evidence composition.

---

### Decision: C06-D002

- **Decision ID**: C06-D002
- **Date**: 2026-06-19
- **Decision**: `go`. C06 Guardian Operator Workspace surface contract defined. 19-section contract covering workspace purpose, 8-zone surface model, source-of-truth mapping, read-only interaction rules, evidence state model, redaction/truth-labeling boundaries, unavailable/deferred states. Workspace implementation not started. Release boundary preserved.
- **Reason**:
  - C06-T001 seam audit identified 10 composition candidates and 8 gaps.
  - C06-T002 translates the audit into a bounded workspace composition contract.
  - Surface model defines 8 zones — 5 safe to compose now, 1 conditional, 2 new.
  - Source-of-truth mapping covers all 8 zones with frontend/backend/durable store sources.
  - Read-only interaction rules: 3 allowed, 11 prohibited.
  - Evidence state model: 7 canonical states.
  - Redaction: 10 forbidden content types.
  - Truth-labeling: 5 templates for tool-turn, command-run, receipt, work-order, health.
  - 6 unavailable/deferred states recorded.
- **Evidence**:
  - `surface-contract.md` — 19 sections (gate, scope, truth, purpose, surface model, truth mapping, interaction rules, evidence states, redaction/labeling, deferred states, non-goals, implementation readiness, backlog, release boundary, validation, final gate).
  - `backlog.md` — C06-T002 `go`, C06-T003 named next.
  - `proof-pack.md` — C06-T002 section recorded.
- **Consequence**:
  - C06 surface contract is the authoritative workspace specification.
  - C06-T003 (lens scaffold) may proceed.
  - No workspace implementation until C06-T003+.
  - All implementation must follow contract rules (read-only, redaction, truth-labeling).
- **Revisit Trigger**:
  - C06-T003 lens scaffold implementation begins — verify contract compliance.
  - C05 receipt linkage is wired — update receipts zone readiness.
  - C06-T009 closeout — verify all zones meet contract.
