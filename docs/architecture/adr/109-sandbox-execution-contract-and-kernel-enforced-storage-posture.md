---
tags:
  - architecture
  - adr
  - sandbox
  - provider
  - storage
  - accepted
aliases:
  - ADR-109
  - Sandbox Execution Contract and Kernel-Enforced Storage Posture
---

# ADR-109: Sandbox Execution Contract and Kernel-Enforced Storage Posture

## Status

Accepted

## Date

2026-11-05

## Context

[[077-sandbox-execution-authority-and-provider-boundary|ADR-077]] defines the
provider-neutral sandbox execution contract. It deliberately prescribes no
class names, methods, or tokens: it states that "a later implementation task
must define versioned schemas." It requires, among other things, a bounded
storage posture, and it forbids a provider from "silently allocat[ing] a wider
class when policy requires a hard ceiling."

[[078-modal-initial-hosted-sandbox-provider|ADR-078]] then selected Modal as
the initial hosted provider. Its live conformance proof
(`docs/architecture/proofs/runtime/2026-08-31-modal-read-exec-provider-conformance-proof.md`)
**proved** the read-only workspace, deny-all egress with a preserved control
plane, credential non-disclosure, hard CPU and memory ceilings read from live
cgroup state, a terminal timeout, descendant teardown, and bounded output. It
recorded exactly one unresolved item: `STORAGE_CEILING_UNPROVEN`, because
"Stable Modal 1.5.5 `Sandbox.create` exposed no `storage`, `disk`, or
`disk_size` parameter," and the only available evidence was a measurement
(root `df` reporting `9223372036854771712` bytes), not an enforced ceiling.

Two hosted providers were then evaluated against that clause, and **both fail
it as written**:

- Modal exposes CPU and memory hard limits as `(request, limit)` tuples, but
  its sandbox root filesystem is a fixed 512 GiB that "cannot be increased."
  The ceiling is therefore real but not *selectable*: a request for a 10 GiB
  ceiling is silently served a 512 GiB allocation, which is the "wider class"
  ADR-077 forbids.
- Docker Cloud Sandboxes expose CPU and memory sizing only. There is no disk
  knob, and the microVM root filesystem size is not a settable parameter.

A provider-enforced, *configurable* storage ceiling therefore does not exist
on either vendor. ADR-077 permits "an explicit architecture decision governing
a different resource posture without silently weakening ADR-077," which is
the authority this record exercises.

## Decision

### 1. The contract is now versioned code

`guardian/sandbox/contracts.py` defines the schemas ADR-077 asked a later
implementation to define, under the contract version
`sandbox.execution.v1`:

- `SandboxRequest` carries the request field areas ADR-077 requires:
  contract version, request id, idempotency identity, attempt id, deadline,
  principal, lineage, an integrity-bound workspace materialization, a bounded
  resource posture, a network posture, a secret posture (references only), an
  artifact policy, and the command.
- `SandboxResult` carries the result field areas ADR-077 requires: lineage,
  status, exit posture, failure class, bounded stdout/stderr, the artifact
  manifest (never auto-published), the mutation manifest, resource usage,
  **requested versus attested isolation posture**, provider provenance, and
  teardown status with a cleanup warning.
- A result distinguishes a **boundary-establishment failure** from an
  **execution failure**. "Provider accepted" is never translated into
  "process completed."
- Command text and secret material are never bounded telemetry.
- `guardian/sandbox/policy.py` denies a request whose posture the provider
  cannot establish, **before allocation**. A provider never downgrades a
  requested posture.
- `guardian/sandbox/registry.py` resolves the configured provider.
  Guardian runtime semantics never name a provider; adding a second provider
  is a registration, not a change to runtime code.

### 2. The storage ceiling is kernel-enforced inside the sandbox

ADR-077's storage clause is satisfied by establishing the ceiling **in the
sandbox kernel** rather than through a provider API parameter:

- the workspace is mounted read-only;
- the **only** writable path is a tmpfs created with an explicit `size=`
  option;
- the ceiling is then **attested** from `/proc/mounts` — the kernel's own
  record of what was actually mounted — and compared against the requested
  ceiling;
- if the tmpfs is missing, is not a tmpfs, has no discoverable size, or
  exceeds the requested ceiling, the provider reports a **boundary failure**
  and does not execute the command.

