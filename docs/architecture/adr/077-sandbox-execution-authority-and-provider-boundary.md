---
tags:
  - architecture
  - adr
  - guardian
  - coding-worker
  - sandbox
  - execution-authority
  - provider-boundary
aliases:
  - ADR-077
  - Sandbox Execution Authority and Provider Boundary
---

# ADR-077: Sandbox Execution Authority and Provider Boundary

## Status

Accepted.

## Date

2026-08-31

## Acceptance

- Accepted: 2026-08-31
- Human approver: Resonant Jones through the explicitly authorized architecture-impact task that created this ADR
- Evidence posture: documented contract; no runtime behavior or release claim is changed

## Governing context

This decision aligns with and extends:

- [ADR-020: Guardian Mediated Coding Agent Execution Contract](./020-guardian-mediated-coding-agent-execution-contract.md);
- [ADR-068: Campaign Engine Live Role Execution Contract](./068-campaign-engine-live-role-execution-contract.md);
- the [Pi Invocation Boundary Contract](../pi-invocation-boundary-contract.md); and
- the [2026-08-31 Guardian Native Execution Seam Audit](../proofs/runtime/2026-08-31-guardian-native-execution-seam-audit.md).

Those sources keep Guardian authoritative over user intent, permission, lineage,
and result delivery while treating Pi and other harnesses as execution
substrates. This ADR determines where the lower-level authority to construct an
operating-system sandbox belongs. It does not supersede the governing sources'
identity, provider-attestation, mutation-verification, or result-lineage rules.

## Context

Codexify already has an explicit coding execution seam:

```text
Guardian
  -> CodingAgentTaskEnvelope
  -> coding queue
  -> worker-coding
  -> Pi adapter
  -> structured durable result
  -> source-thread result delivery
```

The maintained Pi 0.82.1 surface can select granular tool-name sets and can
intercept Bash child creation through its `spawnHook`. Those capabilities are
necessary but are not an operating-system isolation boundary. A Bash command
can mutate files, use the network, or leave processes behind even when Pi's
`edit` and `write` tools are absent.

The 2026-08-31 implementation investigation attempted to place Bubblewrap
below that hook. The checked-out `worker-coding` container could not establish
the required namespace and root-pivot boundary under its default confinement.
Adding `SYS_ADMIN`, then `SYS_ADMIN + NET_ADMIN`, remained insufficient;
Bubblewrap worked only when the worker was privileged or received broad
namespace capabilities together with unconfined seccomp. Either working
configuration would give the same process that hosts Pi and provider
credentials ambient sandbox-administration authority. The implementation
stopped fail-closed and made no source change.

This is an authority-placement problem, not a missing Pi abstraction. Codexify
needs a provider-neutral boundary below agent-facing workers so current
Guardian read/exec work and later multi-user execution can share one safe
primitive.

## Constitutional answers

1. **Authoritative state:** Guardian's immutable capability grant and
   source-task lineage authorize an execution attempt. Provider telemetry is
   evidence, not authority.
2. **Evidence-only inputs:** provider capability advertisements, allocation
   identifiers, resource measurements, output, artifact manifests, and
   isolation receipts describe an attempt; they do not widen its grant.
3. **Requested capability:** allocate one isolated environment for one
   execution principal, task, workspace, and bounded capability grant, then run
   foreground processes within that boundary.
4. **Authorizing actor:** Guardian resolves user and policy authority. The
   Coding Worker translates the resolved grant but may not enlarge it. A
   Sandbox Provider realizes the already-authorized posture.
5. **Durable state:** Guardian-owned request lineage, attempt status, bounded
   result, artifact references, mutation evidence, and provider provenance may
   become durable under the execution principal and source task. The sandbox
   filesystem is ephemeral unless a separately authorized artifact or mutation
   policy exports selected output.
