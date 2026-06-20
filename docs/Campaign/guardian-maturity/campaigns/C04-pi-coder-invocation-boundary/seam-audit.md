# C04-T001 Seam Audit: Pi/Coder Invocation Boundary

## Gate Decision

**`go`** — The seam audit is complete. C04 may proceed to C04-T002.

## Scope

This is a docs-only seam audit. It inspects existing architecture docs, code, tests, and operator surfaces. It does **not** implement Pi/Coder invocation.

## Inputs Read

All required pre-reads available. No missing inputs.

### Missing from search

- `guardian/pi/` subdirectories beyond `__init__.py`, `contracts.py`, `tokens.py`, `validation.py` — none found.
- `tests/pi/` directory — not found.
- `frontend/src/features/coding/` directory — not found.

## Search Terms and Inspection Method

| Term | Used? | Results |
|------|-------|---------|
| `PiInvocation` | ✅ | `guardian/pi/tokens.py` (enums), `guardian/pi/contracts.py` (dataclasses), `guardian/pi/__init__.py` (exports) |
| `PiInvocationEnvelope` | ✅ | `guardian/pi/tokens.py` — `PiInvocationEnvelopeStatus` enum only |
| `PiInvocationReceipt` | ✅ | `guardian/pi/tokens.py` — `PiInvocationReceiptStatus` enum only |
| `PiInvocationArtifact` | ✅ | Not found — no implementation or contract |
| `PiHarnessResult` | ✅ | `guardian/pi/tokens.py` — `PiHarnessResultClass` enum only |
| `CodingAgentTaskEnvelope` | ✅ | `guardian/agents/coding_agent_contracts.py` — dataclass (contract) |
| `Coder` | ✅ | `guardian/core/llm_catalog.py` — "coder" provider label only; `guardian/routes/codex.py` — codex lineage routes |
| `coding agent` | ✅ | `guardian/agents/coding_agent_contracts.py`, `guardian/routes/agent_orchestration.py` |
| `agent orchestration` | ✅ | `guardian/routes/agent_orchestration.py` — routes for plan/deploy/execute/cancel/get |
| `invocation envelope` | ✅ | `guardian/pi/contracts.py` — `PiInvocationEnvelope` dataclass (contract-only) |
| `harness result` | ✅ | `guardian/pi/contracts.py` — `PiHarnessResult` dataclass (contract-only) |
| `result return` | ✅ | `guardian/agents/coding_agent_contracts.py` — `CodingAgentResult` dataclass (contract) |
| `receipt` | ✅ | `guardian/db/models.py` — `WorkOrderResultReceipt` model (C03); no Pi/Coder-specific receipts |
| `artifact` | ✅ | Not found as Pi/Coder artifact — no implementation |
| `lineage` | ✅ | `guardian/codex/lineage.py` — codex entry lineage (not Pi/Coder) |
| `command bus` | ✅ | `guardian/command_bus/` — exists, C05-proven |
| `guardian mediated` | ✅ | `docs/architecture/adr/020-*.md` — ADR-020 |
| `Pi SDK` | ✅ | Not found — no Pi SDK calls in codebase |
| `Minimax` | ✅ | `guardian/pi/tokens.py` — `PiProviderLaneClass.MINIMAX` enum only |

### Inspected directories

`guardian/pi/`, `guardian/agents/`, `guardian/codex/`, `guardian/command_bus/`, `guardian/routes/`, `guardian/workers/`, `guardian/core/`, `guardian/db/models.py`, `frontend/src/features/commandCenter/`, `tests/`, `docs/architecture/`, `docs/Campaign/guardian-maturity/campaigns/C03/`, `C05/`, `C06/`

## Existing Contract Surface

### What Architecture Contracts Say

| Contract | Document | Key normative statements | Runtime implemented? |
|----------|----------|--------------------------|----------------------|
| Guardian-mediated coding-agent execution | ADR-020, `pi-invocation-boundary-contract.md` | Guardian mediates all Pi/Coder execution; invocation envelope carries task, permission policy, lineage | Contract: yes. Runtime: no (envelope types exist as dataclasses, not as wired execution) |
| Agent protocol operations | `agent-protocol-operations.md` | Agent operations defined as protocol types; Guardian holds authority | Contract: yes. Runtime: partial (command bus exists, Pi/Coder execution does not) |
| Agent tool loop contract | `agent-tool-loop-contract.md` | Bounded tool-turn semantics; loop stop reason; no autonomous recursion | Contract: yes. Runtime: C05 observability proven, but execution not implemented |
| Pi invocation boundary contract | `pi-invocation-boundary-contract.md` | Envelope → validation → harness → result return lifecycle; bounded, governed | Contract: yes. Runtime: no — dataclasses exist, no Pi SDK call, no harness execution |
| Runtime protocol token contract | `runtime-protocol-token-contract.md` | Canonical tokens govern provider state, request lifecycle, pipeline state; agent command/execution tokens exist | Contract: yes. Runtime: tokens exist, execution does not |

