---
tags:
  - architecture
  - adr
  - campaign-engine
  - dlg
  - agent-reading-packet
  - guardian
  - pi-loop
  - coding-loop
aliases:
  - ADR-066
  - Campaign Engine Runtime Recovery Contract
---

# ADR-066: Campaign Engine Runtime Recovery Contract

## Status

Accepted.

## Date

2026-08-13

## Acceptance

- Accepted: 2026-08-13
- Human approver: Resonant Jones (operator-owned merge gate on this change)

## Canonicalization History

This ADR is newly allocated ADR-066, the next valid number after ADR-065 in the current ADR Index. It supersedes no numeric identity. Historical Campaign Engine ADR numbers from abandoned or unpushed branches are not authoritative and must not be cited as this decision.

## Context

Campaign Engine was introduced on `main` as a contract-plus-schema surface only:

- `docs/architecture/campaign-engine-contract.md` (v0) defines the orchestration authority for planning, executing, evaluating, and closing bounded development campaigns, with Auditor / Executor / Evaluator role bindings locked per campaign.
- Versioned core schemas under `codex_runner/schemas/campaign_engine/` (`campaign-engine/v0`) define Campaign, Task, Attempt, Evaluation, Receipt, Decision Gate, Campaign State, and Role Binding records with cross-object validation coverage in `codex_runner/tests/test_campaign_engine_schemas.py`.
- A later provider-free runtime implementation existed on an unpushed branch and never became current repository truth. This decision neither cherry-picks nor recreates that implementation; it reconciles the surviving contract so future runtime work is rebuilt against the correct truth surface.

Since Campaign Engine was first designed, the repository architecture has advanced materially:

- The Document Lifecycle Graph (DLG) is now an accepted repository-native source-authority and document-resolution control plane under ADR-056, with its normative contract at `docs/architecture/document-lifecycle-graph-contract.md`. DLG metadata does not grant execution permission or runtime authority.
- The Agent Reading Packet (ARP) is the canonical future bounded source-selection receipt: it records what was selected, resolved, excluded, stale, contradictory, unavailable, or human-dependent for one question or task, and grants no execution permission, architecture approval, or truth guarantee.
- Pi Loop Manager governance has been canonicalized in current ADR history as ADR-063 (Proposed, `docs/architecture/adr/proposed/063-pi-loop-manager-campaign-runner-gate-graph.md`): Pi Loop Manager receipts are bounded attempt evidence, never durable control-plane truth.
- Guardian remains the authority and policy boundary: request policy, transcript lineage, provenance, command authority, and result return (ADR-020, ADR-048, Guardian Build Loop Doctrine, Pi Invocation Boundary Contract).
- Coding Loop and bounded tool-capability work now provide existing execution seams that future Campaign Engine work must compose with rather than duplicate: the coding-worker execution substrate (`/api/agents/coding/execute`, `CodingWorker`, adapter registry, mutation scope guard, validation, patch artifacts, opt-in commit-after-green), the Agent Tool Loop Contract (one bounded tool turn through the command bus), the Provider Tool-Turn Boundary Contract (canonical `ModelTurn` semantics), and the Provider Capability Contract / ADR-062 (declared vs verified vs effective capability).
- Current release truth (`docs/architecture/00-current-state.md`) explicitly states that Campaign Engine schemas do not establish scheduling, delegation, overnight execution, auto-merge, or auto-push.

The first recovery step is therefore not runtime implementation. It is to record an accepted decision that reconciles the surviving Campaign Engine contract with the current architecture so the provider-free runtime can be rebuilt against the correct truth surface. Reconstructing this placement implicitly later would be dangerous, so it requires an accepted ADR.

## Decision

The current Campaign Engine placement is:

```text
DLG / Agent Reading Packet
        |
        | source-selection lineage only
        v
Campaign Engine
        |
        | campaign/task/role orchestration
        v
Guardian authority and policy
        |
        | authorized bounded execution
        v
Pi / Coding Loop / Tool Capability seams
        |
        | execution evidence
        v
Attempt -> Evaluation -> Receipt
```

### 1. DLG/ARP lineage only, never execution authority

Campaign Engine consumes DLG/ARP lineage as its source-selection receipt for campaign planning and task source selection. A campaign run records which sources were selected, resolved, excluded, stale, or contradictory (source-selection lineage) using the ARP contract or an equivalent bounded receipt. DLG document identity, graph metadata, and ARPs grant no execution permission, no runtime authority, and no approval. The DLG remains a docs/control-plane surface; `00-current-state.md` remains release truth; Campaign Engine does not grant the DLG a second truth role.