This is a deliberate, recorded reading of ADR-077's storage clause. It is not
a silent weakening: the clause's intent — a bounded, enforced, non-writable
workspace with a hard writable ceiling — is upheld, and the enforcement
mechanism is stated rather than implied. The provider still may not grant a
wider ceiling than policy requests; it grants a *narrower* one and reports the
difference.

The consequence is explicit and accepted: **the storage ceiling is not
provider-enforced in the vendor's own API surface.** The provider's fixed
allocation remains larger than the attested ceiling. A future provider that
exposes a selectable, enforced storage parameter should supersede this clause
and may then advertise the storage posture on provider grounds.

### 3. Docker Cloud Sandbox is the first adapter

`guardian/sandbox/adapters/docker_cloud.py` implements the contract against
Docker Cloud Sandboxes through the `sbx` CLI, and declares the postures it can
establish. It deliberately does **not** declare `secret_isolation`: a request
carrying secret references is denied before allocation rather than leaking
values into an argument vector.

### 4. The sandbox execution route is a service capability, not operator authority

`guardian/routes/sandbox.py` exposes the contract over HTTP for the coding
worker. It authenticates with `require_service_capability`, which validates a
raw service key **without resolving a principal**. It does not use
`require_operator_auth`, so it does not widen the operator-route surface that
[[100-operator-auth-migration-and-credential-boundary|ADR-100]] freezes. The
caller never names a provider.

The `sandbox` route label is admitted as `internal_only` in the
`v1-whooshd-deepseek-web` profile — the shared Whoosh'd Private Preview
profile — and in no other supported profile. `internal_only` mounts the route
while hiding it from the public OpenAPI surface, which is the correct posture
for a worker-to-worker capability that a trusted worker calls directly. Every
other supported profile keeps `sandbox` quarantined, so the contract is not
reachable on a workstation and default Beta is not qualified. The admission is
pinned by the assertion in `tests/core/test_supported_profile.py`, which
requires `sandbox` to be quarantined in the local and tester profiles.

### 5. Pi bash execution is routed through the provider

Pi's bash spawn hook can rewrite a command before it is spawned, but it cannot
host execution somewhere else. The wiring therefore installs an inline Pi
extension that registers a `bash` tool whose spawn hook rewrites the command
into a local proxy; the proxy forwards the command to the sandbox route and
reproduces the remote stdout, stderr, and exit code. The model keeps calling
the ordinary `bash` tool, so the tool-call contract is preserved and only the
execution location moves.

Because the workspace is read-only, `write` and `edit` are not advertised in
sandbox mode. A turn that mandates a `write` tool cannot be satisfied inside a
read-only workspace, so the wrapper **fails closed** rather than advertising a
tool the boundary would reject.

## Consequences

- A hosted coding run can execute inside a provider sandbox with a read-only
  workspace, denied egress, enforced CPU, memory, and storage ceilings, a
  bounded timeout, bounded output, and verified teardown.
- Adding a second sandbox provider requires no change to Guardian runtime
  semantics.
- The storage ceiling is enforced by the sandbox kernel and attested from the
  kernel's mount table. It is not enforced by the vendor's API.
- The Docker adapter has **not** been proven against a live Docker account.
  It is implemented against the documented `sbx` CLI surface and is unit
  tested with an injected command runner. **A live conformance proof is
  required before this provider may be claimed ADR-077 conformant in
  production.**
- The Pi wiring has not been exercised against a live Pi session or a live
  provider account.

## Relationship to other ADRs

Extends [[077-sandbox-execution-authority-and-provider-boundary|ADR-077]] and
[[078-modal-initial-hosted-sandbox-provider|ADR-078]] without superseding
either, and preserves [[069-codexify-beta-runtime-support-boundary|ADR-069]]
and [[100-operator-auth-migration-and-credential-boundary|ADR-100]] unchanged.

## Current-truth boundary

Architecture only. The provider contract, the policy layer, the registry, the
Docker adapter, the service route, and the Pi wiring are implemented, but no
live provider conformance proof exists, the hosted WebUI bundle still mounts
no `worker-coding` service, and this decision does not qualify default Beta.
[[../00-current-state|00 Current State]] remains release authority.