### What Exists as Contract-Only (Types, No Runtime)

| Artifact | Location | Type |
|----------|----------|------|
| `PiInvocationEnvelope` | `guardian/pi/contracts.py` | Dataclass — fields: pi_invocation_id, status, envelope_id, coding_task_id, campaign_id, work_order_id, adapter_kind, permission_policy, instructions, repo_root, attempt_id, lineage_source_message_id, lineage_user_id, lineage_project_id, provider_lane, created_at |
| `PiHarnessResult` | `guardian/pi/contracts.py` | Dataclass — result class, output summary, error summary, exit code, sandbox path, changeset summary, commit hash |
| `PiInvocationEnvelopeStatus` | `guardian/pi/tokens.py` | Enum: PREPARED, VALIDATED, REJECTED |
| `PiInvocationReceiptStatus` | `guardian/pi/tokens.py` | Enum: ISSUED, ACCEPTED, COMPLETED, FAILED, REJECTED |
| `PiInvocationValidationOutcome` | `guardian/pi/tokens.py` | Enum: VALID, FAILED_CLOSED |
| `PiHarnessResultClass` | `guardian/pi/tokens.py` | Enum: SUCCESS, FAILURE, BLOCKED |
| `PiProviderLaneClass` | `guardian/pi/tokens.py` | Enum: LOCAL, REMOTE, HYBRID, EXTERNAL, MINIMAX |
| `CodingAgentTaskEnvelope` | `guardian/agents/coding_agent_contracts.py` | Dataclass — task envelope per ADR-020 |
| `CodingAgentResult` | `guardian/agents/coding_agent_contracts.py` | Dataclass — result envelope |
| `CodingAgentAdapterKind` | `guardian/agents/coding_agent_contracts.py` | Literal: `pi`, `pi_sdk`, `pi_codex_runner` |

**Key finding**: All Pi/Coder types exist as dataclasses and enums — none are wired to runtime execution. The `pi_codex_runner` adapter kind is labeled "legacy-compatible only" in its source comment and "does not imply direct Codex CLI execution; it is the Pi broker lane."

## Existing Implementation Surface

| Surface | File or directory | Status | Evidence | Notes |
|---------|-------------------|--------|----------|-------|
| `guardian/pi/` | `guardian/pi/` | `contract-only` | `__init__.py`, `contracts.py`, `tokens.py`, `validation.py` — all dataclasses/enums/functions | No Pi SDK calls, no execution, no routes |
| `PiInvocationEnvelope` | `guardian/pi/contracts.py:30` | `contract-only` | Dataclass with 17 fields | Used by agent_orchestration route |
| `PiInvocationReceipt` | Not found as type | `missing` | `PiInvocationReceiptStatus` enum exists, but no dataclass | Receipt model absent |
| `PiInvocationArtifact` | Not found | `missing` | No artifact dataclass, route, or model | — |
| `PiHarnessResult` | `guardian/pi/contracts.py:90` | `contract-only` | Dataclass with 7 fields | Not used in any route |
| `PiInvocationValidationResult` | Not found | `missing` | `validation.py` has helper functions, no result type | Validation functions exist, unwired |
| Validation helpers | `guardian/pi/validation.py` | `contract-only` | `validate_pi_invocation_envelope()` function | Not called by any route or worker |
| `execute_coding_task` route | `guardian/routes/agent_orchestration.py:208` | `scaffold` | POST `/api/agents/coding/execute` — creates deployment + run record, returns run_id | No Pi/Coder execution in the route itself; delegates to worker |
| Agent orchestration routes | `guardian/routes/agent_orchestration.py` | `scaffold` | Plan, deploy, execute, cancel, get run, stream events, list runs | Backend routes exist for flow management |
| Codex routes | `guardian/routes/codex.py` | `implemented` | Codex entry CRUD + lineage | Not Pi/Coder-specific |
| Codexify router | `guardian/routes/codexify_router.py` | `implemented` | Embedding/search/capability | Not Pi/Coder-specific |
| `CodingAgentTaskEnvelope` | `guardian/agents/coding_agent_contracts.py` | `contract-only` | Dataclass | Used by orchestration route |
| Coding agent contracts | `guardian/agents/coding_agent_contracts.py` | `contract-only` | Envelope, result, permission policy dataclasses | No execution |
| Chat worker | `guardian/workers/chat_worker.py` | `implemented` | Chat completion worker | No Pi/Coder-specific execution |
| Command bus | `guardian/command_bus/` | `implemented` | Manifest, invoke, run readback (C05-proven) | No Pi/Coder invocation in command bus |
| Frontend operator surface | `frontend/src/features/commandCenter/` | `read-only` | CodingWorkOrdersPanel + workspace lens (C06-proven) | No Pi/Coder execution controls |
| Work-order receipts | `guardian/db/models.py:4459` | `implemented` (C03) | `WorkOrderResultReceipt` model, routes, tests | Not Pi/Coder-specific |
| Pi/Coder tests | Not found | `missing` | No `tests/pi/` directory | — |