6. **Completion evidence:** successful allocation, attested establishment of
   every requested boundary, bounded execution and resource results, explicit
   termination, artifact/mutation accounting, and source-lineage correlation.
   Request acceptance or sandbox allocation alone is not completion.

## Decision

Codexify adopts a provider-neutral Sandbox Execution Authority boundary:

```text
Guardian / Coding Worker
        |
        | authorized, bounded request
        v
Sandbox Execution Contract
        |
        | provider adapter
        v
Sandbox Provider administrative plane
        |
        | isolated allocation
        v
Sandboxed Execution Environment
        |
        | bounded result + provenance
        v
Coding Worker -> Guardian durable result and source-thread delivery
```

Sandbox-construction authority belongs inside a Sandbox Provider's isolated
administrative plane. It is not ambient authority of Guardian, the Coding
Worker, Pi, Guardian Chat, or the model/provider process. A provider may
internally use root privileges, namespaces, containers, microVMs, cgroups, or
equivalent platform controls, but agent-controlled processes cannot access
those controls and callers interact only through the bounded contract.

Provider choice is deployment configuration. It is not Guardian UX, product
identity, or a conversational mode. An E2B-hosted adapter, self-hosted E2B, a
future Codexify Linux executor, a rootless-container backend, a microVM backend,
or another provider may satisfy this contract after conformance proof.

## Logical roles and ownership

### Guardian

Guardian owns:

- user intent and execution-principal resolution;
- account, Project, repository, and workspace identity;
- capability grants and approval policy;
- source-message and source-task lineage;
- the decision to accept, deny, retry, or surface an execution result; and
- the final conversational result and truthful delegation explanation.

Guardian does not manage Linux namespaces, cgroups, virtual machines,
containers, or provider-specific sandbox primitives directly.

### Coding / Agent Worker

The Coding Worker owns:

- agent and model execution;
- the Pi runtime when Pi is the selected harness;
- translation of a Guardian grant into the provider-neutral requested posture;
- provider-adapter invocation;
- result normalization, bounded telemetry, and existing mutation verification;
- provider/model runtime identity attestation; and
- return of structured evidence through existing durable lineage.

The Coding Worker MUST remain unprivileged with respect to sandbox
construction. It MUST NOT receive privileged-container status, unrestricted
`CAP_SYS_ADMIN`, unrestricted `CAP_NET_ADMIN`, an unrestricted Docker socket,
or unconfined seccomp solely to construct sandboxes. The worker's provider
credential may authorize bounded provider API calls; it does not grant an
agent-controlled command access to the provider administrative plane.

### Sandbox Execution Contract

The Sandbox Execution Contract is the stable Codexify boundary. It carries an
authorized request from a worker to a provider adapter and returns a normalized
result. The logical request and result names in this ADR are descriptive, not
new canonical runtime tokens or prescribed class names. A later implementation
task must define versioned schemas and register any canonical vocabulary
through the existing token-governance process.

### Sandbox Provider

A Sandbox Provider:

- validates that it can establish every requested posture;
- allocates a tenant- and task-scoped environment;
- materializes only authorized workspace inputs;
- enforces filesystem, process, network, resource, and secret boundaries below
  the model/tool layer;
- executes and supervises the requested process;
- collects bounded output, artifacts, mutations, usage, and provenance;
- terminates or destroys the allocation according to policy; and
- fails without execution when any required boundary cannot be established.

The adapter MUST normalize provider-specific SDK objects and errors. Raw
provider terminology may appear in inspectable provenance, but it MUST NOT
become Guardian's normal conversational vocabulary or authority model.

### Sandboxed Execution Environment

Untrusted or model-generated commands execute only inside this environment.
The environment is isolated from the Coding Worker and from other principals,
tasks, and workspaces. It receives the minimum filesystem, network,
environment, process, and resource posture granted for the attempt.

## Provider-neutral request contract

The request contract MUST be able to express the following logical fields.
Exact encoding is deferred to the implementation slice.

