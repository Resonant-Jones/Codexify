# C04-T003 Proof Matrix: Pi/Coder Invocation Boundary

## Gate Decision

**`go`** — The proof matrix is complete. C04 may proceed to C04-T004.

## Scope

This is a docs-only proof matrix. It turns the C04-T002 acceptance contract into a task-by-task proof rubric. It does **not** implement Pi/Coder invocation.

## Inputs Read

All 25 required pre-reads available. No missing inputs. All 11 reference targets available from C04-T001.

## Proof Matrix Purpose

This matrix prevents future C04 work from accepting scaffolds, docs, mocked tests, route presence, or pointers as runtime proof. Every future C04 implementation task must identify:

- **Target acceptance state**
- **Current acceptance state**
- **Evidence required for promotion**
- **Required blockers** if evidence is missing
- **Release-boundary statement**

Release support is governed only by current-state/release evidence, not by C04 proof alone.

## Proof State Ladder

| State | Entry evidence | Promotion evidence | Forbidden claim | Required proof artifact |
|-------|---------------|--------------------|-----------------|------------------------|
| `not_started` | Campaign selected, no files | Seam audit or contract | "Already underway" | Seam audit or contract artifact |
| `contract_only` | Types/dataclasses/enums exist | Test + documentation | "Runtime execution" | Contract + test + decision log |
| `scaffolded` | Route or UI component skeleton | Wiring to runtime + test | "Invocation works" | Source + route test + decision log |
| `implemented_unproven` | Code exists, not tested | Tests + dry-run proof | "Correct behavior" | Test suite + dry-run artifact + decision log |
| `runtime_proven_internal` | Tests pass, dry-run succeeded | Supported-path test | "Release-ready" | Internal proof report + decision log |
| `operator_visible_read_only` | Read-only workspace card | Truth-labeling + redaction test | "Execution controls" | UI test + redaction test + decision log |
| `blocked` | Missing dependency or risk unresolved | Resolve blocker | "Partially accepted" | Blocker resolution evidence |
| `deferred` | Intentional postponement | Revisit trigger | "Hidden readiness" | Reason recorded in backlog |

## Core Boundary Proof Matrix

| Boundary Surface | Current state | Target state for C04 | Required evidence | Insufficient shortcut | Missing-evidence gate |
|-----------------|---------------|---------------------|-------------------|-----------------------|-----------------------|
| `PiInvocationEnvelope` | `contract_only` | `contract_only` (verified) | Contract test + validation test | Import test only | `next-proof-needed` |
| `PiInvocationReceipt` | `missing` (enum only) | `contract_only` | Receipt dataclass + contract test | Enum presence | `next-proof-needed` |
| `PiInvocationArtifact` | `missing` | `deferred` (C04 does not require) | Deferred reason recorded | — | `deferred` — not blocking |
| `PiHarnessResult` | `contract_only` | `contract_only` (verified) | Contract test | Dataclass-only presence | `next-proof-needed` |
| `PiInvocationValidationResult` | `missing` | `contract_only` | Validation result type + contract test | Validation function presence | `next-proof-needed` |
| Permission validation | `contract_only` | `contract_only` (verified) | Permission validation test + fail-closed test | Type definition | `next-proof-needed` |
| Guardian policy decision | `missing` | `contract_only` | Decision type + contract test | Route presence | `hold` — policy is foundational |
| Command bus authority | `implemented` (C05) | `implemented` (preserved) | Already proven by C05 | — | Prohibited to regress |
| Invocation id generation | `scaffold` | `scaffold` (verified) | Id consistency contract | UUID test only | `next-proof-needed` |
| Harness identity | `contract_only` | `contract_only` (verified) | Harness registry test | Adapter kind literal | `next-proof-needed` |
| Result return path | `scaffold` | `contract_only` (verified) | Result shape test + linkage test | Route presence | `next-proof-needed` |
| Transcript lineage | `contract_only` | `contract_only` (verified) | Lineage trace contract test | Field presence | `hold` — lineage is foundational |
| Source-message lineage | `contract_only` | `contract_only` (verified) | Source message propagation contract test | Field presence | `hold` — lineage is foundational |
| Artifact lineage | `deferred` | `deferred` | Not required for C04 | — | `deferred` |
| Receipt lineage | `deferred` | `deferred` (C05 deferred) | Not required for C04 | — | `deferred` |
| Validation outcome | `contract_only` | `contract_only` (verified) | Validation outcome contract test | Enum presence | `next-proof-needed` |
| Redaction posture | `contract_only` (C05) | `contract_only` (verified) | Redaction contract test | C05 docs alone | `next-proof-needed` |
| Failure state handling | `contract_only` | `contract_only` (verified) | Fail-closed contract test | Happy-path test only | `next-proof-needed` |
| No recursive loop enforcement | `contract_only` | `contract_only` (verified) | Policy validation test | Contract assertion | `hold` — safety critical |
| No autonomous dispatch enforcement | `contract_only` | `contract_only` (verified) | Policy validation test | Contract assertion | `hold` — safety critical |
| Provider lane separation | `contract_only` | `contract_only` (verified) | Lane separation contract test | Enum presence | `next-proof-needed` |
| Minimax provider lane separation | `contract_only` | `deferred` (not activated) | Deferred reason | Enum presence | `deferred` |
| Operator read-only evidence | `missing` | Not targeted by C04-T003 | — | — | Deferred to C04-T006+ |
| Tests | `missing` (no tests/pi/) | Not targeted by C04-T003 | — | — | Deferred to C04-T006+ |
| Runtime proof | `missing` | Not targeted by C04-T003 | — | — | Deferred to C04 implementation |
| Release support | `missing` | Not targeted by C04 | Only via release governance | Any C04 evidence alone | Prohibited to claim |

