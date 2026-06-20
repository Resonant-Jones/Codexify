# C04-T002 Acceptance Contract: Pi/Coder Invocation Boundary

## Gate Decision

**`go`** — The acceptance contract is complete. C04 may proceed to C04-T003.

## Scope

This is a docs-only acceptance contract. It governs future C04 implementation and proof tasks. It does **not** implement Pi/Coder invocation.

## Inputs Read

All 24 required pre-reads available. No missing inputs. All 11 reference targets available from C04-T001.

## Contract Purpose

This contract defines what must be true before any Pi/Coder invocation boundary work can be accepted. It explicitly separates:

- **Contract-only scaffolds** — types, dataclasses, enums that exist as types but have no runtime wiring.
- **Implementation presence** — code that exists in the repository but may not be invoked.
- **Runtime proof** — code that is proven to execute via tests, dry runs, or supported-path evidence.
- **Release support** — the subset of runtime-proven behavior that is part of the active release promise.

Later tasks must not treat route presence, type presence, or docs language as runtime proof.

## Acceptance State Model

| State | Meaning | Allowed evidence | Forbidden inference | Promotion requirement |
|-------|---------|------------------|---------------------|-----------------------|
| `not_started` | No work has begun | None | None | Create contract or seam audit |
| `contract_only` | Types and contracts exist, no runtime wiring | Type definitions, dataclasses, enum definitions, contract docs | May not claim implementation, runtime proof, or release support | Implement + test |
| `scaffolded` | Route or component skeleton exists, not wired to runtime | Route signature, component shell, placeholder UI | May not claim execution, invocation, or receipt creation | Wire to runtime + test |
| `implemented_unproven` | Code exists but has no runtime proof | Source code, import paths | May not claim runtime execution, completion, or correctness | Add tests + dry-run proof |
| `runtime_proven_internal` | Code executes and passes tests in dev environment | Tests passing, dry-run evidence, source inspection | May not claim release support or operator visibility | Add operator read-only surface |
| `operator_visible_read_only` | Runtime-proven behavior is visible to operator in read-only form | Operator workspace cards, read-only evidence surfaces, truth-labeling | May not claim execution controls or mutation capability | Governance review |
| `blocked` | Cannot proceed due to missing dependency, unresolved risk, or architecture conflict | Blocked evidence recorded in backlog + decision log | May not claim partial completion as acceptance | Resolve blocker |
| `deferred` | Intentionally postponed | Reason recorded | May not claim hidden readiness | Revisit trigger |

### Key Rules

- **Release support is not an acceptance state.** It remains governed by `00-current-state.md` and requires separate release boundary proof.
- **Import shape tests are not runtime proof.** They prove types exist, not that code executes.
- **Mock-only tests are not runtime proof.** They must be paired with supported-path or dry-run evidence.
- **A green health endpoint alone is not acceptance.** Health checks verify infrastructure, not invocation correctness.

## Invocation Boundary Acceptance Criteria

### Invocation Envelope

- `PiInvocationEnvelope` must carry: invocation id, coding task id, work order id, campaign id, adapter kind, permission policy, instructions, lineage, provider lane, user identity, project identity, attempt id.
- Envelope must be validatable in isolation before any execution decision.
- Envelope must carry Guardian-owned permission posture — not delegate policy decisions to the adapter.

### Permission Posture

- Permission policy must include: allow_shell, allow_network, allow_write, allowed_paths, max_runtime_seconds.
- Policy must be Guardian-enforced, not adapter-self-declared.
- Missing or incomplete policy must default to fail-closed.

### Guardian Policy Ownership

- Guardian owns the invocation decision. No adapter may auto-execute.
- The invocation seam must require explicit Guardian approval before execution.
- Guardian may reject invocations based on policy, permission, lineage, or risk.

### Command Bus Authority

- Command bus authority is separate from Pi/Coder invocation.
- Pi/Coder adapters must not bypass command bus authority.
- Command invocation routes must remain governed by C05+C03 contracts.

### Result Return

- Result return must carry: invocation id, harness id, result class, output summary, error summary, exit code, sandbox path, changeset summary, commit hash (when applicable).
- Result must be linked to its originating envelope.
- Result must not auto-apply to the worktree without Guardian review.

### Transcript Lineage

- Transcript must record: source thread id, source message id, invocation id, adapter kind, permission posture, result class.
- Lineage must be traceable from work order → invocation → harness → result → receipt.
- Export/restore lineage obligations remain governed by the Account Export + Restore Contract.

### Source-Message Lineage

- Envelope must carry lineage_source_message_id — the message that prompted the invocation.
- This must not be overridden or fabricated by the adapter.

### Invocation Receipt Semantics

- Invocation receipt records that an invocation was attempted and what the outcome was.
- Receipt does not prove completion, success, or work-order fulfillment.
- Receipt fields: invocation id, receipt id, status (per `PiInvocationReceiptStatus`), harness id, result class, output summary, error summary, commit hash, created_at.
- Receipt must not be confused with command-run receipt or work-order receipt.

### Invocation Artifact Semantics

