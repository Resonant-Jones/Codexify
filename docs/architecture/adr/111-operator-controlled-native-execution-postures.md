---
tags:
  - architecture
  - adr
  - guardian
  - execution-authority
  - operator
  - native-execution
  - sandbox
aliases:
  - ADR-111
  - Operator-Controlled Native Execution Postures
---

# ADR-111: Operator-Controlled Native Execution Postures

## Status

Proposed.

## Date

2026-11-06

## Acceptance

- Proposed: 2026-11-06
- Human approver: pending — Resonant Jones
- Evidence posture: documented architecture contract. Acceptance of this record would record the governing authority and configuration model only. It does not implement an executor, enable any runtime exception, or widen any release claim.

## Governing context

This decision is subordinate to, and must be read together with:

- [ADR-020: Guardian Mediated Coding Agent Execution Contract](./020-guardian-mediated-coding-agent-execution-contract.md) — Accepted;
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md) — **Proposed** (2026-06-30); recorded here because it is the access-topology statement for self-operated instances, but it is not relied upon as an accepted authority;
- [ADR-048: Guardian Three-Channel Delegation Topology](./ADR-048-guardian-three-channel-delegation-topology.md) — Accepted;
- [ADR-077: Sandbox Execution Authority and Provider Boundary](./077-sandbox-execution-authority-and-provider-boundary.md) — Accepted. **This record proposes a narrow, explicitly unaccepted exception to ADR-077 and does not modify it.** See "Relationship to ADR-077";
- [ADR-078: Modal as the Initial Hosted Sandbox Provider](./078-modal-initial-hosted-sandbox-provider.md) — Accepted;
- [ADR-092: Credential Purpose and Mixed-Principal Authentication Boundary](./092-credential-purpose-and-mixed-principal-authentication-boundary.md) — Accepted. Governs credential-class separation;
- [ADR-093: Native Execution Channel and Inference Routing Contract](./093-native-execution-channel-and-inference-routing-contract.md) — Accepted. Governs the execution-channel catalog and keeps Guardian as the routing and authorization authority;
- [ADR-094: Account-Scoped Execution Credential Authority](./094-account-scoped-execution-credential-authority.md) — Accepted;
- [ADR-095: Configuration Inspector Operator Control-Plane Boundary](./095-configuration-inspector-operator-control-plane-boundary.md) — Accepted. **The Configuration Inspector remains read-only under this decision.**;
- [ADR-105: Operator Actor Identity and Human Approval Provenance](./105-operator-actor-identity-and-human-approval-provenance.md) — Accepted. Governs operator lane separation and human approval provenance;
- [ADR-108: Codexify Music Producer Authority and Agent-DAW Service Boundary](./108-codexify-music-producer-authority-and-agentdaw-service-boundary.md) — Proposed. See "Relationship to ADR-108";
- ADR-109: Sandbox Execution Contract and Kernel-Enforced Storage Posture — **Pending, not on `main`.** Currently proposed by the open sandbox/voice work (PR #1006). This record does not depend on it and does not preempt it.

Numbering: 111 rather than 109 or 110, because ADR-109 and ADR-110 are allocated by the open sandbox/voice branch. This follows the index convention established by ADR-106 and ADR-107, which record their own numbering decisions.

## Context

The End Operator's requirement is a product authority requirement, not a request for unsafe defaults and not a request for implicit model authority:

> If somebody installs Codexify on their own machine, they should be able to configure it to run commands autonomously, including destructive commands, without approving every operation. They should also be able to choose whether those commands run in an isolated sandbox or directly in an authorized execution environment. Those choices should persist across sessions and restarts.

Codexify is a Life Harness: a fully integrated system that goes with its user everywhere, which is why self-hosting capability is treated as a first-class requirement rather than an escape hatch. Connecting to the Resonant Constructs Network is a convenience, not a continuity requirement. By the same logic, an operator's own authority over their own instance must not require them to fight the product for it.

**What already exists, and is real:**

| Existing capability | Location | State |
| --- | --- | --- |
| Centralized tool policy with `enforce` / `warn` / `off` modes | `guardian/tools/policy.py:73`, `:156` | Implemented |
| Command-bus permission profiles with independent `shell_allowed`, `shell_read_only`, `allowed_shell_commands`, `filesystem_access`, `allowed_write_roots`, `network_allowed` axes | `guardian/command_bus/permission_profiles.py` | Implemented |
| Distinction between genuinely enforced boundaries and advisory configuration | `guardian/core/guardian_permission_posture.py` | Implemented; explicitly enumerates which surfaces are enforced and which are advisory |
| Provider-neutral sandbox request/result contract and posture semantics | `guardian/sandbox/contracts.py`, `guardian/sandbox/policy.py` | In flight under ADR-109 (PR #1006); hosted provider conformance already proven under ADR-078 |
| Operator control plane with a dedicated authentication dependency | ADR-095, `guardian.core.dependencies.require_operator_auth` | Accepted |
| Credential-class separation and human approval provenance | ADR-092, ADR-105 | Accepted |

**What does not exist:** one unified, persistent, operator-controlled native execution policy that governs unrestricted shell execution, persistent automatic authorization, and executor selection together. Today the axes above are evaluated independently and none of them is a durable operator-level posture that survives restart.

**Two facts that must not be conflated.** First, `CODEXIFY_POLICY_MODE=off` is *not* an unrestricted-execution grant. It bypasses one layer — `evaluate_tool_policy` / `apply_policy_mode` — while permission-profile evaluation (`guardian/command_bus/invoke.py:395-411`), external transport policy (`:412-431`), the phase-1 write gate (`:558-570`), and a second policy evaluation inside the loopback adapter (`guardian/command_bus/loopback_http_adapter.py:97-136`) all still run. **There is consequently no code path today that grants unrestricted execution even to an operator who wants it.** That absence is the gap this record addresses, and it is why "persistent automatic authorization" in this decision requires a real mechanism rather than a mode flip.

Second, the current runtime has no operating-system isolation boundary in the coding path. `guardian/core/guardian_permission_posture.py` states this plainly: there is no sandbox provider wired into the coding worker, and the adapter runs a subprocess in the worker context with no OS-level isolation. That is the honest present truth and it must not be reported otherwise.

## Constitutional answers

Five authorities are kept **distinct**. Collapsing any two of them is a defect in an implementation of this record.

1. **Operator authentication** — *who is presenting.* Governed by ADR-092 and ADR-095. A deployment API key, an `operator_session`, and a canonical account-admin principal are different authority classes. Under ADR-105, raw API-key and `operator_session` credentials keep the operator-control lane and never produce, imply, or record a human approver identity.
2. **Account authorization** — *what this account may do.* Governed by the account's own grants and the canonical `User` role.
3. **Configuration ownership** — *who may change this instance's posture, and where that truth is stored.* Owned by the operator control plane under ADR-095. The Configuration Inspector remains read-only and gains no write authority here.
4. **Execution permissions** — *what a given execution attempt may do.* Granted per attempt, never inherited from model-authored input.
5. **Physical isolation** — *where the process actually runs.* An execution-environment property, and the one axis that can only be truthfully asserted by the executor that realizes it.

These are deliberately not one "Safe Mode" switch. A single bundled toggle would make it impossible to configure, for example, unrestricted shell with no approval prompts while retaining container isolation — and it would make the operator's actual posture illegible.

## Decision

### 1. Canonical authority ladder

Five distinct authorities, resolved in order, each strictly bounded by the one above it:

```
Instance / Host Operator
  └─ Authenticated Account
       └─ Project
            └─ Agent / Persona
                 └─ Individual Execution Attempt
```

- Only a **verified operator** may configure host-level execution exposure or remove instance-level safeguards.
- A normal user, a model, an imported configuration file, a project document, a generated tool, or an agent-authored artifact **cannot self-authorize operator privileges**.
- **Self Operator** — the single person operating their own instance — is a first-class, explicitly defined case. A self-operator satisfies the operator-authority requirement through local instance ownership rather than through a remote operator session. It is not a weakened variant of the operator case; it is a different, equally legitimate, way to be one.
- Authority resolution is **monotonic downward**. A lower layer can narrow but never widen the grant above it.

### 2. Approval configuration

- Preserves the existing `CODEXIFY_POLICY_MODE` vocabulary: `enforce`, `warn`, `off`. These modes are reconciled, not replaced by parallel semantics.
- Adds **persistent automatic authorization**: a durable operator-configured posture under which recurring approval is not required for a bounded class of execution. No time-limited or per-session consent is mandatory for an operator-configured persistent policy.
- **Tool approval remains distinct from ownership, authentication, credential authorization, and other independent gates.** A command may be pre-approved while the attempt is still refused for lack of credential authority, and vice versa.
- **ADR-105 is not generalized.** The Campaign Continuation Authority human-approval requirements recorded in ADR-105 govern that surface. They are not read as a universal per-command approval requirement, and this decision does not impose them on native execution. Conversely, nothing here weakens ADR-105 for the surface it governs.

### 3. Tool authority

Independently configurable:

- **Catalog-only** — the model may select only entries from an operator-configured command catalog.
- **Allowlisted shell** — the model may construct commands from an operator-configured allowlist of executables, arguments, and paths.
- **Unrestricted shell** — the model may construct arbitrary commands, bounded only by the selected executor's actual authority.

An unrestricted shell grant authorizes arbitrary commands **within the selected executor's real authority**. It does not authorize anything the executor cannot actually do, and it does not grant filesystem or network authority beyond what the executor enforces.

> **Read-only labels are not isolation.** A tool labelled read-only is not an OS-enforced read-only filesystem, and no capability may be reported as isolated, read-only, network-denied, or credential-protected unless the chosen executor actually enforces that property.

### 4. Execution environment

Executor selection is **independent of approval mode**. Three conceptual execution targets are preserved:

| Target | Meaning | Relationship to ADR-077 |
| --- | --- | --- |
| **Isolated Sandbox Provider** | Execution inside a provider that realizes the ADR-077 provider-neutral contract, including posture establishment, egress, secret isolation, resource ceilings, teardown, and bounded output | Conformant |
| **Trusted container execution** | Execution inside a container the operator trusts, with boundaries **clearly disclosed** rather than asserted | Conformant only where the container genuinely realizes the requested posture; disclosure is mandatory either way |
| **Operator-authorized host-native execution** | Execution directly on the host, in a component **separate from Guardian's application process** | **Deliberate exception. Requires explicit architectural acceptance before any implementation.** |

Requirements:

- The End Operator must be able to configure unrestricted shell execution, persistent automatic authorization, and an explicitly chosen isolation posture.
- **The existing Guardian Docker container is not automatically an ADR-077 Sandbox Provider.** A container that runs the application is not a provider-neutral isolation boundary, and no posture may be claimed on its behalf. Where a trusted container is selected, its real boundaries are disclosed as what they are.
- **Host-native execution must not borrow ambient backend privileges.** It runs under its own host authority, separate from Guardian's application process, so that Guardian's compromise does not silently confer host authority.
- The architecture **permits** operator-selected non-isolated execution. It does not make that mode a default, and no posture becomes a default merely because it is selectable.

### 5. Effective policy resolution

One authoritative resolution algorithm. Instance restrictions set the upper bound; each layer below may narrow but never widen it.

```
effective_policy = resolve(instance_operator_posture,
                            account_grants,
                            project_grants,
                            agent_grants,
                            attempt_request)
```

- Explicit operator configuration can change the **instance's** upper bound. Nothing below the operator can.
- Missing or conflicting authority **never silently escalates**. Absence of a grant is a denial, not a default-allow.
- Configuration **precedence** is not permission **escalation** authority. A more specific configuration winning a lookup does not grant a capability that the operator never granted.
- This algorithm is reconciled with existing profile / project / account capability-binding precedence rather than replacing it.

### 6. Persistence

Persistent operator configuration must survive: application restart, worker restart, new thread creation, model switching, and agent delegation.

The durable record carries: a revision, actor attribution, provenance, and revocation state. An effective-policy inspector exposes the resolved posture and its provenance.

**Existing configuration and persistence ownership is identified before any new storage table is proposed.** The operator control plane under ADR-095 and the existing configuration stores are the owners of truth. This decision does not authorize a parallel configuration store.

### 7. Execution-time posture

Every execution attempt resolves a **trusted, immutable effective execution posture** before anything is dispatched. The posture identifies:

operator/account authority · project/workspace scope · agent/execution principal · tool authority · shell authority · filesystem scope · network posture · approval policy · executor target · isolation posture · resource and deadline constraints.

**Model-supplied metadata cannot expand any of these grants.** Model-authored tool arguments, project documents, tool descriptions, and retrieved content are inputs, not authority.

### 8. Enforcement truth

Five states must be distinguishable in every diagnostic, receipt, and operator-facing surface:

1. **Requested policy** — what was asked for.
2. **Resolved policy** — what authority actually authorized.
3. **Executor-enforced capabilities** — what the selected executor can actually guarantee.
4. **Advisory controls** — what is requested and observed but not enforced.
5. **Operator-disabled controls** — what the operator deliberately turned off.

A capability is never reported as isolated, read-only, network-denied, or credential-protected unless the executor enforces it. **Truthful operator diagnostics are preserved even when approval requirements are disabled.**

Disabling optional diagnostic telemetry is not the same as deleting canonical execution lineage. Message, request, task, and attempt lineage remain canonical and durable.

## Relationship to ADR-077

ADR-077 remains **Accepted and normative**. This record proposes, but does not enact, a narrow exception to two of its requirements, and only for the host-native execution target:

| ADR-077 requirement | Proposed exception |
| --- | --- |
| Security invariant 5 — "A sandbox fails closed if its requested isolation posture cannot be established or attested." | For the host-native target, there is no isolation posture to establish. The exception is that the posture is *absent by explicit operator selection* rather than *failed to establish*. The target must fail closed in a different, truthful way: it must refuse to claim any isolation it does not have. |
| Security invariant 7 — "Tool allowlists and prompt instructions are defense in depth, not sufficient filesystem, network, or process isolation." | For the host-native target, defense in depth is the *only* layer. This is the acknowledged risk of the mode, and it is why the mode is operator-selected, never default, and never silently reached. |
| Security invariant 9 — "A sandboxed process receives no host/container administration capabilities." | Not excepted. The host-native executor is a separate component with its own host authority; it does not receive container administration capabilities from Guardian. |

**All other ADR-077 requirements remain normative for every execution posture**, including the host-native target: the provider-neutral request and result contracts, the evidence-only rule, the completion-evidence rule, truthfulness of execution provenance, and the requirement that a provider never silently substitute a wider posture.

**Acceptance of this record alone changes no runtime behavior.** The host-native exception becomes implementable only through a separate, explicitly accepted implementation decision. Nothing in this record permits an implementation to skip ADR-077.

## Relationship to ADR-108

ADR-108 records that the `/api/music` facade is kept thin and in-process *because model-callable tools are derived from the Guardian application's own OpenAPI schema*.

The native tool surface contemplated alongside this record is **not** an OpenAPI-route-derived surface; it uses the command bus's existing non-HTTP `internal` command layer. This is stated here explicitly so that ADR-111 and ADR-108 do not appear to contradict each other by omission. ADR-108's statement is scoped to its own surface and is neither amended nor reinterpreted by this record. If a future reviewer judges that the model-callable tool surface must be uniformly OpenAPI-derived, that is a separate decision requiring its own record.

## Invariants

- Guardian retains authorization authority.
- Models do not become permission authorities.
- Instance Operator and ordinary User remain distinct.
- Operator authentication, account authorization, configuration ownership, execution permissions, and physical isolation remain five distinct things.
- Approval-free execution is a valid persistent operator policy.
- Operator-authorized direct execution is an explicit architectural exception, never a silent fallback.
- A Project cannot grant itself host authority.
- A persona cannot widen its own permissions.
- Executor capabilities are reported truthfully, including when they are absent.
- The Configuration Inspector remains read-only; no parallel configuration authority is created.
- Provider credentials and command credentials retain separate ownership.
- Existing message, request, task, and attempt lineage remains canonical.
- No parallel tool registry or policy engine is created.
- ADR-105's Campaign Continuation Authority approval requirements are neither generalized nor weakened.
- Supported release claims remain unchanged.

## ADR Impact

Classification: Requires new ADR. ADR-111 is **Proposed**.

- **ADR-077 remains Accepted and normative** until an explicit human architecture decision accepts the operator-direct-execution exception recorded above.
- **ADR-109 is Pending** and is not amended, preempted, or depended upon here.
- No other ADR is amended. ADR-092, ADR-094, ADR-095, ADR-105, ADR-093, ADR-020, and ADR-039 are preserved as written.
- ADR-039 remains Proposed. Reconciling the self-operator case against ADR-039 is a consequence of accepting this record and requires its own explicit treatment.

## Acceptance criteria

1. The authority hierarchy is unambiguous and each of the five authorities is distinct.
2. Persistent approval-free execution is explicitly supported as a valid operator posture.
3. Tool, approval, filesystem, network, and executor policies are separate, independently configurable dimensions.
4. Trusted direct execution is represented as an explicit operator-owned posture with its own host authority.
5. Existing `CODEXIFY_POLICY_MODE` behavior is reconciled rather than duplicated.
6. The ADR-077 conflict and the proposed exception are explicit and unaccepted.
7. Effective policy cannot be widened by model-authored input.
8. Operator and Project configuration boundaries are defined.
9. Enforcement truth and audit requirements are documented.
10. The Configuration Inspector remains read-only and no parallel configuration authority is introduced.
11. No implementation, executor, or release-support claim is added.

## Non-goals

- No shell executor implementation.
- No Docker, sandbox service, or `guardian/sandbox/` changes.
- No host-native agent service.
- No database migration.
- No Settings UI implementation.
- No native tool registration and no command-bus behavior change.
- No policy bypass introduced into running code.
- No change to ADR-095's Configuration Inspector boundary.
- No change to ADR-105's human-approval provenance contract.
- No unrelated architecture cleanup.

## Proof surface

Documentation-only proof:

- ADR relationship consistency, including the proposed ADR-077 exception and its non-activation.
- Explicit operator/user authority separation and the five distinct authorities.
- No conflicting permission precedence.
- No unstated override of ADR-077, ADR-095, or ADR-105.
- No release-claim expansion.

**No runtime execution proof is claimed.**

## Validation

- `git diff --check`
- `pytest -v tests/architecture`
- Manual inspection of the ADR index (both the Reading Order list and the ADR Graph section) and the architecture README reference.

No repository-wide test enforces ADR document shape or index/README registration consistency, so the index and README edits are verified by inspection rather than by an automated gate. Two open pull requests already modify `docs/architecture/adr/adr-index.md`, so index reconciliation is expected at merge time.

## Open decisions for the operator

These are recorded, not decided, by this record:

1. Which execution target is the first to be implemented, and in what order the three targets are proven.
2. Whether the self-operator case is recorded by accepting ADR-039, by amending it, or by a separate record.
3. Where persistent operator posture is stored, once existing configuration ownership is identified.
4. The approval surface for per-action approvals when the operator has selected automatic authorization.
5. Whether ADR-108's OpenAPI-derivation statement should be extended to cover non-OpenAPI native commands.