## Evidence Class Matrix

| Evidence class | Proves | Does not prove | Required for | Example artifact |
|---------------|--------|---------------|-------------|-----------------|
| Static source inspection | Code structure, presence/absence | Runtime execution, correctness | C04-T001 (complete) | Seam audit |
| Contract tests | Type shape, validation logic, fail-closed | Runtime execution, provider integration | C04-T002+ contract validation | Test suite |
| Route tests | Route registration, request/response shape, auth | Runtime execution, adapter behavior | C04 implementation | Route test suite |
| Dry-run proof | Code executes in dev without side effects | Production readiness, release support | C04 implementation | Dry-run report |
| Internal runtime proof | Code executes with expected output in dev | Release support, operator safety | C04 implementation | Test + proof report |
| Operator read-only proof | Operator inspects state read-only | Execution governance, mutation safety | C04-T006+ UI tasks | UI test + redaction test |
| Supported-path proof | Code on supported install path | All environments, edge cases | Before release claim | Supported-path test run |
| Docs validation | Docs consistency, heading structure, link integrity | Runtime behavior, execution correctness | All C04 tasks | `python3 scripts/validate_docs.py` |
| Git diff hygiene | Patch cleanliness, trailing whitespace, conflict markers | Code correctness, behavior safety | All C04 tasks | `git diff --check` |
| Release proof | Supported-path performance, integration, rollback | N/A | Before release claim | Multiple evidence sources |

### Rules

- Docs validation proves docs hygiene only.
- Git diff hygiene proves patch cleanliness only.
- Static inspection proves presence/absence only.
- Contract tests prove shape/validation only.
- Route tests prove route behavior only.
- Dry-run proof does not prove live execution.
- Internal runtime proof does not prove release support.
- Operator read-only proof does not prove execution.
- Supported-path proof is required before any release-support claim.

## Gate Outcome Matrix

