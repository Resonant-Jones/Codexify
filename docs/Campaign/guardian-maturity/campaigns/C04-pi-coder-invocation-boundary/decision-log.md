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