## Runtime Behavior Proven vs Not Proven

### Proven by Source Inspection

- `guardian/pi/contracts.py` and `tokens.py` define Pi/Coder **types** only.
- `guardian/agents/coding_agent_contracts.py` defines coding agent **contract** types only.
- `guardian/routes/agent_orchestration.py` has a POST route for `/api/agents/coding/execute` that creates deployment + run records but does **not** execute Pi/Coder directly.
- Command bus exists and is read-only verified (C05).
- Operator workspace exists and is read-only verified (C06).

### Not Proven

- ❌ Live Pi SDK call — not found in codebase.
- ❌ Live Coder execution — not found in codebase.
- ❌ Autonomous dispatch — not found.
- ❌ Recursive tool loop — not found.
- ❌ Command execution added by Pi/Coder seam — not found.
- ❌ Worker orchestration added by Pi/Coder seam — not found.
- ❌ Sandbox execution — not found.
- ❌ Runtime dispatch from Pi/Coder seam — not found.
- ❌ Transcript persistence from Pi/Coder seam — not found.
- ❌ Receipt creation route for Pi/Coder — not found.
- ❌ Artifact creation route for Pi/Coder — not found.
- ❌ Receipt linkage for Pi/Coder — not found (C05 deferred).
- ❌ Frontend execution controls for Pi/Coder — not found.
- ❌ Release support for Pi/Coder invocation — not present.

## Authority and Ownership Boundaries

| Boundary | Preserved? | Evidence |
|----------|-----------|----------|
| Guardian policy ownership | ✅ | `PiInvocationEnvelope` carries permission_policy; contracts assume Guardian authority |
| Command bus authority | ✅ | Command bus is separate — C05-proven, no Pi/Coder commands |
| Transcript ownership | ✅ | Chat worker is separate — no Pi/Coder transcript injection |
| Source-message lineage | ✅ | `pi_invocation_boundary_contract` requires lineage_source_message_id |
| Result return control | ✅ | `CodingAgentResult` is contract-only — no autonomous return |
| Provider lane separation | ✅ | `PiProviderLaneClass` enum defines LOCAL/REMOTE/HYBRID/EXTERNAL/MINIMAX — no lane bleed |
| Identity boundary | ✅ | Envelope carries user_id, project_id — no identity spoofing |
| No bypass of canonical tokens | ✅ | `guardian/protocol_tokens.py` is separate — Pi tokens are additional, not replacement |
| No bypass of export/restore lineage | ✅ | `account-export-restore-contract.md` not impacted by Pi contracts |

## Data and Persistence Surface

| Check | Result |
|-------|--------|
| Pi/Coder-specific persistence tables | **Absent** — no `PiInvocation`, `PiHarnessResult`, `PiInvocationArtifact` tables |
| `WorkOrderResultReceipt` | Present (C03) — not Pi/Coder-specific |
| `CommandRun` | Present (C03) — not Pi/Coder-specific |
| `coding_work_orders` | Present (C03) — not Pi/Coder-specific |
| Agent orchestration tables | Deployment/run tracking likely uses existing agent store — no Pi-specific tables |
| Schema migration for Pi/Coder | **Absent** — no migration file found for Pi/Coder tables |
| Existing migration evidence for C04 | **None** — no schema touches for Pi/Coder |
| Migration risks | **Low** — no schema drift; contracts are type-only |

## Operator Surface and Observability

