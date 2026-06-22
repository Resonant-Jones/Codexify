# Wave 3 Selection After C06 Closeout

## Gate Decision

**`go`** — Selected: **C04: Pi/Coder Invocation Boundary**

## Scope

This is a docs-only selection artifact. It does **not** implement the selected campaign, create first-task implementation instructions, or widen release claims.

## Inputs Read

All required pre-reads from `docs/architecture/`, `docs/Campaign/guardian-maturity/` campaign closeouts, and campaign map available. No missing inputs.

| # | Key inputs | Status |
|---|-----------|--------|
| 1–15 | `docs/architecture/*.md` (15 files) | ✅ |
| 16–17 | Wave 2 selection artifacts | ✅ |
| 18–23 | C03, C05, C06 closeouts + proof docs | ✅ |
| 24+ | Campaign map, backlog, decision logs | ✅ |

## Current Campaign State

| Campaign | Status | Closeout evidence | Selection relevance |
|----------|--------|-------------------|---------------------|
| C03 Coding Delegation Spine | closed | Work-order CRUD, command bus manifest/invoke/run-readback, receipt persistence/linkage, operator receipt evidence | C03 provides the infrastructure C04 needs: work-orders, command bus, receipt evidence |
| C05 Command Bus and Tool Turn Observability | closed | Seam audit, read model contract, backend helper/route, Command Center tool-turn UI | C05 provides bounded tool-turn observability — essential for governed invocation proof |
| C06 Guardian Operator Workspace | closed | Operator workspace lens, HealthOverview, CodingWorkOrdersPanel, command-run/tool-turn/receipt evidence cards | C06 provides the operator UI surface for C04 invocation envelope preview |

## Wave 2 Closure Summary

### What Wave 2 Proved

- **C03**: Work-order/command-run/receipt infrastructure exists and is operator-visible. Command bus has 106 auto-discovered commands. Receipt persistence, readback, and fail-closed linkage are proven. 52 backend + 16 frontend tests.
- **C05**: Bounded tool-turn observability is read-only, test-able, and redaction-safe. Tool-turn state, loop-stop reason, command-run linkage, and evidence durability are surfaceable. 108 backend + 142 frontend tests.
- **C06**: Operator workspace can compose existing truth surfaces into a unified read-only lens. Command-run, tool-turn, and receipt evidence cards are live. 58 shell + 128 broader frontend tests.

### What Remains Explicitly Unproven

- **Pi/Coder invocation** has not been made operator-visible.
- No governed invocation seam exists in the UI.
- No envelope preview for coding-agent work exists.
- No validation-only run mode is surfaceable.
- Receipt linkage remains deferred (C03 receipt store not wired in command bus routes).

## Candidate Campaigns Considered

### C04: Pi/Coder Invocation Boundary (Wave 3, HIGH risk)

- **Why now**: C03 proved delegation infrastructure. C05 proved observability. C06 proved operator workspace. C04 is the logical next step — make Pi/Coder invocation governed, visible, and bounded. The campaign map lists C04 as Wave 3 and directly dependent on C03.
- **Supporting evidence**: Pi Invocation Boundary Contract exists in `docs/architecture/pi-invocation-boundary-contract.md`. C03 work-order/command-bus infrastructure is proven. C06 operator workspace provides the UI surface for envelope preview.
- **Dependency on C03/C05/C06**: C03 work-orders for task tracking. C05 observability for invocation evidence. C06 workspace for envelope preview UI.
- **Risk**: HIGH — involves backend route work, Pi/Coder interaction, and governance semantics. Must stay bounded — validation-only, no autonomous execution.
- **Non-goals**: No autonomous delegation. No ungoverned Pi/Coder execution. No recursive tool loops. No release widening.
- **First task**: `C04-T001: Pi/Coder invocation boundary seam audit`

### C07: Persona Studio and Agent Configuration (Wave 3, MED risk)

- **Why now**: Operator now has a workspace (C06) but cannot inspect or configure agent persona settings. Moving configuration from scattered assumptions into an inspectable surface would improve operator control.
- **Supporting evidence**: Persona Studio spec exists in `docs/architecture/persona-studio-spec.md`. C06 workspace provides the UI surface for configuration inspection.
- **Dependency on C03/C05/C06**: C06 workspace for UI surface. Otherwise partially independent.
- **Risk**: MED — frontend/config only. No backend route, schema, or provider changes per campaign map.
- **Non-goals**: No new backend persona execution. No model selection changes. No release widening.
- **First task**: `C07-T001: Persona Studio configuration surface seam audit`

### C08: Whoosh'd Runtime Setup and Local Model Management (Wave 3, MED risk)

- **Why now**: Operator workspace exists but local runtime configuration is not operator-safe. Model inventory, preset selection, readiness warnings, and state distinction need inspection surfaces.
- **Supporting evidence**: Config and Ops doc and local runtime presets exist. C06 workspace could host runtime configuration cards.
- **Dependency on C03/C05/C06**: C06 workspace for UI surface. Otherwise partially independent.
- **Risk**: MED — involves backend route and frontend changes per campaign map.
- **Non-goals**: No new runtime behavior. No model loading changes. No release widening.
- **First task**: `C08-T001: Whoosh'd runtime configuration seam audit`

