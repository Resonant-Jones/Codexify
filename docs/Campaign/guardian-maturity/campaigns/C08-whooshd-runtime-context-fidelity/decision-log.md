# C08 Decision Log: Whoosh'd Runtime Integration & Context Fidelity

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C08-D001 | 2026-06-20 | `go` — C08 seam audit complete; 17 files, 7 gaps, 7 risks, C08-T002 next | active |

---

### Decision: C08-D001

- **Decision ID**: C08-D001
- **Date**: 2026-06-20
- **Decision**: `go`. C08 Whoosh'd runtime configuration and model inventory seam audit complete. 17 files inspected across 8 seam groups. 7 gaps and 7 risks registered. 6-task backlog defined. No runtime, provider, context, or frontend changes made. Release boundary preserved.
- **Reason**: Audit confirms Whoosh'd sidecar, model profiles, and local runtime presets exist. Key gaps: context fidelity not proven, system identity not proven at call boundary, model inventory not operator-visible, local-only posture not verified at call site. C08 started after C04 closure and Wave 4 selection.
- **Evidence**: `runtime-config-model-inventory-seam-audit.md` — 8 seam groups, 17 files, 7 gaps, 7 risks, 6-task candidates.
- **Consequence**: C08 campaign active. C08-T002 (endpoint config + health check proof) next.
- **Revisit Trigger**: C08-T002 health-check proof — verify Whoosh'd endpoint and state visibility.

---

### Decision: C08-D002

- **Decision ID**: C08-D002
- **Date**: 2026-06-20
- **Decision**: `go`. C08-T002 endpoint health proof complete. Base URL from `WHOOSHD_HOST:WHOOSHD_PORT`. 4 health probes proved. States and ownership tracked. 16 tests without real daemon. Model inventory, context fidelity, and operator diagnostics remain unproven. C08-T003 next.
- **Reason**: Endpoint configuration and health-check semantics proven via focused tests and proof artifact. No runtime, provider, model inventory, or context changes.
- **Evidence**: `endpoint-health-proof.md` — truth table, boundary table, gaps, risks. 16 tests pass.
- **Consequence**: C08-T002 accepted. C08-T003 (model inventory identity) may proceed.
- **Revisit Trigger**: C08-T003 model inventory proof — cross-reference against endpoint health findings.

---

### Decision: C08-D003

- **Decision ID**: C08-D003
- **Date**: 2026-06-20
- **Decision**: `go`. C08-T003 model inventory identity proof complete. Registry ID ≠ repo ID. Display label ≠ canonical identity. 14 tests. 4 gaps. No real daemon. C08-T004 next.
- **Reason**: Model inventory identity proven via file-backed profiles. Key finding: profile `id` and `model.repo` are distinct fields — identity not collapsed. Duplicate handling, validation, runtime model ID, and operator visibility remain gaps.
- **Evidence**: `model-inventory-identity-proof.md` — truth table, boundary table, gaps, risks. 14 tests pass.
- **Consequence**: C08-T003 accepted. C08-T004 (context bundle + system identity) may proceed.
- **Revisit Trigger**: C08-T004 context fidelity proof — verify model identity propagates to context boundary.

---

### Decision: C08-D004a

- **Decision ID**: C08-D004a
- **Date**: 2026-06-20
- **Decision**: `go`. C08-T004 split because `chat_completion_service.py` is 4966 lines. Inspection artifact created: 7-step assembly chain, candidate proof seam at `_build_messages_for_llm_compat()`. No code or test changes. C08-T004b next.
- **Reason**: Monolithic C08-T004 was too large. Split into T004a (inspect), T004b (prove), T004c (close). Assembly chain mapped from chat route through worker, completion service, message assembly, context injection, provider dispatch.
- **Evidence**: `context-assembly-seam-inspection.md` — 7-step chain, 4 critical functions, Whoosh'd/local lane map, candidate test seam.
- **Consequence**: C08-T004a accepted. C08-T004b may proceed with focused tests at `_build_messages_for_llm_compat()`.
- **Revisit Trigger**: C08-T004b context delivery proof — verify messages + model_id + context_bundle captured at provider-call boundary.