| Surface | Type | Pi/Coder relevance |
|---------|------|--------------------|
| `CodingWorkOrdersPanel` | Read-only evidence | Work orders, command runs, tool-turn, receipt evidence — C03/C05/C06 proven. Not Pi/Coder-specific. |
| `GuardianOperatorWorkspaceLens` | Read-only workspace | Composes existing surfaces. No Pi/Coder controls. |
| `GuardianWorkspaceCommandRunEvidenceCard` | Read-only evidence | Command-run pointers. Not Pi/Coder-specific. |
| `GuardianWorkspaceToolTurnEvidenceCard` | Read-only evidence | C05 tool-turn observability. Not Pi/Coder-specific. |
| `GuardianWorkspaceReceiptEvidenceCard` | Read-only evidence | Receipt pointers. Not Pi/Coder-specific. |
| Execution controls | **Missing by design** | No dispatch, execute, run-tool, invoke-Coder controls in workspace or CodingWorkOrdersPanel |
| Envelope preview | **Missing** | No UI for previewing a CodingAgentTaskEnvelope before execution |
| Validation-only run mode | **Missing** | No "validate then execute" UI flow |
| Provider lane selection | **Missing** | No UI for choosing Pi provider lanes |
| Diagnostics-only surfaces | **Limited** | EventConsole has raw event stream — not redaction-reviewed for Pi/Coder content |

## Test and Proof Surface

| Test area | Status |
|-----------|--------|
| `tests/pi/` | **Not found** — no Pi/Coder-specific tests |
| `tests/routes/` | Contains command bus, work-order, receipt tests — not Pi/Coder-specific |
| `tests/command_bus/` | C05-proven — not Pi/Coder-specific |
| `tests/core/` | Local runtime preset tests, turn lock tests — not Pi/Coder-specific |
| Pi token shape tests | **Not found** |
| Envelope validation tests | **Not found** — `guardian/pi/validation.py` exists but has no tests |
| Harness result tests | **Not found** |

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Accidental release-claim widening | **HIGH** | C04 must explicitly state that no autonomous delegation, Pi/Coder execution, or recursive tool loops are supported |
| Conflating provider lane with Pi/Coder invocation governance | MED | `PiProviderLaneClass` is a separate enum — must not be collapsed into runtime provider state |
| Treating command-run evidence as completion proof | MED | Command-run card already truth-labels — C04 must preserve this |
| Treating receipt evidence as completion proof | MED | Receipt card already truth-labels — C04 must preserve this |
| Hidden autonomous execution | **HIGH** | No autonomous execution found — C04 must ensure none is introduced |
| Ungoverned result return | **HIGH** | `CodingAgentResult` is contract-only — C04 must enforce governance on result return |
| Lineage loss | MED | Lineage is encoded in envelope fields — C04 must preserve this in any implementation |
| Raw payload exposure | **HIGH** | C05 redaction boundaries must apply to any C04 envelope/result display |
| Schema drift | LOW | No Pi/Coder tables exist — C04 must not expand schema without architecture proof |
| UI execution controls appearing before runtime governance | **HIGH** | C04 must not add execute/dispatch controls until runtime governance is proven |

## Recommended C04 Backlog

1. `C04-T001: Pi/Coder invocation boundary seam audit` ← THIS TASK
2. `C04-T002: Define Pi/Coder invocation boundary acceptance contract`
3. `C04-T003: Envelope preview contract (operator-visible envelope before execution)`
4. `C04-T004: Validation-only run mode contract`
5. `C04-T005: Result return governance contract`
6. `C04-T006: Envelope preview UI scaffold`
7. `C04-T007: Validation-only run mode UI scaffold`
8. `C04-T008: C04 integration proof and closeout`

## Release Boundary

- No runtime behavior changed.
- No command invocation semantics changed.
- No tool execution semantics changed.
- No Coder execution semantics changed.
- No Pi SDK behavior changed.
- No chat completion semantics changed.
- No persistence schema changed.
- No protocol tokens added or renamed.
- No receipt linkage implemented.
- No release claim widened.
- No autonomous delegation claim added.
- No Pi/Coder execution claim added.
- No recursive tool-loop claim added.
- No artifact creation claim added.
- No receipt creation claim added.
- No work-order completion claim added.
- No successful merge claim added.

## Documentation Follow-Through

- `00-current-state.md` unchanged.
- ADRs unchanged.
- C03 files unchanged.
- C05 files unchanged.
- C06 closeout unchanged.
- No backend files changed.
- No frontend files changed.
- No tests changed.
- C04 campaign scaffold created.
- C04 proof-pack updated.
- C04 decision-log updated.
- C04 backlog created.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C04-T002: Define Pi/Coder invocation boundary acceptance contract`
