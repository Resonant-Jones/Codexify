# Codexify Developer Guide

Codexify is sovereign cognitive infrastructure: a local-first system for running chat, retrieval, document context, and bounded tooling under explicit operator control instead of outsourcing core authority to a remote control plane.

## What Codexify is

Codexify is a local-first runtime built around a queue-backed Guardian execution model.
On the current supported path, the system runs through local Docker Compose, persists chat and operational state in Postgres, uses Redis for queues and task-event transport, supports workspace-local retrieval, and keeps provider governance explicit rather than ambient.

For developers, that means Codexify is best understood as:

- a thread-first cognitive runtime
- a Guardian-mediated orchestration layer
- a bounded retrieval and tool-execution system
- a sovereignty-preserving data surface with export and restore guarantees

## What Codexify is not

Codexify is not currently a cloud-first hosted control plane.
It is not currently a proof of autonomous recursive agent execution.
It is not currently a federation-ready general network runtime.
It is not currently a promise that packaged desktop replaces the supported local Compose path.

## Supported runtime reality

The authoritative short-horizon truth lives in [runtime-truth.md](./runtime-truth.md).
Today, the supported path remains local Docker Compose with a local-only provider posture.
Chat completion, upload to embed to readback, workspace-local retrieval, image-turn containment, and coding-result return through Guardian are part of the supported reality on that path.

## Developer map

- [architecture-map.md](./architecture-map.md)
  The guide to reading the rest of the corpus in the right order.
- [runtime-truth.md](./runtime-truth.md)
  The supported runtime contract and its active limits.
- [operator-truth.md](./operator-truth.md)
  The release-truth surfaces and known operational risks.
- [runtime-topology.md](./runtime-topology.md)
  The implemented runtime component map.
- [chat-runtime.md](./chat-runtime.md)
  Queue-backed chat semantics, identity boundaries, and state splits.
- [data-and-storage.md](./data-and-storage.md)
  Storage roles, key entities, lineage, and restore obligations.
- [config-and-ops.md](./config-and-ops.md)
  Provider governance, health surfaces, and operator interpretation.
- [retrieval-and-context.md](./retrieval-and-context.md)
  Retrieval posture and orchestration boundaries.
- [workspace-surface.md](./workspace-surface.md)
  Workspace as Shelf, Scratchpad, and Inspector.
- [identity-and-personas.md](./identity-and-personas.md)
  Identity doctrine and persona boundaries.
- [canonical-tokens.md](./canonical-tokens.md)
  Canonical token discipline for runtime and UI meaning.
- [extension-boundaries.md](./extension-boundaries.md)
  Bounded plugin and extension governance.
- [pi-invocation-boundary.md](./pi-invocation-boundary.md)
  The Pi invocation boundary and Guardian ownership rules.
- [proof-and-validation.md](./proof-and-validation.md)
  What counts as proof and what does not.
- [core-doctrines.md](./core-doctrines.md)
  The engineering laws that keep runtime claims honest.
- [decentralized-infrastructure.md](./decentralized-infrastructure.md)
  The carefully bounded direction toward decentralized network behavior.

## Recommended reading path

1. Start with [architecture-map.md](./architecture-map.md).
2. Read [runtime-truth.md](./runtime-truth.md) and [operator-truth.md](./operator-truth.md) next.
3. Read [runtime-topology.md](./runtime-topology.md), [chat-runtime.md](./chat-runtime.md), and [data-and-storage.md](./data-and-storage.md) to understand the live system shape.
4. Read [config-and-ops.md](./config-and-ops.md), [retrieval-and-context.md](./retrieval-and-context.md), and [canonical-tokens.md](./canonical-tokens.md) for the semantics that keep the runtime honest.
5. Finish with [extension-boundaries.md](./extension-boundaries.md), [pi-invocation-boundary.md](./pi-invocation-boundary.md), [proof-and-validation.md](./proof-and-validation.md), and then [decentralized-infrastructure.md](./decentralized-infrastructure.md) so future direction is interpreted through current supported reality, not the reverse.