| Area | Required meaning |
| --- | --- |
| Contract and attempt | Contract version, request identity, idempotency identity, attempt identity, and deadline. Retries must not silently create duplicate executions. |
| Principal | Stable execution-principal reference and account/tenant scope. This is an identifier, not a credential or prompt-derived identity. |
| Lineage | Source message, source task, parent attempt, Guardian grant reference or digest, and correlation identifiers required by ADR-020/ADR-068. |
| Workspace | Project/workspace identity plus an immutable, integrity-bound materialization source such as a snapshot, archive, object reference, or provider-neutral fetch plan. A host path alone is not portable authority. |
| Filesystem posture | Read visibility, protected/read-only roots, disposable scratch space, and explicitly allowed writable paths or artifact roots. Omission grants no write authority. |
| Process posture | Foreground executable request, working directory, bounded stdin policy, process count where supported, signal/termination policy, and an explicit background-process posture. Immediate read/exec defaults to no surviving background processes. |
| Time and resources | Wall-clock timeout and maximum CPU, memory, and storage posture. A provider may map these to predeclared resource classes, but it may not silently allocate a wider class when policy requires a hard ceiling. |
| Network posture | No egress by default for the immediate read/exec profile; otherwise an explicit bounded egress posture. Ingress/preview exposure is separate and denied unless granted. |
| Environment and secrets | An allowlist of non-secret environment keys/values and opaque secret references with purpose and delivery constraints. Parent process environments and provider credentials are never copied wholesale. |
| Artifact/output policy | Output byte/time limits, stdout/stderr handling, artifact export roots, permitted media/types/sizes, retention, and whether any workspace mutation may be proposed for later Guardian validation. |
| Termination policy | Kill-on-timeout, disconnect behavior, teardown deadline, and whether pause/resume is forbidden or separately authorized. |

Command text, arguments, stdin, environment values, and secret material may be
necessary inside the encrypted request path, but they are not bounded
telemetry. Logs, metrics, receipts, and ordinary error messages MUST remain
content-free except for output explicitly admitted by the output policy.

### Required read/exec posture

The first implementation must support a posture equivalent to:

- one principal + one source task + one workspace + one capability grant;
- project/workspace inputs visible for reading;
- foreground process execution;
- no exported or effective workspace mutation unless separately authorized;
- no shell-command network egress;
- no background process surviving attempt teardown;
- bounded time, CPU, memory, storage, output, and artifacts;
- scratch storage only where explicitly provided; and
- no provider, database, service, or unrelated user credentials in the child
  environment.

If a provider cannot make an authorized workspace path actually read-only, it
may not claim to satisfy that posture merely because the source was copied into
a disposable filesystem. A disposable copy can protect the source of truth,
but it does not prove in-sandbox mutation denial. The provider adapter must
either establish the requested in-sandbox filesystem boundary or reject that
posture. A separately defined "disposable writable copy with no mutation
export" posture may be considered later; this ADR does not silently equate it
with read-only execution.

## Provider-neutral result contract

The normalized result MUST be able to carry bounded structured fields for:

- request, attempt, principal, task, message, and workspace lineage;
- allocation and execution status;
- exit posture and code when policy permits;
- timeout, cancellation, resource-limit, or termination reason;
- a bounded output summary suitable for Guardian result handling;
- bounded stdout/stderr contents or protected references according to policy;
- an artifact manifest with integrity, size, type, retention, and source path
  metadata, never automatic publication;
- a mutation manifest or explicit no-export/no-mutation posture;
- resource usage where the provider supplies trustworthy measurements;
- the isolation posture requested and the posture the provider attests it
  established;
- provider, adapter, template/image/runtime, region, and sandbox identifiers as
  inspectable provenance; and
- teardown status and any cleanup warning.

The result MUST distinguish execution failure from boundary-establishment
failure and cleanup uncertainty. An adapter may not translate "provider
accepted the request" into "process completed." If teardown cannot be
confirmed, Guardian records the attempt as non-successful and schedules only
provider-owned cleanup/reconciliation; it does not treat the environment as a
trusted reusable shell.

