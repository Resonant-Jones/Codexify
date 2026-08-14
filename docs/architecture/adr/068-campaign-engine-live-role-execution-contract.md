---
tags:
  - architecture
  - adr
  - campaign-engine
  - live-role-execution
  - guardian
  - pi-invocation
  - coding-loop
  - provider-capability
aliases:
  - ADR-068
  - Campaign Engine Live Role Execution Contract
---

# ADR-068: Campaign Engine Live Role Execution Contract

## Status

Accepted.

## Date

2026-08-14

## Acceptance

- Accepted: 2026-08-14
- Human approver: Resonant Jones (operator-owned merge gate on this change)

## Canonicalization History

This ADR is newly allocated ADR-068, the next valid number after ADR-066 in the current ADR Index and after the canonical Operator-Approved Derived Chroma Retirement decision that already owns ADR-067 on `main`. It supersedes no numeric identity. Historical Campaign Engine ADR numbers from abandoned or unpushed branches are not authoritative and must not be cited as this decision.

## Context

Accepted ADR-066 (Campaign Engine Runtime Recovery Contract, 2026-08-13) reconciles the Campaign Engine placement on `main`:

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

ADR-066 explicitly defers the first live Campaign Engine lifecycle: "The next authorized implementation slice is the provider-free Campaign Engine lifecycle ... This ADR does not implement that slice, does not resurrect the unpushed provider-free branch, and does not approve scheduling, delegation, overnight execution, auto-merge, or auto-push. Any implementation slice requires a separately approved task with its own proof surface."