| Condition | Gate |
|-----------|------|
| Proof artifact missing | `next-proof-needed` |
| Source lineage missing | `hold` |
| Policy decision missing | `hold` |
| Permission posture missing | `hold` |
| Command authority bypass | `hold` |
| Raw payload exposure | `hold` |
| Route presence only | `next-proof-needed` |
| Type presence only | `next-proof-needed` |
| Mocked tests only | `next-proof-needed` |
| Runtime execution unproven | `next-proof-needed` |
| Unsupported release claim | `hold` |
| Implementation outside declared files | `hold` |
| Docs validation missing | `next-proof-needed` |
| `git diff --check` failure | `next-proof-needed` |
| Task name includes implementation details instead of name only | `next-proof-needed` |

## Required Proof Rows for Future C04 Tasks

Every future C04 proof-pack section must include:

| Field | Required |
|-------|----------|
| Task ID | ✅ |
| Target boundary surface | ✅ |
| Current state before task | ✅ |
| Target state after task | ✅ |
| Files changed | ✅ |
| Evidence class | ✅ |
| Proof artifact | ✅ |
| Tests or docs validation | ✅ |
| Release-boundary statement | ✅ |
| Prohibited claims check | ✅ |
| Gate decision | ✅ |
| Next task by name only | ✅ |

## Lineage Proof Requirements

| Lineage element | Required for C04? | Gate if missing |
|-----------------|-------------------|-----------------|
| Source thread id | ✅ | `hold` |
| Source message id | ✅ | `hold` |
| Request or attempt id | When available | `next-proof-needed` |
| Invocation id | ✅ | `hold` |
| Harness or adapter id | ✅ | `hold` |
| Permission posture | ✅ | `hold` |
| Result artifact reference | When available | Not blocking |
| Receipt reference | When available | Not blocking (deferred) |
| Validation outcome | ✅ | `next-proof-needed` |
| Redaction posture | ✅ | `next-proof-needed` |

### Rules

- Local surrogate ids do not satisfy lineage.
- Lineage must survive export/restore per Account Export + Restore Contract.
- Lineage fields must not be fabricated by the adapter.

## Receipt and Artifact Proof Requirements

| Proof row | Required for C04? | Gate |
|-----------|-------------------|------|
| Invocation receipt contract | ✅ (shape + status) | `next-proof-needed` |
| Command-run receipt (C03) | Already proven | — |
| Work-order receipt (C03) | Already proven | — |
| Artifact reference contract | Deferred for C04 | `deferred` |
| Artifact payload contract | Deferred for C04 | `deferred` |
| Completion verdict | Not required for C04 | Prohibited to claim |

### Rules

- Receipt presence does not prove completion.
- Artifact presence does not prove correctness.
- These three concepts must not be collapsed into one status string.

## Operator Surface Proof Requirements

| Proof row | Required for C04? | Gate |
|-----------|-------------------|------|
| Invocation id display | C04-T006+ | Read-only only |
| State display | C04-T006+ | Per acceptance state model |
| Policy decision display | C04-T006+ | Approved/rejected summary |
| Permission summary display | C04-T006+ | High-level only |
| Harness id display | C04-T006+ | Read-only |
| Result availability display | C04-T006+ | "Available" or "Pending" |
| Receipt id display | C04-T006+ | When available |
| Artifact reference display | C04-T006+ | When available |
| Validation summary display | C04-T006+ | Valid/rejected + reason |
| Redaction state display | C04-T006+ | Summary of redactions |
| No raw payload exposure | ✅ Always | `hold` if violated |
| No execution controls | ✅ Always | `hold` if violated |

### Prohibited Controls

Dispatch, execute, retry, replay, approve, complete, create artifact, create receipt, run tool, invoke tool, merge, mark complete.

## Redaction and Safety Proof Requirements

Future C04 tasks must prove absence of:

- Raw args
- Raw command payloads
- Raw `extra_meta`
- Raw `result_json`
- Raw event payloads
- Stack traces
- Hidden prompts
- System prompts
- Secrets
- Credentials
- Unredacted payloads

Fail-closed behavior is required if redaction posture is unknown.

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
- C04 proof matrix created.
- C04 proof-pack updated.
- C04 decision-log updated.
- C04 backlog updated.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C04-T004: Repair Pi/Coder invocation receipt and artifact contract gaps`