| Candidate | Why now | Depends on | Risk | First task by name only | Selected |
|-----------|---------|------------|------|------------------------|----------|
| C04 Pi/Coder Invocation Boundary | Natural progression — C03/C05/C06 built the infrastructure; C04 governs invocation | C03 directly, C05/C06 for surface | HIGH | `C04-T001: Pi/Coder invocation boundary seam audit` | ✅ |
| C07 Persona Studio | Operator workspace exists; configuration is scattered | C06 for UI surface | MED | `C07-T001: Persona Studio configuration surface seam audit` | Deferred |
| C08 Whoosh'd Runtime | Operator workspace exists; runtime config not inspectable | C06 for UI surface | MED | `C08-T001: Whoosh'd runtime configuration seam audit` | Deferred |

## Selection Criteria

| Criterion | Weight | C04 | C07 | C08 |
|-----------|--------|-----|-----|-----|
| Closes highest-value proven gap | High | **Pi/Coder invocation gap is the highest-leverage unproven seam** | Configuration visibility gap | Runtime config visibility gap |
| Builds directly on accepted proof | High | **C03/C05/C06 all provide readiness** | C06 provides UI readiness | C06 provides UI readiness |
| Can be sliced atomically | Medium | **Seam audit is atomic, read-only** | Seam audit is atomic | Seam audit is atomic |
| Does not widen release claims | Critical | **Stays bounded — validation-only** | Safe | Safe |
| Requires no autonomous delegation | Critical | **Governed, not autonomous** | Safe | Safe |
| Requires no ungoverned Pi/Coder | Critical | **Governed only** | Not applicable | Not applicable |
| Preserves local-first beta truth | Critical | **Yes** | Yes | Yes |
| Clear proof surface | Medium | **Invocation Contract + C03 infrastructure** | Persona Studio spec | Config and Ops doc |

## Selected Wave 3 Campaign

**C04: Pi/Coder Invocation Boundary**

### Rationale

C04 is the sharpest next campaign after Wave 2. C03 proved that work-orders, command bus, and receipt evidence exist. C05 proved that tool-turn execution is observable and bounded. C06 proved that operator truth surfaces can be composed into a unified workspace. C04 closes the next seam: making Pi/Coder invocation governed, operator-visible, and bounded by validation-only semantics.

The Pi Invocation Boundary Contract already exists in `docs/architecture/pi-invocation-boundary-contract.md`. C04 must translate that contract into an inspectable governed invocation seam — envelope preview for coding-agent work, validation-only run mode, and explicit non-autonomous governance — without widening release claims.

C07 (Persona Studio) and C08 (Whoosh'd Runtime) are valuable but can be parallelized or sequenced after C04. They depend primarily on C06 workspace surfaces and are partially independent. C04 is the higher-risk, higher-leverage campaign that should precede less-dependent work.

### Prerequisite Evidence

- **C03**: Work-order CRUD, command bus (106 commands), receipt persistence/readback/linkage.
- **C05**: Bounded tool-turn observability, read model contract, redaction boundaries.
- **C06**: Operator workspace lens, command-run/tool-turn/receipt evidence cards.
- **Architecture**: Pi Invocation Boundary Contract, Agent Protocol Operations, Agent Tool Loop Contract.

### First Task by Name Only

**`C04-T001: Pi/Coder invocation boundary seam audit`**

### Expected Proof Surface

- Current Pi/Coder invocation seams audited.
- Pi Invocation Boundary Contract compared to current runtime.
- Gaps between contract and current state classified.
- Envelope preview readiness assessed.
- Validation-only run mode feasibility assessed.
- Atomic task backlog for C04 defined.

### Release-Boundary Statement

- No autonomous delegation implemented or claimed.
- No ungoverned Pi/Coder execution implemented or claimed.
- No recursive tool loops implemented or claimed.
- No artifact creation implemented or claimed.
- No receipt creation implemented or claimed.
- No work-order completion semantics implemented or claimed.
- No release claim widened.

## Deferred Candidates

| Candidate | Reason deferred |
|-----------|----------------|
| C07 Persona Studio | Valuable but lower leverage than C04. Partially independent — can be parallelized or sequenced after C04. No blocking dependency. |
| C08 Whoosh'd Runtime | Valuable but lower leverage than C04. Partially independent — can be parallelized or sequenced after C04. No blocking dependency. |
| Receipt linkage follow-through | Deferred from C05. Not a standalone campaign. Best addressed during C04 or as a follow-on task within a later execution ledger campaign. |

## Non-Claims

- No implementation started.
- No backend route added.
- No frontend behavior changed.
- No runtime behavior changed.
- No autonomous delegation proof added.
- No Pi/Coder execution proof added.
- No recursive tool-use proof added.
- No artifact creation proof added.
- No receipt creation proof added.
- No receipt-as-completion proof added.
- No release promise widened.

## Validation

```
git diff --check                    clean
python3 scripts/validate_docs.py     passed
```

No automated runtime tests apply — docs-only campaign selection.

## Final Gate

- **Decision**: `go`
- **Wave 3 campaign selected**: C04: Pi/Coder Invocation Boundary
- **Next step by name only**: `Create first task for C04: Pi/Coder Invocation Boundary`