The provider-free runtime slice (merged 2026-08-13 via PR #709) is now canonical on `main`. It proves:

- Campaign loading and validation;
- locked Auditor / Executor / Evaluator role bindings;
- bounded source-selection lineage;
- one runnable Task;
- synthetic Executor Attempt;
- synthetic Evaluation;
- evidence Receipt;
- final CampaignState;
- deterministic identities;
- zero provider calls;
- zero source mutations;
- zero decision gates.

Current accepted architecture still does not authorize the Campaign Engine to perform live provider-backed role execution. The Pi Invocation Boundary defines Guardian-mediated envelope, permission, receipt, result-validation, and lineage semantics but explicitly remains contract/validation only — no live Pi SDK/runtime invocation is established by that contract.

This ADR creates the smallest accepted architecture surface required for one subsequent live implementation slice. It does not implement live execution. The proof boundary is documented and explicitly bounded.

## Decision

ADR-068 authorizes exactly one bounded live Campaign Engine lifecycle:

```text
predefined Campaign + Task
        |
        v
bounded source-selection lineage
        |
        v
Guardian permission resolution
        |
        v
immutable invocation authorization
        |
        v
locked Executor
        |
        v
existing approved execution seam
        |
        v
Attempt + bounded execution evidence
        |
        v
locked Evaluator
        |
        v
read-only independent evaluation
        |
        v
Evaluation
        |
        v
Receipt + CampaignState
```

### 1. Authority ownership

**Campaign Engine owns:** Campaign lifecycle; Task lifecycle; role assignment; RoleBinding identity and revision; Attempt identity; Evaluation identity; acceptance criteria; source-selection lineage references; evidence linkage; final orchestration state; blocking when required evidence or identity proof is missing.

Campaign Engine does not self-authorize execution.

**Guardian owns:** permission resolution; live-execution authorization; target-repository policy; read/write scope; subprocess/command permission; network/provider permission; mutation permission; read-only Evaluator enforcement; policy denial; operator escalation; result validation and governed return.

Campaign Engine may request. Guardian grants or denies.

**Pi owns (where Pi is the selected harness):** bounded invocation transport; provider/model invocation mechanics; raw invocation metadata; bounded result return.

Pi does not own: Campaign state; role selection; acceptance criteria; retry policy; rebinding; approval; Receipt authority.

**Coding Loop owns (where the existing Coding Loop is the selected execution rail):** current governed coding execution mechanics; target/mutation scope enforcement already assigned to that substrate; validation/patch artifact production according to its accepted contract.

Campaign Engine must not implement a second coding execution stack.

**DLG / ARP owns:** source-selection lineage only.

An ARP does not authorize execution.

### 2. Execution-seam selection rule

Do not define "Pi" as synonymous with "Executor."

Campaign Engine roles bind to provider/model identity and an approved execution adapter or harness. The first proof's selected Executor/Evaluator path may use Pi where current implementation architecture supports it. However:

- Campaign Engine must compose with current Coding Loop/tool execution rails where repository mutation occurs;
- Pi may provide model/harness invocation mechanics;
- Guardian remains the authority boundary;
- no new competing execution loop may be created.

The five identities remain independently inspectable:

```text
role
!= provider
!= model
!= invocation harness
!= mutation rail
!= authority
```

### 3. Initial proof role posture

Authorize:

**Auditor** — provider-free/fixture-backed for the first live proof. No live model invocation. Consumes the already supplied campaign/source context. Performs no provider call.

**Executor** — one live invocation. One locked RoleBinding. Exact provider/model identity supplied by the binding. Bounded mutation only inside an explicitly approved isolated proof target. No Git commit, push, merge, PR, or deployment.

**Evaluator** — one live invocation. One locked RoleBinding. Exact provider/model identity supplied by the binding. Read-only. Evaluates Task acceptance criteria against bounded evidence. Does not repair or mutate. Does not trigger an automatic retry.

Do not make any specific DeepSeek model identifier a permanent architectural default. Previously used identifiers such as `deepseek/deepseek-v4-flash` or `deepseek/deepseek-v4-pro` may be used later as proof fixture bindings only if they still resolve from current operator configuration.

### 4. Live invocation authorization

Every live role invocation must be associated with an immutable authorization/envelope record containing or referencing at minimum:

- Campaign ID;
- Task ID;
- Run ID;
- role;
- RoleBinding ID;
- binding revision;
- provider ID;
- model ID;
- adapter/harness ID;
- configuration hash;
- source-context / ARP reference;
- target repository identity;
- allowed file paths;
- requested permissions;
- granted permissions;
- execution mode;
- operator consent or authorization reference;
- expected output contract/schema;
- invocation/correlation ID;
- prompt or request payload hash.

Once Guardian authorizes the invocation, material fields may not change. A changed material field requires a new authorization/invocation identity. The Campaign Engine schemas reference these authorization/envelope records by stable identity (string); they do not duplicate the nested payload. The Pi Invocation Boundary provides the canonical envelope/receipt identities (`PiInvocationEnvelope.invocation_id`, `PiInvocationPolicyDecision.policy_decision_id`, `PiInvocationReceipt.receipt_id`) that Campaign Engine references.

### 5. Permission resolution

Guardian must resolve explicitly before provider invocation:

- whether live role execution is allowed;
- whether provider/network access is allowed;
- whether the selected provider/model is allowed;
- whether the target repository is allowed;
- which paths may be read;
- which paths may be mutated;
- whether subprocess/local command execution is allowed;
- whether the role is mutation-capable or read-only;
- whether Git operations are forbidden;
- whether durable Codexify ingestion is forbidden.

Permission denial stops the lifecycle before provider invocation. No prompt text may substitute for enforcement.

### 6. RoleBinding invariants (preserved)

Exactly three canonical roles (Auditor, Executor, Evaluator). Each role has exactly one locked binding per binding revision. Maximum three distinct models per Campaign. Roles may share a model. No silent provider/model switching. No global default may override a locked role binding. Missing provider/model identity proof fails closed. Actual provider/model mismatch fails closed. No runtime rebinding is authorized. No automatic retry is authorized. Future retries must stay on the same binding unless separately authorized rebinding exists.

Live-mode RoleBinding additions:

- `live_role_binding` (object, conditional, required when `execution_mode` is `live`): `{ provider_identity_proof, target_repository_identity, allowed_file_paths, requested_permissions, granted_permissions, operator_consent_reference }`. These fields are absent (and the section absent) for provider-free fixtures. No credentials may appear inside these fields; identity proofs are references, not material.
- `redaction_status` (string, conditional, required when `execution_mode` is `live`): one of `redacted`, `unredacted`. Records whether the durable binding publication was redacted of any material the redactor deemed sensitive.

### 7. Executor boundary

The first live Executor may:

- operate only against an isolated disposable proof repository or temporary copy;
- modify only declared allowed files;
- perform one predefined bounded Task;
- run only Guardian-approved validation commands;
- return structured execution evidence.

The Executor may not: target the main Codexify worktree; alter Campaign Engine state directly; alter source-selection lineage; change RoleBindings; switch provider/model; invoke another role; widen allowed paths; redefine acceptance criteria; commit; push; merge; open a PR; deploy; write durable Codexify application state.

### 8. Evaluator boundary

The first live Evaluator receives only bounded evidence:

- original Task objective;
- acceptance criteria;
- source-context lineage reference where relevant;
- Executor Attempt;
- changed-file list;
- bounded diff/snapshot;
- validation command and output;
- exact Executor binding/actual identity;
- exact Evaluator binding identity.

The Evaluator must not receive hidden Executor scratch reasoning; permission to mutate files; repair authority; retry authority; provider-switch authority; architecture approval outside declared criteria.

Allowed verdicts remain the current bounded Evaluation domain:

- `passed`
- `passed_with_advisories`
- `repair_required`
- `blocked`

A `repair_required` or `blocked` verdict returns control to the operator. No repair loop is authorized.

### 9. Actual identity verification

For every live role invocation:

- expected provider/model identity comes from the locked RoleBinding;
- actual provider/model identity must be captured from the execution/harness receipt where supported;
- actual identity must match expected identity;
- missing identity evidence fails closed;
- mismatch fails closed;
- identity comparison result is recorded in Attempt/Evaluation evidence.

Do not infer successful identity from the requested model alone.

### 10. Provider capability posture

Live execution may proceed only when the required role capability is eligible under current provider capability governance. Align with ADR-062/provider capability doctrine:

- declared capability is not enough;
- current verified/effective capability must satisfy the Task requirements;
- capability evidence remains scoped to provider/model/target/schema identity;
- no proof for one target generalizes automatically to another.

### 11. Attempt contract (extended)

The strict `campaign-engine/v0` Attempt schema gains conditional live-mode fields. Provider-free Attempts remain schema-valid unchanged.

Live-mode required fields when `execution_mode` is `live`:

- `execution_mode` (string enum): `provider_free` | `live` | `provider_free_synthetic` — defaults to `provider_free` if absent.
- `invocation_authorization_reference` (string): identity of the Guardian authorization record (typically `PiInvocationPolicyDecision.policy_decision_id`).
- `permission_resolution_reference` (string): identity of the permission-resolution record.
- `expected_provider_id` (string).
- `expected_model_id` (string).
- `actual_provider_id` (string).
- `actual_model_id` (string).
- `identity_verification_result` (string enum): `match` | `mismatch` | `identity_unavailable` | `identity_forged` — `mismatch`, `identity_unavailable`, and `identity_forged` are fail-closed.
- `provider_harness_receipt_reference` (string): identity of the Pi (or other harness) receipt.
- `provider_call_count` (integer, ≥1).
- `target_proof_identifier` (string): the disposable proof-target identifier.
- `changed_files` (array of objects, present iff mutation occurred): each entry `{ path, hash, content_hash_algorithm }`.
- `validation_command_reference` (string, optional).
- `validation_result_hash` (string, optional).
- `exit_classification` (string enum): `succeeded` | `failed_validation` | `failed_transport` | `failed_permission_denied` | `cancelled`.
- `source_mutation_count` (integer, ≥0).
- `secret_redaction_status` (string enum): `redacted` | `not_applicable`.
- `commit_performed` (boolean, must be `false`).
- `merge_performed` (boolean, must be `false`).
- `durable_ingestion_performed` (boolean, must be `false`).

Conditional invariants must keep provider-free Attempts schema-valid: any live-mode Attempt with `commit_performed` / `merge_performed` / `durable_ingestion_performed` equal to `true` is rejected at validation time.

### 12. Evaluation contract (extended)

The strict `campaign-engine/v0` Evaluation schema gains conditional live-mode fields. Provider-free Evaluations remain schema-valid unchanged.

Live-mode required fields when `evaluation_mode` is `live`:

- `evaluation_mode` (string enum): `provider_free` | `live` — defaults to `provider_free` if absent.
- `invocation_authorization_reference` (string).
- `permission_resolution_reference` (string).
- `expected_provider_id` (string).
- `expected_model_id` (string).
- `actual_provider_id` (string).
- `actual_model_id` (string).
- `identity_verification_result` (string enum): `match` | `mismatch` | `identity_unavailable` | `identity_forged`.
- `provider_harness_receipt_reference` (string).
- `structured_acceptance_results` (array of objects): each entry `{ criterion_id, verdict, evidence_refs, basis }` with `verdict` in `{pass, fail, advisory}`.
- `read_only_assertion` (boolean, must be `true`).
- `mutation_performed` (boolean, must be `false`).
- `independent_model_judgment` (boolean, must be `true` for live evaluations; provider-free evaluations continue to record `independent_model_judgment: false`).
- `secret_redaction_status` (string enum): `redacted` | `not_applicable`.

Provider-free Evaluation continues to require `independent_model_judgment: false` (it does not make an independent-model-judgment claim). Live Evaluation requires `independent_model_judgment: true`. A live Evaluation with `mutation_performed: true` is rejected.

### 13. Receipt contract (extended)

The strict `campaign-engine/v0` Receipt schema gains conditional live-mode fields. Provider-free Receipts remain schema-valid unchanged.

Live-mode required fields when the Receipt subject is a live execution:

- `executor_role_binding_id` (string).
- `expected_executor_provider_id` (string).
- `expected_executor_model_id` (string).
- `actual_executor_provider_id` (string).
- `actual_executor_model_id` (string).
- `executor_invocation_receipt_reference` (string).
- `evaluator_role_binding_id` (string).
- `expected_evaluator_provider_id` (string).
- `expected_evaluator_model_id` (string).
- `actual_evaluator_provider_id` (string).
- `actual_evaluator_model_id` (string).
- `evaluator_invocation_receipt_reference` (string).
- `source_context_reference` (string, the Agent Reading Packet identity or equivalent bounded receipt).
- `source_context_hash` (string, lowercase 64-char SHA-256 hex digest).
- `executor_identity_verification_result` (string enum).
- `evaluator_identity_verification_result` (string enum).
- `redaction_result` (string enum): `redacted` | `not_applicable`.
- `commit_performed` (boolean, must be `false`).
- `merge_performed` (boolean, must be `false`).
- `durable_ingestion_performed` (boolean, must be `false`).
- `rebinding_performed` (boolean, must be `false`).
- `provider_call_count` (integer, ≥1).
- `source_mutation_count` (integer, ≥0).
- `final_verdict` (string enum): `passed` | `passed_with_advisories` | `repair_required` | `blocked`.
- `proof_target_identifier` (string).

Receipt remains evidence, not authority or approval.

### 14. Schema-version policy decision

Decision: extend the existing `campaign-engine/v0` schemas as backward-compatible conditional branches; do not introduce a `v1`. Reasoning:

- All current schemas are `additionalProperties:false` with strict required sets; new live-mode fields are added under new keys (`execution_mode`, `live_role_binding`, `invocation_authorization_reference`, etc.) that existing fixtures never set.
- Every new field is either optional (the provider-free path does not set it) or required only when the matching `execution_mode`/`evaluation_mode` discriminator is `live`.
- Existing provider-free fixtures (`valid_campaign.json`, `provider_free_runtime_campaign.json`, the provider-free Attempt/Evaluation/Receipt in the merged runtime) remain schema-valid and continue to pass `test_campaign_engine_schemas.py` unchanged.
- A `v1` introduction would force a partially-upgraded mixed-version state during the transition window, exactly what the packet forbids.
- The schemas remain a single source of truth with conditional live-mode branches rather than two parallel schema sets.

### 15. Failure behavior (live mode fail-closed)

The live lifecycle must fail closed on:

- Guardian permission denial;
- missing operator/live-execution consent where required;
- unresolved RoleBinding;
- unresolved provider/model;
- provider capability ineligibility;
- missing actual identity evidence;
- actual provider/model mismatch;
- target-path escape;
- mutation outside allowed paths;
- malformed provider result;
- invalid structured evaluation;
- unauthorized Evaluator mutation;
- validation failure where acceptance requires passing validation;
- secret leakage into durable proof artifacts;
- harness transport failure;
- invalid receipt/result provenance.

No automatic fallback occurs. No automatic repair occurs. No automatic retry occurs.

### 16. Proof boundary

The first future implementation authorized by this ADR supports exactly:

- one Campaign;
- one Task;
- one provider-free Auditor;
- one live Executor invocation;
- one live Evaluator invocation;
- one isolated proof target;
- bounded source mutation;
- bounded validation;
- one Evaluation verdict;
- one final Receipt;
- one final CampaignState.

This proof does not establish: production readiness; release support; autonomous planning; multi-task scheduling; background execution; retry loops; repair loops; rebinding; generalized provider support; arbitrary repository targeting; auto-commit; auto-push; auto-merge; deployment; database persistence; UI/API/worker/queue support.

### 17. Security and privacy

- No secrets in Campaign, Task, prompts, receipts, proof artifacts, fixtures, or commits.
- Credentials remain in existing provider/Pi auth stores.
- Raw model/harness results are sanitized before durable evidence publication.
- Environment variables and token-like values are redacted.
- Repository context is minimized to bounded Task needs.
- Evaluator receives only required evidence.
- Provider responses are untrusted until validated.
- Provider/model identity evidence is preserved without credential material.
- The new `live_role_binding` section and the new live-mode Attempt/Evaluation/Receipt fields carry only **identity references** (string ids of other records), not credential material. The schema validator rejects any field whose value pattern matches a credential shape; this is a fail-closed security invariant enforced at validation time.

## Authority and truth boundary

- `docs/architecture/00-current-state.md` retains short-horizon release-truth authority; this ADR does not modify it.
- ADR-066 retains Campaign Engine placement authority; this ADR (ADR-068) adds the live-role-execution overlay inside that placement.
- DLG metadata and ARPs remain evidence for source selection, not executable instructions and not authority grants.
- Guardian remains the authority/policy boundary for any live execution.
- Current code, focused tests, and live proof retain implementation-evidence roles.
- Human review remains required for any live Campaign Engine implementation, release claim, and rebinding.

## Relationship map

| Surface | Role in the live-role-execution placement | What it is not |
|---|---|---|
| Campaign Engine (ADR-066, ADR-068) | Campaign/task/role orchestration; bounded live-role invocation request | Self-authorizing execution; release proof |
| Guardian (ADR-020, ADR-048) | Permission resolution; live-execution authorization; result validation and return | The execution harness |
| Pi Invocation Boundary + ADR-063 | Bounded harness invocation transport; envelope, receipt, result-return identities | Autonomous dispatch; durable control-plane truth |
| Coding Loop substrate | Governed coding-execution rail when mutation is required | Auto-merge; auto-push; release approval |
| Agent Tool Loop / command bus | Bounded one-tool-turn execution lane (when applicable) | General autonomous agent runtime |
| Provider Tool-Turn / ADR-062 | Provider-neutral transport and capability seams | Provider-owned orchestration state |
| ADR-028 Execution Ledger / ADR-050 | Durable campaign-runner evidence and GitHub-native dry-run surfaces | Campaign Engine orchestration authority |
| DLG / ARP | Source-selection lineage only | Execution authority, approval, second truth store |

## Non-Goals

This ADR does not:

- implement Campaign Engine runtime code (the provider-free slice remains the only implementation);
- modify Pi runtime implementation;
- modify Coding Loop runtime;
- modify Guardian runtime;
- modify the command bus, provider adapters, database models, migrations, API routes, or UI;
- approve scheduling, delegation, overnight execution, auto-merge, or auto-push;
- create a new DLG node record or regenerate DLG projections (the current phase rules and pinned Phase 3A/3B calibration do not require registration of this ADR; the node corpus remains fixed at its reviewed nine-node baseline);
- widen the supported beta release promise;
- authorize any specific DeepSeek model as a permanent default;
- create a new competing execution loop.

## Invariants

- DLG/ARP grants no execution authority to Campaign Engine.
- Campaign Engine never bypasses Guardian authority or policy.
- Campaign Engine composes with Pi, Coding Loop, and tool-capability seams instead of duplicating them.
- The five execution identities (role, provider, model, harness, mutation rail, authority) remain independently inspectable.
- Auditor / Executor / Evaluator bindings remain locked per campaign with lineage-recorded rebinding only.
- Every execution and evaluation step produces a Receipt.
- Provider-free fixtures and the provider-free runtime remain schema-valid and test-green.
- Live-mode schemas carry identity references, not credential material.
- Live-mode Receipts must record commit/merge/durable-ingestion/rebinding all `false`.
- Live-mode Evaluator evaluations must record `mutation_performed: false` and `independent_model_judgment: true`.
- Live-mode Attempt identity verification must be `match`; any other value is fail-closed.
- No beta/release claim is made until live runtime proof exists.

## Consequences

- Future live Campaign Engine work has a decided authority and contract surface and does not need to reconstruct execution-seam ownership implicitly.
- The provider-free slice remains the only Campaign Engine implementation on `main`; this ADR adds the next authorized implementation slice's contract, not the slice itself.
- Guardian, Pi, Coding Loop, Provider Capability, and DLG/ARP boundaries stay in their existing ownership.
- Live-mode schema additions are conditional branches, not a breaking change to provider-free schemas.
- Release claims remain unchanged until live runtime proof exists.

## Documentation Follow-through

This change:

- registers ADR-068 in `docs/architecture/adr/adr-index.md` (Reading Order and ADR Graph);
- aligns `docs/architecture/campaign-engine-contract.md` with ADR-068 (provider-free vs authorized-live distinction);
- aligns `docs/architecture/pi-invocation-boundary-contract.md` with ADR-068 (explicit permission to use Pi as a Campaign Engine live-execution harness under Guardian-mediated authorization);
- extends the four affected Campaign Engine schemas (RoleBinding, Attempt, Evaluation, Receipt) with backward-compatible conditional live-mode branches;
- extends `codex_runner/tests/test_campaign_engine_schemas.py` with the 33 acceptance proofs enumerated in the task brief;
- syncs the adr-index DLG node record `content_hash` to the updated index bytes, following the established ADR-add convention.

Deferred (separately approved tasks with their own proof surface):

- implementation of Guardian permission resolution for Campaign Engine;
- the first isolated live Executor proof;
- the first live Evaluator proof;
- live Auditor;
- live Coding Loop integration;
- operator runbook;
- retry/repair/rebinding policy (none authorized by this ADR);
- multi-task scheduling, queue, worker, API, UI;
- database persistence;
- release-truth update after live proof;
- README entry for ADR-068 (deferred to a follow-up task).

## Acceptance record

Resonant Jones accepts ADR-068 on 2026-08-14 through the operator-owned merge gate on this change. Acceptance approves the live-role-execution contract overlay; provider-free runtime presence, schema additions, validation coverage, or this accepted ADR still does not constitute live execution, release support, or runtime proof.

## Related Documents

- `docs/architecture/00-current-state.md`
- `docs/architecture/campaign-engine-contract.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/guardian-build-loop-doctrine.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/architecture/provider-tool-turn-boundary-contract.md`
- `docs/architecture/provider-capability-contract.md`
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
- `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`
- `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md`
- `docs/architecture/adr/ADR-048-guardian-three-channel-delegation-topology.md`
- `docs/architecture/adr/050-event-driven-campaign-control-plane.md`
- `docs/architecture/adr/062-provider-capability-model-contract.md`
- `docs/architecture/adr/066-campaign-engine-runtime-recovery-contract.md`
- `docs/architecture/adr/proposed/063-pi-loop-manager-campaign-runner-gate-graph.md`
- `codex_runner/schemas/campaign_engine/`
- `codex_runner/tests/test_campaign_engine_schemas.py`
- `guardian/pi/` — canonical Pi envelope, policy decision, receipt, and harness-result identities referenced by Campaign Engine schemas.
