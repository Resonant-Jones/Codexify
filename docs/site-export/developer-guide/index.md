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

- [core-doctrines.md](./core-doctrines.md)
  The engineering laws that keep runtime claims honest.
- [runtime-truth.md](./runtime-truth.md)
  The supported runtime contract and its active limits.
- [decentralized-infrastructure.md](./decentralized-infrastructure.md)
  The carefully bounded direction toward decentralized network behavior.

## Recommended reading path

1. Start with [runtime-truth.md](./runtime-truth.md).
2. Read [core-doctrines.md](./core-doctrines.md) to understand the guardrails behind those claims.
3. Read [decentralized-infrastructure.md](./decentralized-infrastructure.md) last so future direction is interpreted through current supported reality, not the reverse.
