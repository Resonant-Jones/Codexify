# ADR-039: Capability-Oriented Mesh Architecture

**Status:** Accepted (Architectural Principle)  
**Date:** 2026-06-30  
**Scope:** Architecture, networking, customer isolation, provider routing, transport abstraction

---

## Context

Codexify is expected to operate across heterogeneous infrastructure:

- Local developer machines
- LAN-connected private nodes
- Tailscale tailnets
- Headscale-managed meshes
- Cloud-hosted services
- Customer-owned hardware
- Mobile clients
- Future transport mechanisms

The initial networking exploration assumed that tailnet membership could act as the practical trust boundary between users, devices, customers, and private infrastructure.

That model breaks down as soon as Codexify must serve multiple trust domains at once.

Observed constraints:

- A normal Tailscale client is active in one tailnet at a time.
- Operator devices may need administrative access to multiple environments.
- Customer-facing services must remain reliable and must not depend on tailnet switching.
- Customers must not inherit broad access to internal infrastructure.
- Private model hosts, memory stores, databases, embeddings, and secrets must remain behind explicit service boundaries.
- Headscale can provide a self-owned control plane, but it does not remove the need for explicit trust isolation.
- Subnet routing is powerful but too broad for most customer-facing boundaries.

The architecture therefore cannot depend on raw network membership as the authorization model.

Network access is not the same thing as capability authorization.

---

## Decision

Codexify SHALL model the system as a capability mesh rather than a machine mesh.

Codexify SHALL expose capabilities through governed boundaries instead of exposing machines, subnets, or raw infrastructure surfaces.

Networking SHALL be treated as a transport implementation beneath the application and authorization layer.

Authorization SHALL be based on explicit identity, policy, and capability grants, not implicit membership in a tailnet, subnet, LAN, VM network, or provider environment.

---

## Architectural Principle

> Expose capabilities, not machines.

Operational corollaries:

- Route intent, not packets.
- Trust boundaries are product architecture.
- Network membership is not authorization.
- Customer access terminates at a governed edge.
- Private resources remain private even when their capabilities are shared.

---

## Core Pattern

Every Codexify interaction should be expressible as:

```text
Resource
    -> Boundary
    -> Capability
    -> Consumer
```

Examples:

```text
VaultNode
    -> AxisNode
    -> Memory.Search
    -> Phone Client
```

```text
Private LLM Runtime
    -> Codexify Provider Broker
    -> Model.Complete
    -> Customer Workspace
```

```text
Postgres
    -> Repository Interface
    -> Thread.Read
    -> Authenticated User
```

The consumer must not need to know which machine, network, or provider executes the work.

---

## Node Role Model

Nodes represent architectural responsibilities rather than fixed hardware.

Canonical role vocabulary:

| Role | Responsibility | Boundary Posture |
|---|---|---|
| `VaultNode` | Stores and protects private resources | Never customer-facing |
| `AxisNode` | Routes, governs, authenticates, brokers | Controlled service boundary |
| `ScoutNode` | Observes, checks, discovers, reports | Read-biased / inspection-biased |
| `EdgeNode` | Exposes limited customer or device access | Public or semi-public boundary |
| `BridgeNode` | Translates between trust domains | Explicitly audited seam |

Hardware may change. Role semantics should remain stable.

A Mac mini, VM, container, cloud instance, or Kubernetes workload may implement a role, but the role must define the trust posture.

---

## Trust Domain Separation

Codexify deployments SHOULD separate private resources from customer-facing surfaces.

Recommended topology:

```text
Customer / Phone / External Client
        |
        v
Customer Tailnet, HTTPS, Cloudflare Tunnel, or Edge Transport
        |
        v
AxisNode / EdgeNode
        |
        v
Local service interface, queue, repository, or provider adapter
        |
        v
VaultNode / Private Infrastructure
```

The customer-facing network must not automatically expose:

- raw model server ports
- LAN subnets
- private tailnets
- database ports
- embedding stores
- object storage backends
- SSH surfaces
- unrestricted filesystem mounts
- secrets or operator controls

Customer access terminates at the edge or broker.

Private infrastructure responds only through scoped service contracts.

---

## Transport Abstraction

Codexify SHALL treat transports as interchangeable execution paths.

Candidate transports:

- `localhost`
- `unix_socket`
- `lan`
- `tailscale`
- `headscale`
- `wireguard`
- `https`
- `cloudflare_tunnel`
- `queue`
- `container_network`
- `future_transport`

A capability may advertise transport metadata, but callers must not bind directly to transport details unless explicitly operating in a diagnostic or administrative mode.

Candidate capability descriptor:

```yaml
name: Memory.Search
owner: VaultNode
required_permissions:
  - memory.search
available_transports:
  - lan
  - tailscale
  - https
preferred_transports:
  - localhost
  - lan
  - tailscale
visibility: private
health: healthy
```

Transport selection belongs to the broker/router layer.

Capability authorization belongs to the policy layer.

---

## Provider Symmetry

Transport routing follows the same architectural pattern as model/provider routing.

Model provider examples:

```text
OpenAI
Anthropic
Gemini
Ollama
Local GGUF Runtime
```

Transport provider examples:

```text
LAN
Tailscale
Headscale
HTTPS
Unix Socket
Queue
```

Both are implementation providers beneath a capability contract.

Codexify should not be architected as the Tailscale version, the Headscale version, the Ollama version, or the cloud version.

Codexify should route capabilities across whatever provider or transport is authorized, healthy, and appropriate for the request.

---

## Subnet Routing Policy

Subnet routing MAY be used for internal operator infrastructure.

Subnet routing SHOULD NOT be the default customer-facing integration pattern.

Customer-facing access SHOULD prefer:

- authenticated APIs
- scoped provider adapters
- queue-backed jobs
- read-only mounts
- signed URLs
- repository interfaces
- service accounts with constrained credentials
- explicit tool permissions

Customer-facing access SHOULD avoid:

- raw subnet access
- broad SSH access
- database-level exposure
- tailnet-wide membership as a substitute for authorization
- bridge VMs with unconstrained forwarding between private and customer networks

Subnet routing is a network primitive, not a product authorization model.

---

## Machine-in-the-Middle Pattern

A host may safely sit between private infrastructure and customer-facing service islands only if it behaves as a broker, not a transparent bridge.

Safe form:

```text
Private Resource
    -> Host-controlled narrow seam
    -> Customer VM / Service Island
    -> Customer Capability
```

Unsafe form:

```text
Customer Tailnet
    -> VM
    -> Subnet Router
    -> Private LAN / Private Tailnet
```

The middle machine may provide:

- a local API
- an internal queue
- a scoped reverse proxy
- a read-only mount
- a redacted data export
- a metered model endpoint
- a limited tool adapter

The middle machine must not silently route the customer into private infrastructure.

---

## Customer Isolation Contract

Each customer or external trust domain SHOULD receive a bounded service island.

Example:

```text
Physical Host
  - Host OS: Resonant private tailnet
  - VM A: Customer A tailnet / customer edge
  - VM B: Customer B tailnet / customer edge
  - Local-only seams from host to each VM
```

Each service island must have:

- explicit ingress
- explicit egress
- explicit identity context
- explicit capability grants
- scoped logs
- revocation path
- no implicit access to sibling customers
- no implicit access to operator infrastructure

A customer island consumes capabilities. It does not own the infrastructure behind those capabilities.

---

## Reliability Implication

Production customer access MUST NOT depend on an operator device switching tailnets.

CLI-driven tailnet switching may be useful for operator convenience, debugging, or local administration.

It must not be used as a runtime dependency for customer reliability.

Production paths require stable identities:

```text
customer-a-edge: always present in Customer A trust domain
customer-b-edge: always present in Customer B trust domain
vaultnode: always present in private trust domain
axisnode: always present at the broker boundary
```

A customer-facing lighthouse must not rotate between oceans.

---

## Fractal Architecture

This principle applies recursively.

At each scale, Codexify should ask the same questions:

```text
What capabilities do I provide?
What capabilities do I consume?
What boundary do I enforce?
Who is authorized?
What evidence proves the boundary is working?
```

Applicable scales:

```text
Function
  -> Module
  -> Service
  -> Node
  -> Workspace
  -> Customer Island
  -> Organization
  -> Mesh
```

The same rule applies at every layer:

> Resources stay behind boundaries. Capabilities cross boundaries under policy.

---

## Security Requirements

Future implementation work derived from this ADR must preserve the following invariants:

1. Customer access does not imply private infrastructure access.
2. Tailnet membership does not imply capability authorization.
3. Subnet reachability does not imply application permission.
4. Broker nodes must authenticate, authorize, meter, and log capability invocations.
5. Private model runtimes must not be directly exposed to customers by default.
6. Provider adapters must not leak raw credentials, private endpoints, or diagnostic internals.
7. Cross-domain bridge behavior must be explicit, reviewed, and testable.
8. Revocation must be possible at the capability layer even if the network path still exists.
9. Service islands must not have implicit lateral movement into sibling islands.
10. Runtime transport selection must not bypass policy evaluation.

---

## Runtime Non-Decision

This ADR does not implement:

- Tailscale integration
- Headscale integration
- subnet routers
- VM orchestration
- transport registry code
- provider broker code
- capability registry persistence
- customer isolation automation

This is an architecture decision and boundary contract.

Implementation requires follow-on design, proof harnesses, and security sweeps.

---

## Consequences

### Positive

- Decouples trust from network membership.
- Supports multiple customer trust domains without operator tailnet switching.
- Keeps private model and memory infrastructure behind brokered seams.
- Makes Tailscale, Headscale, LAN, HTTPS, and future transports interchangeable.
- Aligns networking with existing provider-routing instincts.
- Enables enterprise-style customer isolation without overexposing infrastructure.
- Produces a stable conceptual model for Codexify as a capability mesh.

### Tradeoffs

- Requires a capability registry or equivalent routing contract.
- Requires explicit broker/service boundaries.
- Requires more policy design before runtime implementation.
- Requires security review for bridge nodes and service islands.
- Adds abstraction overhead compared to direct machine access.

The tradeoff is accepted because direct machine access does not scale safely across customers, devices, and sovereign infrastructure boundaries.

---

## Follow-On Work

| Work Item | Description | Dependency |
|---|---|---|
| Capability registry proposal | Define canonical capability descriptor schema, visibility, health, and permission fields | This ADR |
| Transport registry proposal | Define transport adapter vocabulary and selection rules | Capability registry proposal |
| Customer service island contract | Define per-customer edge/VM/container isolation requirements | This ADR |
| Broker authorization proof | Prove policy evaluation occurs before transport execution | Capability registry proposal |
| VaultNode exposure audit | Verify private model/memory/database surfaces are not directly customer reachable | This ADR |
| Headscale/Tailscale evaluation note | Compare managed Tailscale, Headscale, and raw WireGuard against this ADR | Transport registry proposal |
| Subnet router safety note | Document when subnet routing is allowed, forbidden, or operator-only | This ADR |

---

## Decision Summary

Codexify is not a VPN-shaped product.

Codexify is a capability mesh.

Machines may host capabilities. Networks may carry capability calls. Providers may execute capability work.

But trust belongs to explicit authorization at the capability boundary.

The architectural spine is therefore:

```text
Expose capabilities, not machines.
Route intent, not packets.
Treat transport as implementation.
Treat boundaries as product architecture.
```