## Lifecycle and consistency

The normal lifecycle is:

```text
authorize -> allocate -> attest boundaries -> materialize -> execute
          -> collect -> terminate -> verify -> persist bounded result
```

- Guardian grants are immutable per attempt. A retry uses the same idempotency
  identity or a new explicitly linked attempt; it does not widen authority.
- Provider allocation state is ephemeral operational state. Guardian's durable
  result and lineage are the system of record for what Codexify requested and
  observed.
- Workspaces and artifacts have explicit source-of-truth ownership. A sandbox
  never becomes canonical merely because a process changed its filesystem.
- An adapter must declare a conformance/capability matrix. Unsupported
  filesystem, network, resource, secret, lifecycle, or artifact requirements
  are denied before execution rather than approximated silently.

## Security invariants

1. Agent-facing workers do not gain ambient sandbox-construction privileges.
2. Model/provider credentials are not exposed to sandboxed commands unless a
   separate, explicit Guardian grant authorizes a purpose-bound secret.
3. Provider/model transport authority is distinct from sandbox-command network
   authority.
4. `allow_network=false` for a sandbox does not disable the parent model client
   or the worker-to-sandbox-provider control connection.
5. A sandbox fails closed if its requested isolation posture cannot be
   established or attested.
6. Denied filesystem mutation is enforced below the model/tool layer.
7. Tool allowlists and prompt instructions are defense in depth, not sufficient
   filesystem, network, or process isolation.
8. A sandboxed process cannot escape into the Coding Worker execution context.
9. A sandboxed process receives no host/container administration capabilities.
10. Cross-user and cross-project access is denied by default.
11. Allocation is scoped to an execution principal, task, workspace, and grant;
    Codexify does not expose one shared mutable shell across users or tasks.
12. Provider implementation details do not become Guardian's conversational
    identity or a user-facing execution mode.
13. Guardian retains truthful, bounded execution provenance sufficient to
    explain delegation when asked.
14. Existing provider/model identity attestation, allowed-path validation,
    pre/post mutation checks, Git posture checks, result validation, and source
    lineage remain active as defense in depth.

### Separate network planes

At least three independent network authorities exist:

```text
model/provider transport     worker -> configured inference provider
sandbox control transport    worker -> selected Sandbox Provider API
command data-plane traffic   sandboxed process -> explicitly granted targets
```

The first two are service control paths held outside the sandbox. The third is
the untrusted command's network posture and defaults to denied for read/exec.
Provider credentials used on either control path stay outside the sandbox. A
provider adapter must not implement command network denial by disabling the
parent worker's network namespace.

## Multi-tenant allocation model

The primitive is:

```text
allocate sandbox for execution principal + task + workspace + capability grant
```

It is not "Resonant Jones's shell" and not a singleton terminal owned by a
worker. Every allocation must bind tenant/account, principal, source task,
workspace, grant, attempt, provider allocation, and teardown state. Provider
credentials may be deployment-scoped, but the adapter must perform
Codexify-owned authorization and preserve per-attempt isolation; a provider
team or API key is not a substitute for Codexify user/project authorization.

This boundary is intended to serve future project inspection, shell
diagnostics, coding tasks, generated applets, data-processing jobs, artifact
generation, temporary development servers, and agent experimentation. Those
capabilities require separate grants, policies, implementation tasks, and proof.
No such feature is implemented or released by this ADR.

## E2B candidate evaluation

E2B is the recommended first hosted Sandbox Provider **candidate**, subject to
contract-adapter implementation and local/provider conformance proof. It is not
the architecture itself and is not integrated by this decision.

The evaluation below uses E2B's public documentation and official open-source
infrastructure as inspected on 2026-08-31. Public documentation is capability
evidence, not proof that Codexify maps or enforces a requested posture
correctly.

