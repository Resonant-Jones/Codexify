# Core Doctrines

## Runtime truth outranks aspiration

Treat `docs/architecture/00-current-state.md` as the short-horizon release truth.
Older plans, broader architecture notes, and attractive future-state language do not widen the supported promise on their own.

## Route acceptance is not completion

A request accepted by a route has only entered the queue-backed execution path.
Completion depends on downstream worker, provider, persistence, and event publication behavior.

## Task-event publication is not UI receipt

Task events can exist without the UI receiving or rendering them.
When debugging user-visible behavior, keep queue publication, transport delivery, and shell receipt as separate layers.

## Personas borrow identity; they do not own it

Persona and profile systems can shape behavior, but durable identity remains user-owned.
Do not let persona features silently redefine ownership, provenance, or durable facts.

## Retrieval policy belongs in orchestration, not prompt text

Retrieval scope and widening decisions belong in the router and broker layer.
Do not bury retrieval behavior inside prompt instructions or ad hoc UI heuristics.

## Export and restore are sovereignty guarantees

Users must be able to carry their canonical state, lineage, and artifact relationships with them.
Restore must fail closed or report loss explicitly instead of silently degrading.

## Repeated contract-bearing literals must become canonical tokens

When a runtime status, lifecycle state, or stop reason becomes part of the truth surface, promote it into a canonical token contract.
Do not let route, queue, worker, and UI layers drift on inline literals.

## Agent execution must be bounded, inspectable, and Guardian-mediated

Codexify’s current tool and extension seams are intentionally narrow.
One bounded tool turn, explicit command-bus authority, lineage-preserving reinjection, and reviewable extension governance outrank any shortcut toward opaque autonomy.
