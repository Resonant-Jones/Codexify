# Wave 4 Campaign Selection After C04 Closeout

## Gate Decision

**`go`** — Selected: **C08: Whoosh'd Runtime Integration & Context Fidelity**

## Scope

This is a docs-only campaign selection artifact. It does **not** implement C08, create backend routes, modify frontend code, deploy models, change runtime behavior, or widen release claims.

## Inputs Read

| # | Key inputs | Status |
|---|-----------|--------|
| 1–15 | `docs/architecture/*.md` (15 files) | ✅ |
| 16–19 | C03, C05, C06, C04 closeouts | ✅ |
| 20 | Campaign map (`01-campaign-map.md`) | ✅ |
| 21 | Wave 3 selection artifact | ✅ |

All required inputs available. No missing inputs.

## Current Campaign State

| Campaign | Status | What it proved |
|----------|--------|----------------|
| C03 Coding Delegation Spine | closed | Work-order, command-run, receipt infrastructure |
| C05 Command Bus & Tool Turn Observability | closed | Bounded tool-turn evidence, redaction, readback route |
| C06 Guardian Operator Workspace | closed | Read-only operator workspace composing C03/C05 surfaces |
| C04 Pi/Coder Invocation Boundary | closed | Contracts, dry-run route, evidence adapter, operator evidence UI — validation-only, no execution |

## What The System Needs Right Now

