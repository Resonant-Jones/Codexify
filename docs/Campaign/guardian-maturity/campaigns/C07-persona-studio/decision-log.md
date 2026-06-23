# C07 Decision Log: Persona Studio

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C07-D001 | 2026-06-20 | `go` — C07 seam audit complete; 13 surfaces, 10 gaps, 7 risks, C07-T002 next | active |

---

### Decision: C07-D001

- **Decision ID**: C07-D001
- **Date**: 2026-06-20
- **Decision**: `go`. C07 Persona Studio seam audit complete. 13 surfaces audited. 10 gaps and 7 risks registered. 7-task backlog defined. No implementation, UI, routes, persistence, permissions, retrieval, runtime flags, memory writes, chat history, or execution authority added. C07-T002 next.
- **Reason**: Audit confirms Studio feature exists with page/API/store but boundedness is unproven. Gaps: V1 contract, permission matrix, retrieval policy, config preview, profile boundaries. No code or test changes.
- **Evidence**: `persona-studio-current-surface-seam-audit.md` — 13 surfaces, 10 gaps, 7 risks.
- **Consequence**: C07 campaign active. C07-T002 (contract + proof plan) next.
- **Revisit Trigger**: C07-T002 V1 contract — define bounded scope for Studio without execution authority.

---

### Decision: C07-D002

- **Decision ID**: C07-D002
- **Date**: 2026-06-20
- **Decision**: `go`. C07 Persona Studio V1 contract and proof plan defined. 11 V1 goals, 13 non-goals, 5-task proof ladder, 10 acceptance criteria, 12-row boundary table. No implementation. C07-T003 next.
- **Reason**: C07-T001 audit gaps mapped to bounded V1 contract. Proof ladder defines 5 tasks (T003–T007) with goals, non-goals, and boundaries. No code, UI, routes, persistence, permissions, retrieval, memory, chat, or execution added.
- **Evidence**: `persona-studio-bounded-v1-contract-proof-plan.md`.
- **Consequence**: C07-T002 accepted. C07-T003 (route/navigation boundaries) may proceed.
- **Revisit Trigger**: C07-T003 navigation boundaries proof — verify Studio page routes safely.

---

### Decision: C07-D003

- **Decision ID**: C07-D003
- **Date**: 2026-06-20
- **Decision**: `go`. C07-T003 navigation boundary proof complete. `/persona-studio` route recognized, page framed as configuration surface. 8 tests. No chat/memory/execution. C07-T004 next.
- **Reason**: Route/navigation boundaries proven: Studio is a configuration surface reachable at `/persona-studio`, not a chat or execution surface. No forbidden imports or controls. 8 deterministic tests.
- **Evidence**: `persona-studio-route-navigation-boundary-proof.md` + 8 test file.
- **Consequence**: C07-T003 accepted. C07-T004 (profile draft state) may proceed.
- **Revisit Trigger**: C07-T004 draft state proof — verify Studio local draft and validation boundaries.

---

### Decision: C07-D004

- **Decision ID**: C07-D004
- **Date**: 2026-06-20
- **Decision**: `go`. C07-T004 draft/validation boundary proof complete. Draft state is local storage. Validation is type-level, not enforcement. 9 tests. No memory, chat, execution. C07-T005 next.
- **Reason**: Profile draft state proven as local storage. Validation proven as config-level types only. No backend persistence, memory writes, chat writes, or execution authority.
- **Evidence**: `persona-studio-profile-draft-validation-boundary-proof.md` + 9 tests.
- **Consequence**: C07-T004 accepted. C07-T005 (effective config preview) may proceed.
- **Revisit Trigger**: C07-T005 config preview proof — verify resolved thread_config from draft.

---

### Decision: C07-D005

- **Decision ID**: C07-D005
- **Date**: 2026-06-20
- **Decision**: `go`. C07-T005 effective config preview boundary proof complete. Config fields from local state only. No provider, chat, memory, or execution. 9 tests. C07-T006 next.
- **Reason**: Effective config preview bounded: config derived from local storage seed state. TruthMatrix/DiagnosticsPanel importable. No execution, provider calls, memory writes, or chat history.
- **Evidence**: `persona-studio-effective-config-preview-boundary-proof.md` + 9 tests.
- **Consequence**: C07-T005 accepted. C07-T006 (permission/retrieval preview) may proceed.
- **Revisit Trigger**: C07-T006 permissions/retrieval preview — prove preview-only posture.

---

### Decision: C07-D006

- **Decision ID**: C07-D006
- **Date**: 2026-06-20
- **Decision**: `go`. C07-T006 permission/retrieval preview boundary proof complete. Tools + retrieval config present, no enforcement/execution imports. 9 tests. C07-T007 next.
- **Reason**: Permission and retrieval surfaces proven as preview-only config types. No enforcement, execution, command bus, PiCoder, memory, or chat imports.
- **Evidence**: `persona-studio-permission-retrieval-preview-boundary-proof.md` + 9 tests.
- **Consequence**: C07-T006 accepted. C07-T007 (V1 closeout) may proceed.
- **Revisit Trigger**: C07-T007 V1 closeout — verify all C07 boundaries sealed.
