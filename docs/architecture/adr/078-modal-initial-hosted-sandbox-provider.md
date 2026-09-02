---
tags:
  - architecture
  - adr
  - guardian
  - sandbox
  - execution-authority
  - provider-boundary
  - modal
aliases:
  - ADR-078
  - Modal Initial Hosted Sandbox Provider
---

# ADR-078: Modal as the Initial Hosted Sandbox Provider

## Status

Accepted.

## Date

2026-08-31

## Acceptance

- Accepted: 2026-08-31
- Human approver: Resonant Jones through the explicit operator decision that
  authorized this architecture-impact task
- Evidence posture: documented contract grounded by the committed live-runtime
  provider qualification; no runtime behavior or release claim is changed

## Governing context

This decision is subordinate to and aligned with
[ADR-077: Sandbox Execution Authority and Provider Boundary](./077-sandbox-execution-authority-and-provider-boundary.md).
ADR-077 remains the canonical provider-neutral authority boundary. This ADR
selects an initial hosted implementation target behind that boundary; it does
not supersede, narrow, or weaken ADR-077.

Related doctrine includes:

- [ADR-020: Guardian Mediated Coding Agent Execution Contract](./020-guardian-mediated-coding-agent-execution-contract.md),
  which keeps Guardian authoritative over request, policy, transcript, and
  lineage;
- [ADR-068: Campaign Engine Live Role Execution Contract](./068-campaign-engine-live-role-execution-contract.md),
  which preserves bounded Guardian-authorized execution and receipts;
- [ADR-062: Provider Capability Model Contract](./062-provider-capability-model-contract.md),
  which proposes evidence-backed capability distinctions and explicitly keeps
  runtime proof separate from release support; and
- the [Pi Invocation Boundary Contract](../pi-invocation-boundary-contract.md),
  which treats Pi as an execution substrate rather than product identity or
  authority owner.

The local committed architecture and proof corpus is authoritative for this
decision. A public or connected branch that predates ADR-077 or the provider
qualification receipts does not override newer local evidence.

## Context

ADR-077 requires untrusted or model-generated processes to execute behind a
provider-neutral `SandboxProvider` boundary while Guardian, `worker-coding`,
Pi, and model/provider processes remain unprivileged with respect to sandbox
administration.

Two hosted candidates were qualified against the immediate read/exec posture:

- E2B remained partially conformant because the tested hosted API did not
  expose a provider-enforced read-only workspace/input mechanism and did not
  prove a hard storage ceiling.
- Modal 1.5.5 proved the strict read-only workspace boundary and all other
  mandatory isolation properties exercised by the bounded qualification except
  for a provider-enforced storage/disk ceiling through the stable Sandbox API.

The committed Modal receipt concludes exactly:

`MODAL_READ_EXEC_PARTIALLY_CONFORMANT`

Its single mandatory ADR-077 failure is:

`STORAGE_CEILING_UNPROVEN`

The operator has selected Modal as Codexify's initial hosted execution-plane
vendor. The selection must be recorded before provider-specific implementation
begins, without converting partial qualification into production approval.

## Constitutional answers

1. **Authoritative state:** Guardian's capability grant, execution principal,
   workspace authority, and source-task lineage remain authoritative. This ADR
   records provider selection, not execution permission.
2. **Evidence-only inputs:** the Modal and E2B qualification receipts describe
   observed provider behavior. Provider IDs, measurements, and catalog breadth
   do not grant capability or establish release support.
3. **Requested capability:** implement ADR-077's provider-neutral read/exec
   contract through the first selected hosted provider.
4. **Authorizing actor:** the operator selects the deployment target; Guardian
   authorizes each future execution. Modal may realize only the bounded request
   it receives.
5. **Durable state:** this ADR and future Guardian-owned request/result lineage
   are durable. A Modal sandbox filesystem is never canonical application or
   workspace state merely because it exists.
6. **Completion evidence:** provider selection is complete when this decision
   is accepted and indexed. Provider qualification, adapter implementation,
   supported-path proof, and release support remain separate gates.

## Decision

Codexify will target **Modal as the first hosted implementation** of ADR-077's
provider-neutral `SandboxProvider` boundary.

The architecture remains:

```text
Guardian / Coding Worker
        |
        | Codexify-owned bounded request
        v
provider-neutral SandboxProvider contract
        |
        | Modal adapter (initial hosted implementation target)
        v
Modal administrative plane
        |
        | isolated allocation
        v
sandboxed execution environment
        |
        | Codexify-owned bounded result + inspectable provenance
        v
Coding Worker -> Guardian durable result and source-thread delivery
```