| Architecture concern | Current public E2B surface | Codexify proof still required |
| --- | --- | --- |
| Isolation model | E2B documents one Firecracker microVM per sandbox, per-sandbox cgroups and network namespaces, and copy-on-write root filesystems. | Verify the selected hosted or self-hosted deployment/version, tenant isolation assumptions, sandbox escape posture, and provider attestation retained in receipts. |
| Process/shell APIs | SDKs expose foreground/background command execution, process listing, streaming output, signals, and process kill. | Force the read/exec adapter to foreground-only, bound output, terminate the whole allocation, and prove a background descendant cannot survive the lifecycle. |
| Filesystem APIs | SDKs expose read, write, list, upload/download, and other filesystem operations. | Prove immutable workspace materialization, actual read-only paths, writable-root constraints, artifact export, and no unauthorized mutation propagation. Public API availability alone does not prove read-only enforcement. |
| Network controls | Current SDK source exposes per-sandbox internet denial, egress allow/deny selectors, and restricted public traffic; E2B infrastructure documents per-slot nftables egress enforcement. | Prove deny-all egress, DNS behavior, bypass resistance, atomic policy establishment before command start, and separation from worker/provider control traffic for the chosen service tier and region. |
| Environment and secrets | Sandbox creation accepts environment variables, and E2B documents a private-beta workload-identity mechanism that keeps token values out of sandbox code during matching egress requests. | Default to a minimal allowlisted environment; never forward the worker environment or provider credentials. Treat workload identity and any secret broker as unavailable until the selected tier, audience binding, revocation, expiry, and non-disclosure behavior are proved. |
| Resource controls | Templates/build records carry vCPU and RAM; metrics expose CPU, memory, and disk usage; Firecracker and cgroups provide the underlying boundary. | Map every requested CPU/memory/storage ceiling to a provider-enforced template/resource class or reject it. Per-request dynamic sizing and hard storage limits must not be assumed. |
| Lifecycle | SDKs expose create/connect, timeout, kill, and pause/resume/snapshot surfaces. | Immediate read/exec must use kill/teardown rather than persistent pause, confirm termination, handle lost responses idempotently, and reconcile leaked allocations. |
| Artifacts/output | Filesystem APIs and signed upload/download URLs can move selected files; command APIs return structured exit/output information. | Enforce Codexify byte/type/root/retention policy, integrity-bind exported artifacts, redact provider errors, and avoid treating remote filesystem state as durable authority. |
| Temporary previews | `getHost(port)` and the provider proxy can route HTTP/WebSocket traffic from a sandbox port, with restricted-traffic support. | Preview ingress is a separate, default-denied capability; prove authentication, expiry, port scope, teardown, and no cross-tenant exposure before use. |
| Multi-tenancy | E2B allocates separate sandbox VMs and has team/API-key control-plane concepts. | Bind Codexify principal/task/workspace/grant lineage independently; verify quotas, cleanup, region/residency, provider-operator access, and cross-tenant isolation. |
| SDK coupling | JavaScript/Python SDKs and a REST control plane expose the provider feature set. | Keep E2B objects and error taxonomies inside one adapter; conformance tests target the Codexify contract, not E2B-specific conversational behavior. |
| Hosted implications | A hosted service removes sandbox-node privilege from Codexify's Coding Worker and can provide rapid isolated allocations. | Review data residency, retention, subprocess/output confidentiality, provider access, availability, egress, quotas, cost, incident response, and credential rotation before production use. |
| Self-hosting implications | E2B publishes Terraform-based infrastructure for GCP and AWS (AWS described as beta) and documents a privileged Firecracker orchestrator tier separate from callers. | Self-hosting is substantial infrastructure: KVM/nested virtualization, control/data planes, databases, object storage, networking, observability, patching, capacity, and isolation operations become Codexify operator responsibilities. It is not equivalent to enabling Bubblewrap in `worker-coding`. |

