# High Agency Generalist Role

> Classification: conceptual product/architecture doctrine<br>
> Runtime impact: none<br>
> Release promise: none<br>
> Interpretation rule: if this conflicts with `docs/architecture/00-current-state.md`, current-state wins.

Grounding note: this spec maps to Codexify's bounded orchestration and extension boundaries. In current architecture docs, the bounded tool-augmented completion contract is described as allowing one model-chosen command-bus invocation, reinjecting the result, and then stopping after the final answer to avoid recursive autonomous loops. The self-extending plugin system likewise frames proposals, review, registration, and scoped bindings without allowing silent mutation of identity, provenance, runtime law, or queue/worker semantics. Pi-like invocation is similarly scoped so Guardian remains the policy, lineage, command-authority, and result-return boundary.

## Purpose

Define the Codexify equivalent of the "High Agency Generalist" role.

In Codexify, this is the adaptive execution layer: the part of the system that can coordinate tools, workflows, workers, plugins, and recovery paths without becoming an unbounded autonomous agent.

## Codexify Translation

The High Agency Generalist maps to:

- Guardian orchestration
- command bus
- bounded tool loop
- Flow Builder
- cron/scheduled automation
- coding worker seams
- plugin/capability system
- future Pi-like harness invocation
- operator-guided recovery

## System Responsibility

This role answers:

- What needs to happen next?
- Which capability should perform it?
- Is this action allowed?
- What evidence proves it happened?
- Where should the result return?
- Does this require human review?
- Has the system hit a recursion or authority boundary?

## Design Interpretation

High agency does not mean unlimited autonomy.

In this conceptual mapping, high agency means:

- bounded delegation
- explicit permission
- durable receipts
- result return through Guardian
- no silent mutation
- no recursive tool loops by default
- human authority preserved

## Related Existing Surfaces

- Command bus
- Agent orchestration
- Coding worker
- bounded tool-augmented completion
- Self-Extending Agent Plugin System
- Pi Invocation Boundary
- Flow Builder
- Execution Ledger concepts
- Cron and automation lanes

## Invariants

- Guardian remains the authority boundary.
- External harnesses must not bypass Guardian.
- Tool execution must not become recursive by accident.
- Capability installation must be reviewable.
- Generated extensions may not mutate identity or runtime law.
- Results must return with lineage and receipts.
- Command execution must be idempotency-aware where applicable.

## Failure Modes

| Failure | Consequence |
| --- | --- |
| Recursive tool loop | Loss of control |
| Harness bypasses Guardian | Authority break |
| Plugin writes identity | Sovereignty violation |
| Result lacks receipt | No auditability |
| Action returns outside source thread | Broken continuity |
| Capability drift | Unreviewed system mutation |

## Product Language

This role is the system's "adaptive execution layer."

It is the generalist with a toolbelt, a leash, a clipboard, and a very serious policy binder.