Modal is an implementation choice, not architectural authority. Guardian owns
intent, identity, policy, permission, lineage, and result interpretation.
Codexify-owned request/result contracts remain canonical. Modal SDK objects,
resource names, errors, and service concepts terminate inside the adapter
except where bounded provider provenance is retained for inspection.

Adding or replacing a provider must not require a change to Guardian-facing
execution semantics when the provider can satisfy the same Codexify contract.

## Selection, qualification, implementation, and release are distinct

The following postures MUST NOT collapse:

| Posture | Meaning after this ADR |
| --- | --- |
| Provider selection | **Complete.** Modal is the selected initial hosted implementation target. |
| Provider qualification | **Partial.** The bounded live proof passed every tested mandatory gate except a proven hard storage ceiling. |
| Provider implementation | **Not implemented.** No production Modal `SandboxProvider` adapter exists. |
| Supported runtime path | **Not established.** Pi and ordinary Guardian execution do not route through Modal. |
| Release support | **Not claimed.** `00-current-state.md` remains unchanged and authoritative. |

Therefore:

```text
Modal selected != Modal fully qualified
Modal qualified != adapter implemented
adapter implemented != supported runtime path
supported runtime path != release support
```

## Why Modal was selected

The selection is grounded in the committed
[Modal ADR-077 read/exec conformance proof](../proofs/runtime/2026-08-31-modal-read-exec-provider-conformance-proof.md),
not vendor marketing or catalog breadth. Within that bounded live
qualification, Modal demonstrated:

- a provider-enforced read-only Volume mount that preserved protected
  workspace content and namespace state across mutation attacks and a fresh
  mount;
- no effective permission reversal or writable protected-workspace state,
  including when guest `chmod` or `chown` returned success;
- deny-all command-network egress while provider control traffic remained
  functional outside the sandbox command environment;
- enforceable CPU and memory ceilings;
- timeout enforcement and whole-sandbox teardown;
- no background descendant surviving sandbox teardown;
- exclusion of parent/provider credentials and a bounded child environment;
- bounded output behavior and task/workspace/grant lineage retention; and
- explicit terminal sandbox cleanup and deletion of proof Volumes.

Operational simplicity and Modal's broader hosted-service portfolio are
secondary considerations only. They are not security evidence and do not
close any ADR-077 gate.

The committed
[E2B read/exec conformance proof](../proofs/runtime/2026-08-31-e2b-read-exec-provider-conformance-proof.md)
and
[E2B read-only-input qualification](../proofs/runtime/2026-08-31-e2b-provider-read-only-input-qualification-proof.md)
remain useful contrast: the tested E2B surface did not provide the strict
provider-enforced read-only input posture required by ADR-077. This decision
does not permanently exclude E2B or another future conformant provider.

## Remaining mandatory qualification blocker

Modal 1.5.5's stable Sandbox API did not expose a proven provider-enforced
per-Sandbox storage or disk ceiling. Filesystem-capacity measurement is not a
hard allocation limit and does not satisfy ADR-077's bounded-resource
requirement.

`STORAGE_CEILING_UNPROVEN` remains fail-closed. The production adapter cannot
claim the ADR-077 read/exec posture, enter a supported runtime path, or support
a release claim until a separately authorized task either:

1. proves a provider-enforced storage ceiling through a stable,
   account-available Modal surface; or
2. obtains an explicit architecture decision governing a different resource
   posture without silently weakening ADR-077.

This ADR does neither. Partial conformance must remain visible in capability
declarations, adapter gates, proof receipts, and operator-facing diagnostics.

## Provider neutrality and privilege separation

ADR-077's authority placement remains unchanged:

- Guardian, `worker-coding`, Pi, and the model/provider process remain
  unprivileged with respect to sandbox construction.
- Modal receives only the narrow provider credential and request authority
  needed to allocate and supervise a sandbox.
- Modal credentials remain outside the repository and outside sandbox command
  environments unless a separately governed secret-delivery contract
  explicitly authorizes delivery.
- Provider/model transport remains distinct from sandbox-command network
  authority.
- A failed or unavailable isolation control rejects execution rather than
  silently allocating a wider posture.
- Tool allowlists remain defense in depth; filesystem, network, process,
  resource, and environment enforcement occurs below the model/tool layer.

Modal does not become a Codexify identity, policy, permission, transcript,
workspace-authority, or application-authority surface.

## Adjacent Modal services

Modal's broader service portfolio may reduce future integration cost, but
vendor convenience grants no authority to expand Codexify's dependency graph.
No Modal storage, inference, queue, function, database, web endpoint, app
hosting, secret-delivery, or other adjacent service is admitted by this ADR.