The operator workspace (C06) can inspect work orders, command runs, tool-turn evidence, and dry-run Pi/Coder validation — but all of this depends on the inference provider layer being correctly configured, identified, and truthful. When Codexify speaks to local inference (Whoosh'd), the model must receive identity, context, retrieval evidence, runtime posture, and operator truth consistently. If the runtime layer is misconfigured or opaque, every operator truth surface above it is built on sand.

C08 closes that gap: it makes the local runtime configuration operator-safe, model-inventory verifiable, context-injection demonstrable, and runtime truth-surface honest.

After C08, the operator can trust that the engine room is wired correctly. Then C09 (execution authority) and C10 (result return) have a proven substrate to depend on.

## Candidate Campaigns Considered

| Candidate | Why now | Risk | Selection |
|-----------|---------|------|-----------|
| C08: Whoosh'd Runtime Integration & Context Fidelity | Fixes local model identity, context injection, runtime truth surfaces, provider routing | MED — backend config + frontend display | ✅ Selected |
| C07: Persona Studio Operator Surface | Product-facing persona/config surface; operator value | MED — frontend/config | Deferred |
| C09: Pi/Coder Invocation Execution Authority | Starts actual controlled execution beyond dry-run | HIGH — requires C08 + C10 substrate | Deferred |
| C10: Pi/Coder Result Return & Receipt Lineage | Result return, receipts, artifact lineage | MED — requires C09 | Deferred |
| C11: Pi/Coder Sandbox Worker Proof | Worker/sandbox proof for delegated execution | HIGH — requires C09 | Deferred |

### C08: Whoosh'd Runtime Integration & Context Fidelity

- **Why now**: C04 closed the invocation boundary. C06 gives the operator a workspace. But the local inference provider layer (Whoosh'd) has opaque configuration, unclear model inventory, and untestable context fidelity. The operator can't answer "is the model getting the right context?" — the most basic pre-requisite for any downstream execution work.
- **Supporting evidence**: `config-and-ops.md` and `local_runtime_presets.py` document existing runtime configuration surfaces. C06 operator workspace can host runtime truth cards. The `/v1/models` endpoint and provider health surfaces exist but are not operator-visible for local runtime.
- **Dependency on C03/C05/C06/C04**: C06 workspace for UI surfaces. C04 provider-lane contract for lane separation. C05 redaction posture for safe context display.
- **Risk**: MED — involves backend config route work and frontend display. No execution semantics changed.
- **Non-goals**: No model training. No provider switching. No execution. No result return. No release widening.
- **First task**: `C08-T001: Whoosh'd runtime configuration and model inventory seam audit`

## Selection Criteria

| Criterion | C08 | C07 | C09 | C10 | C11 |
|-----------|-----|-----|-----|-----|-----|
| Closes acute operator-blindness gap | **Yes — runtime opacity** | Partial | No | No | No |
| Builds on accepted proof | **C06 workspace + C04 lane contract** | C06 workspace | C04 boundary, needs C08/C10 | Needs C09 | Needs C09 |
| Atomic first task | **Config seam audit** | Config seam audit | Execution auth design | Receipt design | Worker proof design |
| Does not widen release | **Yes** | Yes | Needs care | Needs care | Needs care |
| Safer after C04 closeout | **Yes** | Yes | Needs substrate | Needs C09 | Needs C09 |
| Reduces local-only posture risk | **Yes — makes it inspectable** | Indirectly | No | No | No |
| Keystone — unlocks later campaigns | **Yes — C09/C10/C11 need trustworthy runtime** | No | Needs C08 | Needs C08+C09 | Needs C08+C09 |

## Selected Wave 4 Campaign

**C08: Whoosh'd Runtime Integration & Context Fidelity**

### Rationale

C08 is the keystone campaign. C04 proved the invocation boundary but the system cannot meaningfully delegate to local inference unless the runtime layer is correctly configured, identifiable, and provably delivering context to the model. The operator currently cannot answer "is the model getting the right context?" — and every operator truth surface built in C06 is undermined by that opacity.

C08 closes this gap by:
1. Making Whoosh'd runtime configuration operator-visible and inspectable.
2. Proving model inventory truth (what models are available, what's loaded).
3. Proving context injection path fidelity (identity, retrieval evidence, runtime posture reaches the model).
4. Exposing runtime truth surfaces in the operator workspace (model availability, provider status, context bundle integrity).
5. Keeping the local-only posture honest and inspectable.

After C08, C09 (execution authority) and C10 (result return) have a proven, inspectable substrate to depend on. Without C08, C09 would be building execution authority on an untestable foundation.

### Prerequisite Evidence

- **C06**: Operator workspace exists and can host runtime truth cards.
- **C04**: Provider-lane contract defines LOCAL lane separation — C08 can prove the LOCAL lane is correctly configured.
- **C05**: Redaction posture established — safe rendering of runtime/provider state is proven.
- **C03**: Work-order and command-run infrastructure exists for runtime configuration work orders.

### First Task by Name Only

**`C08-T001: Whoosh'd runtime configuration and model inventory seam audit`**

### Expected Proof Surface

- Current Whoosh'd runtime configuration seams audited.
- `/v1/models` and provider health endpoints classified.
- Context injection path identified (prompt assembly → model → response).
- Model inventory truth vs catalog truth gap quantified.
- Runtime configuration gaps (presets, startup, restart) classified.
- Operator visibility gaps in current workspace classified.
- Atomic task backlog for C08 defined.

### Release-Boundary Statement

- No live Pi/Coder execution.
- No live Pi SDK behavior.
- No Coder execution.
- No command bus execution.
- No worker enqueue.
- No receipt/artifact creation.
- No result return runtime.
- No release support widening.
- Local-only posture preserved.

## Deferred Candidates

| Candidate | Reason deferred |
|-----------|----------------|
| C07 Persona Studio | Valuable but lower leverage than C08. Operator-facing config surface can follow runtime substrate work. |
| C09 Pi/Coder Execution Authority | Too early. Needs C08 (trustworthy runtime) + C10 (receipt lineage) as substrate. Would be building on sand. |
| C10 Pi/Coder Result Return & Receipt Lineage | Needs C09. Receipt lineage without execution authority is speculative. |
| C11 Pi/Coder Sandbox Worker Proof | Needs C09. Worker proof before execution authority is premature. |

## Non-Claims

- No implementation started.
- No backend route added.
- No frontend behavior changed.
- No runtime behavior changed.
- No model training or deployment.
- No provider switching.
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
- **Wave 4 campaign selected**: C08: Whoosh'd Runtime Integration & Context Fidelity
- **Next step by name only**: `C08-T001: Whoosh'd runtime configuration and model inventory seam audit`