### 2. Campaign Engine owns campaign/task/role orchestration only

Campaign Engine owns campaign state, task sequencing, execution attempts, evaluation results, retry and escalation decisions, and campaign closure — the orchestration layer. It does not own provider execution, policy authority, or source authority. Providers remain execution substrates and do not own orchestration state or decisions.

### 3. Guardian remains the authority and policy boundary

All execution flows through Guardian authority and policy: request policy, lineage, command authority, and result return. Campaign Engine may propose; Guardian grants. No Campaign Engine runtime slice may bypass Guardian, the command bus for Codexify-owned actions, transcript ownership, provenance, or export/restore obligations.

### 4. Composition with existing execution seams, not duplication

Future Campaign Engine runtime work composes with, and must not duplicate:

- the Guardian Build Loop as the canonical end-to-end governed build/change pipeline;
- the Pi Invocation Boundary Contract and ADR-063 Pi Loop Manager as the bounded harness-invocation and attempt-evidence seams;
- the Coding Loop execution substrate (route, worker, adapter registry, mutation guard, validation, patch artifacts, commit-after-green) as the governed coding-execution rail;
- the Agent Tool Loop Contract and command bus as the bounded one-tool-turn execution lane;
- the Provider Tool-Turn Boundary Contract and Provider Capability Contract / ADR-062 as the provider-neutral transport and capability seams;
- ADR-028 Execution Ledger and ADR-050 Event-Driven Campaign Control Plane as the durable campaign-runner evidence and GitHub-native dry-run control-plane surfaces.

No new competing "loop" name is introduced. Execution backends are adapters or harnesses under Guardian; receipts are evidence, not truth.

### 5. Campaign / Task / Attempt / Evaluation / Receipt semantics are preserved

The canonical entity semantics from `campaign-engine-contract.md` v0 and the `campaign-engine/v0` schemas — Campaign, Task, Attempt, Evaluation, Receipt, Decision Gate, Campaign State, Role Binding — remain the schema-locked vocabulary. This ADR changes no schema and no semantic. Future runtime work must produce and consume these records as defined.

### 6. Locked Auditor / Executor / Evaluator role bindings are preserved

The role model is unchanged: exactly three roles (Auditor, Executor, Evaluator); each role binds to exactly one model at runtime; a maximum of three distinct models per campaign; roles may share a model; bindings are locked for the duration of a campaign; rebinding requires explicit operator approval and creates a new binding revision with recorded lineage. No silent provider or model switching during retries. Attempts inherit the role's locked binding.

### 7. The provider-free lifecycle is the next authorized implementation slice

The next authorized implementation slice is the provider-free Campaign Engine lifecycle: campaign/task/attempt/evaluation/receipt mechanics, decision gates, and locked role bindings without provider-coupled orchestration, built against this ADR's truth surface. This ADR does not implement that slice, does not resurrect the unpushed provider-free branch, and does not approve scheduling, delegation, overnight execution, auto-merge, or auto-push. Any implementation slice requires a separately approved task with its own proof surface.

### 8. Release boundary

Campaign Engine remains outside current beta/release claims until runtime proof exists. The presence of the contract, schemas, validation coverage, or this accepted ADR does not establish scheduling, delegation, overnight execution, auto-merge, auto-push, runtime support, or release readiness.

## Authority and truth boundary

- `docs/architecture/00-current-state.md` retains short-horizon release-truth authority; this ADR does not modify it.
- This accepted ADR has decision authority inside its declared scope: the placement and recovery posture of Campaign Engine.
- DLG metadata and ARPs are evidence for source selection, not executable instructions and not authority grants.
- Guardian remains the authority/policy boundary for any execution.
- Current code, focused tests, and live proof retain implementation-evidence roles.
- Human review remains required for future Campaign Engine runtime acceptance, schema changes, and release claims.

## Relationship map