Every proposed adjacent capability must independently follow:

```text
discover → classify → park/admit → execute → prove → revalidate
```

It must also pass the normal Codexify discovery intake, authority review,
credential review, evidence requirements, and release-truth gates. Selecting
one vendor for sandbox execution does not make that vendor a general-purpose
control plane.

## Relationship to Pi and Guardian Native Execution

Pi remains one possible execution substrate. Its maintained Bash `spawnHook`
is the preferred current seam for redirecting a future Pi Bash child request
through the provider-neutral contract and a Modal adapter:

```text
Guardian grant
  -> Coding Worker / Pi
  -> Pi bash spawnHook
  -> SandboxProvider contract
  -> Modal adapter
  -> isolated process
  -> normalized result
  -> Pi / worker
  -> Guardian durable source-thread result
```

The Modal adapter must not become Pi-specific architecture; other authorized
Guardian capabilities may eventually consume the same provider-neutral
contract.

This ADR is a provider-selection prerequisite for **Guardian Native Execution
— Phase 1: Read/Exec Bridge**. It does not implement the adapter, wire Pi,
connect ordinary Guardian Chat, or change user-visible execution behavior.

## Consequences

### Positive

- The first hosted implementation target is explicit before provider-specific
  code is introduced.
- Selection is grounded in live isolation evidence while preserving the
  unresolved resource gate.
- Guardian semantics and Codexify request/result contracts remain portable.
- Agent-facing workers retain least privilege and provider credentials remain
  outside sandbox command environments.
- Later providers can be added or substituted through the same conformance
  boundary.

### Costs and risks

- Modal becomes an operational dependency if and when a production adapter is
  implemented and supported.
- Availability, pricing, data residency, retention, provider-operator access,
  quotas, API drift, and incident response require separate operational review
  and revalidation.
- The missing hard storage ceiling blocks full qualification today.
- Adapter code must normalize Modal-specific behavior without leaking it into
  Guardian policy or UX.
- Broader vendor functionality can tempt scope expansion; the adjacent-service
  intake gate is therefore explicit.

## Deferred implementation and proof

Separately authorized tasks must:

1. qualify a stable provider-enforced Modal Sandbox storage ceiling or return
   for architecture review;
2. implement the Modal adapter behind ADR-077's provider-neutral request/result
   boundary;
3. prove fail-closed mapping, lifecycle reconciliation, credential handling,
   provider drift detection, and all mandatory resource and isolation gates;
4. enforce granular Pi read/exec through the adapter; and
5. only after supported-path proof, consider ordinary Guardian project-thread
   routing and a separate `00-current-state.md` release-truth update.

No step inherits approval from this ADR merely because Modal is selected.

## Non-goals and release boundary

This ADR does not:

- implement or configure Modal;
- install a Modal SDK or copy credentials;
- change ADR-077 or its resource requirements;
- modify provider, worker, Pi, Guardian Chat, ordinary-turn, database, or
  release behavior;
- qualify Modal fully;
- admit any adjacent Modal service;
- claim a supported sandbox path or Guardian Native Execution; or
- modify [`00-current-state.md`](../00-current-state.md).

The evidence posture is a documented provider-selection contract grounded by
existing bounded live proof. No new runtime proof is created by this ADR.

## Related documents

- [ADR-077: Sandbox Execution Authority and Provider Boundary](./077-sandbox-execution-authority-and-provider-boundary.md)
- [ADR-062: Provider Capability Model Contract](./062-provider-capability-model-contract.md)
- [Modal ADR-077 read/exec conformance proof](../proofs/runtime/2026-08-31-modal-read-exec-provider-conformance-proof.md)
- [E2B ADR-077 read/exec conformance proof](../proofs/runtime/2026-08-31-e2b-read-exec-provider-conformance-proof.md)
- [E2B provider read-only-input qualification](../proofs/runtime/2026-08-31-e2b-provider-read-only-input-qualification-proof.md)
- [`00-current-state.md`](../00-current-state.md)

## Axis KB addition

Record that ADR-078 selects Modal as Codexify's initial hosted
`SandboxProvider` implementation target behind ADR-077's provider-neutral
boundary. Modal 1.5.5 remains `MODAL_READ_EXEC_PARTIALLY_CONFORMANT` with
`STORAGE_CEILING_UNPROVEN` as the sole mandatory blocker. Selection is not full
qualification, implementation, supported-path proof, or release support, and
no adjacent Modal service is admitted by the decision.