- Artifact records what was produced by an invocation: code changes, output, sandbox path, changeset.
- Artifact does not prove merge readiness, correctness, or completion.
- Artifact must not be created unless a governed invocation produces one.
- Artifact creation is not required for C04 acceptance — C04 may defer artifact creation to C09 or later.

### Provider Lane Separation

- Pi provider lane must remain distinct from chat/retrieval provider lanes.
- `PiProviderLaneClass` enum (LOCAL, REMOTE, HYBRID, EXTERNAL, MINIMAX) governs lane routing.
- Lane selection must be explicit — no silent promotion from local to remote.

### Minimax Provider Lane

- MINIMAX lane exists as a token in `PiProviderLaneClass`.
- MINIMAX lane must not be activated until separately governed with provider-state proof.
- C04 does not require MINIMAX lane activation.

### Bounded Failure

- Invocation failure must be bounded: fail-closed, no auto-retry without governance.
- Failure reason must be surfaced in result/error summary.
- Auto-retry, exponential backoff, or unsupervised recovery are prohibited.

### No Recursive Loop

- Pi/Coder invocation must not autonomously invoke itself or another adapter.
- Bounded tool-turn contracts (C05) apply to any adapter that executes tools.
- Recursive execution must be blocked at the policy level.

### No Autonomous Dispatch

- Invocations must be Guardian-initiated, not adapter-self-initiated.
- No event, timer, hook, or plugin may autonomously dispatch a Pi/Coder invocation.

### No Hidden Writes

- Invocations must not perform hidden writes: no ungoverned file writes, no ungoverned network access, no ungoverned sandbox escape.
- The permission policy governs allowed write paths and network access.

## Proof Surface Matrix

| Surface | Minimum acceptable evidence | Not enough by itself | Required blocker if missing |
|---------|---------------------------|---------------------|----------------------------|
| `PiInvocationEnvelope` | Shape test + validation test | Type definition alone | C04 cannot proceed past contract-only |
| `PiInvocationReceipt` | Shape test + create test + readback test | Enum presence alone | Receipt linkage is deferred — C04 can proceed with receipt contract, not implementation |
| `PiInvocationArtifact` | Deferred for C04 | Contract presence alone | Artifact creation is not required for C04 acceptance |
| `PiHarnessResult` | Shape test + harness output test | Import test only | Harness result cannot be claimed as execution proof |
| `PiInvocationValidationResult` | Validation test on envelope | Function presence alone | Envelope cannot be claimed validatable |
| Permission validation | Policy validation test + fail-closed test | Type definition alone | Permission posture cannot be claimed governed |
| Guardian policy decision | Decision logic test + fail-closed test | Route presence alone | Cannot claim Guardian owns invocation |
| Command bus boundary | Command bus authority tests (C05) | Route presence alone | Already proven by C05 |
| Result return path | Result shape test + linkage test | Dataclass presence alone | Cannot claim result return is governed |
| Transcript lineage | Lineage trace test from envelope to result | Field presence alone | Cannot claim lineage integrity |
| Source-message lineage | Lineage test — source message id propagates | Field presence alone | Cannot claim source traceability |
| Artifact lineage | Deferred for C04 | — | Not required for C04 acceptance |
| Receipt lineage | Deferred for C04 | — | Not required for C04 acceptance; C05 deferred |
| Operator read-only evidence | Workspace card + test + truth-labeling | Workspace scaffold without data | Operator surface must not claim execution proof |
| Redaction and safe summary | Redaction test per C05 contract | Component presence | Must not expose raw payloads |
| Tests | Contract tests + route tests + supported-path proof | Import tests only | Cannot claim runtime proof |
| Runtime proof | Dry-run proof + supported-path proof | Mock-only tests | Cannot claim execution |
| Release support | N/A — governed by `00-current-state.md` | Any C04 evidence alone | Cannot claim release support |

## Prohibited Acceptance Shortcuts

The following must NOT be accepted as sufficient proof for any C04 task gate:

- Docs language alone (including ADRs and architecture specs).
- Type definitions alone (dataclasses, enums, Literal types).
- Route presence alone (router registered, endpoint exists).
- Scaffold function presence alone (function exists, returns placeholder).
- Command-run pointer presence alone (work-order has latest_run_id).
- Receipt pointer presence alone (work-order has latest_receipt_id).
- Frontend button presence alone (component renders a button).
- Mocked test only (no dry-run or supported-path evidence).
- Import test only (test imports a module, no execution assertion).
- CLI help output alone (Pi CLI has --help text).
- Provider catalog presence alone (Minimax or Pi listed in catalog).
- Health endpoint green state alone (health=ok for any service).
- Unsupported local manual run without recorded proof.

## Required Runtime Proof Classes