| Surface | Role in the Campaign Engine placement | What it is not |
|---|---|---|
| DLG / ADR-056 / ARP | Source-selection lineage and document-resolution receipt for campaign runs | Execution authority, approval, or a second truth store |
| Campaign Engine contract + schemas | Orchestration vocabulary (Campaign/Task/Attempt/Evaluation/Receipt/Gate/State/Binding) | Runtime implementation or release proof |
| Guardian (ADR-020, ADR-048) | Authority, policy, lineage, command authority, result return | The execution harness |
| Guardian Build Loop Doctrine | Canonical end-to-end governed build/change pipeline umbrella | A second competing loop |
| Pi Invocation Boundary + ADR-063 Pi Loop Manager | Bounded harness invocation and attempt-evidence seams | Autonomous dispatch or durable control-plane truth |
| Coding Loop substrate | Governed coding-execution rail (route, worker, adapter, validation, artifacts) | Auto-merge, auto-push, or release approval |
| Agent Tool Loop / command bus | Bounded one-tool-turn execution lane | General autonomous agent runtime |
| Provider Tool-Turn Boundary / ADR-062 | Provider-neutral transport and capability seams | Provider-owned orchestration state or decisions |
| ADR-028 Execution Ledger / ADR-050 control plane | Durable campaign-runner evidence and GitHub-native dry-run surfaces | Campaign Engine orchestration authority |

## Non-Goals

This ADR does not:

- implement Campaign Engine runtime code;
- modify Campaign Engine schemas or their validation coverage;
- modify Pi implementation code, Guardian runtime code, Coding Loop runtime code, tool execution code, or provider adapters;
- modify database schemas, API routes, or UI;
- cherry-pick, recreate, or resurrect the unpushed provider-free runtime branch;
- approve scheduling, delegation, overnight execution, auto-merge, or auto-push;
- create a new DLG node record or regenerate DLG projections (the current phase rules and pinned Phase 3A/3B calibration do not require registration of this ADR; the node corpus remains fixed at its reviewed nine-node baseline);
- widen the supported beta release promise.

## Invariants

- DLG/ARP grants no execution authority to Campaign Engine.
- Campaign Engine never bypasses Guardian authority or policy.
- Campaign Engine composes with Pi, Coding Loop, and tool-capability seams instead of duplicating them.
- Campaign / Task / Attempt / Evaluation / Receipt semantics remain schema-locked.
- Auditor / Executor / Evaluator bindings remain locked per campaign with lineage-recorded rebinding only.
- Every execution and evaluation step produces a Receipt.
- Campaign runs record source-selection lineage (ARP or equivalent bounded receipt).
- Tasks remain atomic; the repository must be clean before execution; allowed file scopes must be enforced.
- Human authority is required for irreversible or architectural decisions.
- No beta/release claim is made until runtime proof exists.

## Consequences

- Future Campaign Engine runtime work has a decided truth surface and does not need to reconstruct authority placement implicitly.
- The provider-free lifecycle has an authorized starting point without granting it implementation approval.
- DLG/ARP, Guardian, Pi, Coding Loop, and tool-capability boundaries stay in their existing ownership.
- The unpushed provider-free branch remains non-canonical history; any future slice rebuilds from this ADR's surface.
- Release claims remain unchanged until runtime proof exists.

## Documentation Follow-through

This change:

- registers ADR-066 in `docs/architecture/adr/adr-index.md` (Reading Order and ADR Graph);
- aligns `docs/architecture/campaign-engine-contract.md` with this decision;
- syncs the adr-index DLG node record `content_hash` to the updated index bytes, following the established ADR-add convention.

Deferred:

- a `docs/architecture/README.md` entry for ADR-066 (README is not authorized in this change; a follow-up task should add it);
- DLG node registration and projection regeneration for this ADR (not required by current phase rules; the Phase 3A/3B calibration remains frozen at the reviewed nine-node baseline);
- any update to `00-current-state.md` (not required: this ADR changes no release posture);
- the provider-free runtime implementation slice (separately approved task, per Decision section 7).

## Acceptance record

Resonant Jones accepts ADR-066 on 2026-08-13 through the operator-owned merge gate on this change. Acceptance approves the Campaign Engine placement and recovery posture; contract and schema presence, validation coverage, or this accepted ADR still does not constitute runtime, release, or implementation proof.

## Related Documents

- `docs/architecture/00-current-state.md`
- `docs/architecture/campaign-engine-contract.md`
- `docs/architecture/document-lifecycle-graph-contract.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/guardian-build-loop-doctrine.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/architecture/provider-tool-turn-boundary-contract.md`
- `docs/architecture/provider-capability-contract.md`
- `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md`
- `docs/architecture/adr/062-provider-capability-model-contract.md`
- `docs/architecture/adr/proposed/063-pi-loop-manager-campaign-runner-gate-graph.md`
- `docs/architecture/adr/ADR-048-guardian-three-channel-delegation-topology.md`
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
- `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`
- `docs/architecture/adr/050-event-driven-campaign-control-plane.md`
- `codex_runner/schemas/campaign_engine/`
- `codex_runner/tests/test_campaign_engine_schemas.py`