Primary evaluation sources:

- [E2B infrastructure architecture](https://github.com/e2b-dev/infra/blob/main/docs/ARCHITECTURE.md)
- [E2B command execution](https://docs.e2b.dev/commands)
- [E2B filesystem read/write](https://docs.e2b.dev/filesystem/read-write)
- [E2B sandbox lifecycle](https://docs.e2b.dev/sandbox)
- [E2B sandbox metrics](https://docs.e2b.dev/sandbox/metrics)
- [E2B sandbox environment variables](https://docs.e2b.dev/sandbox/environment-variables)
- [E2B workload identity](https://docs.e2b.dev/sandbox/workload-identity)
- [E2B internet and egress controls](https://docs.e2b.dev/network/internet-access)
- [E2B sandbox public URLs](https://docs.e2b.dev/network/public-url)
- [E2B self-hosting guide](https://github.com/e2b-dev/infra/blob/main/self-host.md)

The first adapter task must pin and attest the evaluated SDK/API and provider
deployment versions. Later public-provider changes do not automatically amend
this ADR or prove Codexify conformance.

## Relationship to Pi

Pi remains an execution substrate. The maintained Pi Bash `spawnHook` is the
preferred current seam for redirecting Bash child requests to the Sandbox
Execution Contract:

```text
Guardian grant
  -> Coding Worker / Pi
  -> Pi bash spawn request
  -> Sandbox Provider adapter
  -> isolated process
  -> normalized structured result
  -> Pi / Coding Worker
  -> Guardian durable source-thread result
```

Pi's effective tool allowlist remains defense in depth. For a future
read/exec-only session it should expose `read` and `bash` but not `edit` or
`write`; the Sandbox Provider must independently enforce Bash filesystem,
network, resource, secret, and lifecycle bounds.

This contract is not Pi-specific. Future Guardian capabilities may call the
same provider boundary without Pi, provided they carry the same principal,
lineage, capability grant, and policy constraints.

## Relationship to Guardian Native Execution

This ADR is a prerequisite for **Guardian Native Execution — Phase 1:
Read/Exec Bridge**. It does not implement that bridge and does not connect
ordinary Guardian Chat to coding execution.

Expected subsequent slices are:

1. implement and prove the first Sandbox Provider adapter against the
   provider-neutral contract;
2. enforce granular Pi read/exec through that provider;
3. prove filesystem mutation denial, command-network denial, resource limits,
   environment isolation, bounded output, artifact policy, background-process
   containment, teardown, lineage, and existing mutation defenses; and
4. under a separate authorized task, connect ordinary Guardian project-thread
   requests to the existing coding execution seam.

No "Guardian Native Execution" supported-release claim is permitted until the
later bridge and supported-path proof are complete and
[`00-current-state.md`](../00-current-state.md) is separately updated under its
release-truth process.

## Failure modes and required mitigations

| Failure mode | Required response |
| --- | --- |
| Provider cannot establish one requested boundary | Reject before command start; return boundary-establishment failure with bounded provenance. |
| Allocation succeeds but materialization fails | Terminate the allocation; export no workspace mutation; return non-success. |
| Worker/provider response is lost | Reconcile by idempotency/attempt identity; do not issue an uncorrelated duplicate execution. |
| Command exceeds time/resource/output limits | Provider terminates the process/allocation, bounds collected output, records the reason, and returns non-success. |
| Background or descendant process remains | Destroy the allocation; a merely exited parent is not completion. |
| Teardown cannot be confirmed | Mark cleanup uncertain and execution non-successful; invoke provider-owned reconciliation without reusing the environment. |
| Artifact or mutation violates policy | Do not import or publish it; preserve bounded rejection evidence and fail the relevant result posture. |
| Provider version/capability drifts | Fail conformance/attestation and block the posture until the adapter is requalified. |

## Rejected and deferred alternatives

### Privileged Coding Worker — rejected

Granting the existing worker privileged-container status, broad
`CAP_SYS_ADMIN`/`CAP_NET_ADMIN`, or unconfined seccomp so it can sandbox its own
children collapses the trust boundary. Pi, model orchestration, provider
credentials, and sandbox administration would coexist in one compromise
domain. The failed Bubblewrap investigation is evidence that this is not a
small capability exception.

### Direct host execution — rejected

Arbitrary or model-generated commands do not execute directly on the Codexify
host as the normal hosted or multi-user model. Direct host execution creates
ambient filesystem, process, network, secret, and cross-tenant authority that
cannot be reconciled with Guardian's bounded grants.

### Tool-only or prompt-only security — rejected

Pi tool allowlists and prompt restrictions reduce the model's advertised
surface but cannot constrain what an allowed shell does. They remain defense in
depth and never substitute for operating-system/provider enforcement.

### Docker socket delegation — rejected

Pi and the Coding Worker do not receive unrestricted Docker socket access.
Such access is effectively host/container administration, exposes unrelated
workloads, and makes agent-controlled input part of the infrastructure control
plane.

### Provider lock-in — rejected

Guardian contracts are not defined in terms of E2B SDK classes, sandbox URLs,
template identifiers, or error types. E2B may be the first adapter candidate,
but its primitives terminate inside the adapter and remain inspectable
provenance.

### Heavyweight Codexify-owned microVM infrastructure today — deferred

A Codexify-owned Firecracker or other microVM fleet could satisfy this contract
in the future and may improve local sovereignty or specialized policy control.
It is deferred because it introduces a dedicated privileged control plane,
capacity management, image lifecycle, networking, patching, observability, and
multi-tenant operations. The provider boundary preserves this option without
making it the first implementation.

### Bubblewrap inside the existing worker — rejected for the current deployment

Bubblewrap itself is not categorically rejected. Constructing its namespace
boundary inside `worker-coding` under the current container confinement either
fails or requires unacceptable ambient privileges. A future separate,
minimal, provider-owned local executor may use Bubblewrap or rootless container
primitives if its administrative authority is isolated behind this contract
and it passes conformance proof.

## Consequences

### Positive

- Guardian authority remains explicit while operating-system privilege moves
  out of agent-facing workers.
- Provider/model transport can remain available while shell-command network is
  denied.
- Pi's `spawnHook` becomes a narrow integration seam rather than a new broker.
- The same contract can serve immediate read/exec and later multi-user jobs.
- Hosted, self-hosted, rootless-container, and microVM implementations remain
  replaceable.
- Provider-specific capabilities and failures become bounded provenance rather
  than product identity.

### Costs and tradeoffs

- A provider adapter, conformance suite, capability matrix, reconciliation
  loop, and operational lifecycle are required before execution can ship.
- Remote providers add data residency, confidentiality, availability, quota,
  latency, cost, and vendor operational dependencies.
- Self-hosted providers preserve control but require a distinct privileged
  sandbox control plane and substantial operations.
- Resource and filesystem semantics vary across providers; the contract must
  reject unsupported exact postures instead of pretending they are equivalent.
- Temporary previews and persistent environments create separate ingress and
  lifecycle risks and therefore require separate grants.

## Non-goals and release boundary

This ADR does not:

- integrate E2B or install a provider SDK;
- change worker privileges, Docker capabilities, Bubblewrap, or Compose;
- modify Pi, the coding adapter, Guardian Chat, ordinary-turn routing, provider
  selection, model routing, credential storage, billing, or database schemas;
- implement applets, multi-user sandbox UI, persistent agents, or background
  execution;
- prove a hosted or self-hosted Sandbox Provider;
- establish Guardian Native Execution as supported; or
- change [`00-current-state.md`](../00-current-state.md).

The evidence posture is documented contract only. Runtime implementation,
provider qualification, live isolation, supported-path proof, and release
promotion require separately authorized tasks.