| Proof class | What it proves | What it does not prove | When required |
|-------------|---------------|----------------------|---------------|
| Static source inspection | Code structure, type presence, import paths | Execution, runtime behavior, correctness | C04-T001 seam audit — complete |
| Contract tests | Type shape, validation logic, fail-closed behavior | Runtime execution, provider integration | C04-T003+ contract validation |
| Route tests | Route registration, request/response shape, auth | Runtime execution, adapter behavior | C04-T003+ route validation |
| Dry-run proof | Code executes in dev environment without side effects | Production readiness, release support | C04 implementation tasks |
| Internal runtime proof | Code executes and produces expected output in dev | Release support, operator safety | C04 implementation tasks |
| Operator read-only proof | Operator can inspect invocation state read-only | Execution governance, mutation safety | C04-T006+ UI tasks |
| Supported-path proof | Code executes on supported install path | All environments, edge cases | Before any release claim |

**Docs validation is not runtime proof.** `python3 scripts/validate_docs.py` passing means docs are consistent, not that code executes.

## Result Return and Lineage Requirements

### Minimum Acceptable Lineage

Future result return must carry:

| Lineage element | Type | Required |
|-----------------|------|----------|
| Source thread id | int or string | ✅ |
| Source message id | int or string | ✅ |
| Request or attempt id | string | When available |
| Invocation id | string | ✅ |
| Harness id or adapter id | string | ✅ |
| Permission posture | object | ✅ |
| Result artifact reference | string or null | When available |
| Receipt reference | string or null | When available |
| Validation outcome | `PiInvocationValidationOutcome` | ✅ |
| Redaction posture | summary object | ✅ |

### Rules

- Local surrogate ids must not replace lineage.
- Lineage must survive export/restore per the Account Export + Restore Contract.
- Lineage fields must not be fabricated by the adapter.

## Receipt and Artifact Acceptance Rules

### Required Distinctions

| Item | Definition | Proves? |
|------|-----------|---------|
| Invocation receipt | A record of an invocation attempt and its outcome | Proves invocation was attempted, not that it succeeded or completed |
| Command-run receipt | A record of a command bus run (C03) | Proves command execution, not Pi/Coder invocation |
| Work-order receipt | A record of observed results for a work order (C03) | Proves observation, not completion |
| Artifact reference | A reference to a produced artifact | Proves an artifact was referenced, not its contents |
| Artifact payload | The actual content of an artifact | Proves payload exists, not that it is correct or safe |
| Completion verdict | A separate governance decision | Requires human review or policy evaluation — not provided by receipt alone |

### Rules

- These must not be collapsed into one status string.
- "Receipt present" does not equal "invocation complete."
- "Artifact present" does not equal "correct output."

## Operator Surface Acceptance Rules

### Read-Only Until Governance Exists

Operator surfaces must remain read-only until runtime governance is proven. Execution controls must not appear before governance.

### Safe Fields for Read-Only Evidence

| Field | Safe to render | Notes |
|-------|---------------|-------|
| Invocation id | ✅ | Stable public identifier |
| State | ✅ | Per acceptance state model |
| Policy decision | ✅ | Approved/rejected/deferred |
| Granted permission summary | ✅ | High-level: "shell allowed, network denied" |
| Harness id | ✅ | Adapter identifier |
| Result availability | ✅ | "Result available" or "Result pending" |
| Receipt id | ✅ | Only when a receipt exists |
| Artifact reference id | ✅ | Only when an artifact reference exists |
| Validation summary | ✅ | "Valid", "Rejected + reason" |
| Redaction state | ✅ | Summary of redactions applied |

### Prohibited from Operator Surfaces

- Raw args.
- Raw command payloads.
- Raw `extra_meta`.
- Raw `result_json`.
- Raw event payloads.
- Stack traces.
- Hidden prompts.
- System prompts.
- Secrets.
- Credentials.
- Unredacted payloads.

### Prohibited Execution Controls (Before Governance)

- Dispatch.
- Execute.
- Retry.
- Replay.
- Approve.
- Complete.
- Create artifact.
- Create receipt.
- Run tool.
- Invoke tool.
- Merge.
- Mark complete.

## Failure and Blocker Rules

### Required Fail-Closed Cases

| Condition | Required action |
|-----------|----------------|
| Missing policy decision | Gate `hold` |
| Missing source lineage | Gate `hold` |
| Missing permission posture | Gate `hold` |
| Unknown harness identity | Gate `hold` |
| Unvalidated result artifact | Gate `next-proof-needed` |
| Unvalidated receipt | Gate `next-proof-needed` |
| Raw payload exposure | Gate `hold` |
| Command authority bypass | Gate `hold` |
| Provider lane confusion | Gate `hold` |
| Recursive tool request | Gate `hold` |
| Autonomous dispatch request | Gate `hold` |
| Unsupported release claim | Gate `hold` |

### Gate Decision Rules

- **`go`**: All required criteria met. Evidence recorded in proof-pack + decision-log. Next task may proceed by name only.
- **`hold`**: Critical blocker present (execution control before governance, raw payload exposure, authority bypass, release-claim widening). Implementation must not proceed.
- **`next-proof-needed`**: Insufficient evidence (missing tests, incomplete validation, missing proof-pack). Task may proceed after evidence is provided.

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
- C04 acceptance contract created.
- C04 proof-pack updated.
- C04 decision-log updated.
- C04 backlog updated.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C04-T003: Define Pi/Coder invocation boundary proof matrix`
