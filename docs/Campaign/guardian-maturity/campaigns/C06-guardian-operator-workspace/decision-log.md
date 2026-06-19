# C06 Decision Log: Guardian Operator Workspace

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C06-D001 | 2026-06-19 | `go` — C06 seam audit complete; 8 operator surfaces, 5 backend surfaces, 8 gaps, workspace implementation not started, release boundary preserved, C06-T002 next | active |
| C06-D002 | 2026-06-19 | `go` — C06 surface contract defined; 19 sections, 8 zones, source-of-truth mapping, read-only rules, evidence states, redaction/truth-labeling, C06-T003 next | active |
| C06-D003 | 2026-06-19 | `go` — Guardian Operator Workspace lens scaffold added; read-only, no fetch, no mutation, 7 tests, C06-T004 next | active |
| C06-D004 | 2026-06-19 | `go` — first live cards composed; HealthOverview + CodingWorkOrdersPanel in workspace; no new fetch, no mutation, C06-T005 next | active |

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

---

### Decision: C06-D003

- **Decision ID**: C06-D003
- **Date**: 2026-06-19
- **Decision**: `go`. Guardian Operator Workspace lens scaffold added to Command Center. `GuardianOperatorWorkspaceLens` component created (read-only, static scaffold). New `guardian-workspace` rail id wired. Shell renders workspace lens on selection. 7 tests added (5 shell + 2 rail). No backend or runtime behavior change. Workspace implementation remains scaffold-only. Release boundary preserved.
- **Reason**:
  - Scaffold matches C06-T002 surface contract: 8 cards (work-order, command-run, tool-turn, receipt, health, gaps, safety) + header.
  - All content is static — no fetch, no API imports, no dynamic imports.
  - No mutation controls (7 labels absent, test-proven).
  - Truth-labeling present on tool-turn and receipt cards.
  - Safety boundary lists 6 unsupported claims.
  - Rail item and shell switch both test-proven.
  - 26 shell tests (5 new + 21 existing), 16 rail tests (2 new + 14 existing), 74 broader (all pass, 756 skipped).
- **Evidence**:
  - `GuardianOperatorWorkspaceLens.tsx` — 195-line read-only scaffold.
  - `CommandCenterUtilityRail.tsx` — new lens id and entry.
  - `CommandCenterShell.tsx` — switch case wired.
  - `CommandCenterShell.test.tsx` — 5 workspace tests.
  - `CommandCenterUtilityRail.test.tsx` — 2 workspace tests.
- **Consequence**:
  - C06 has a visible workspace entry point in Command Center.
  - C06-T004 (compose live cards) may proceed.
  - Scaffold remains static until live data sources are composed.
- **Revisit Trigger**:
  - C06-T004 composes work-order card — replace scaffold text with live CodingWorkOrdersPanel integration.
  - C06-T005 composes receipt card — replace scaffold text with live ReceiptEvidence.
  - C06-T006 composes tool-turn card — replace scaffold text with live ToolTurnObservability.

---

### Decision: C06-D004

- **Decision ID**: C06-D004
- **Date**: 2026-06-19
- **Decision**: `go`. First live read-only cards composed inside Guardian Operator Workspace. `HealthOverview` rendered for runtime/health card. `CodingWorkOrdersPanel` rendered for work-order status card. Remaining cards remain static/deferred. No new backend routes, no new fetch behavior beyond existing nested component behavior, no mutation controls added. Release boundary preserved.
- **Reason**:
  - HealthOverview composed with props from shell (healthItems, lastCheckedAt, loading, onRefresh) — no new fetch.
  - CodingWorkOrdersPanel composed as-is — preserves existing C05 tool-turn and C03 receipt behavior.
  - Command-run evidence, tool-turn observability (separate), receipt evidence (separate), gaps, safety boundary remain static/deferred cards.
  - 26 shell tests pass (5 workspace + 21 existing). 96 broader tests pass.
  - Git diff --check clean, docs validator passed.
- **Evidence**:
  - `GuardianOperatorWorkspaceLens.tsx` — props interface + live HealthOverview + live CodingWorkOrdersPanel.
  - `CommandCenterShell.tsx` — workspace case passes health props.
  - `CommandCenterShell.test.tsx` — existing workspace tests continue to pass.
- **Consequence**:
  - Workspace now has 2 live cards (work-order + health) and 6 static/deferred cards.
  - C06-T005 (composition proof) may proceed.
  - Remaining deferred cards (command-run, tool-turn standalone, receipt standalone) not yet composed.
- **Revisit Trigger**:
  - C06-T005 composition proof — verify all cards match contract.
  - C06-T006/T007 — compose remaining deferred cards.
  - C06-T008 integration tests — verify full workspace behavior.
