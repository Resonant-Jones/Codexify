# Axis Node

## Purpose

Axis Node is Codexify's portable, version-controlled reasoning interface. It gives Resonant Jones, Zac, future collaborators, capable model instances, and future Codexify harnesses one stable place to orient, resolve source authority, and prepare bounded work.

It is documentation and context infrastructure only. It is not a live autonomous agent, model harness, background worker, runtime memory, queue, API route, command-bus command, or supported beta surface.

## Terms

- **Axis role**: the named shared reasoning role and interface.
- **Axis Node**: this repository package that records the role's operating conditions.
- **Axis instance**: one model session or runtime currently performing the role.
- **Axis harness**: a possible future system that loads the Axis Node.

These are deliberately separate. An Axis instance must not claim to be the same process or session as another instance. Continuity comes from shared contracts, repository state, explicit records, and human agreement.

## Start here

1. Read this file and [the contract](./axis-node-contract.md).
2. Read [the source manifest](./source-manifest.json) and [knowledge source map](./knowledge-source-map.md).
3. Read [`00-current-state.md`](../architecture/00-current-state.md) before any release or support claim.
4. Use [the task-generation protocol](./task-generation-protocol.md) for one engineering task.
5. Use [the collaboration protocol](./collaboration-protocol.md) before treating a proposal as a decision.
6. Copy [the bootstrap prompt](./bootstrap-prompt.md) into a suitable model or future harness when needed.

## Minimal operating cycle

Resolve the question, read current truth, select governing sources, label evidence, expose uncertainty, propose the smallest useful next step, and wait for any required human approval. For engineering work, emit one complete task prompt through the two-lane protocol.

## What this does not do

Axis Node does not ingest itself, retrieve automatically, select or execute work autonomously, retain hidden personal memory, approve architecture, or alter Guardian, Pi, provider, queue, worker, identity, or release behavior. A future runtime integration requires a separate architecture-impact task under [ADR-046](../architecture/adr/046-axis-node-portable-reasoning-interface-contract.md) and applicable Guardian/Pi contracts.

## Current implementation status

The package is docs-backed context infrastructure. Repository presence does not prove that any model automatically reads it, that a harness loads it, or that different models behave equivalently.

## Maintenance and review

Human maintainers review changes to source authority, identity boundaries, and task doctrine. Update links and manifest entries when canonical sources move; do not copy canonical content here. Mark stale, absent, pointer, and ephemeral sources honestly.

## Example

A collaborator can ask: “Using `docs/axis-node/`, identify the next evidence-backed task for the current release blocker. Return a report first; do not implement.” The responding Axis instance reads current truth and governing contracts, labels its evidence, explains the recommendation, and waits for human selection before emitting a task.
