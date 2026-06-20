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
