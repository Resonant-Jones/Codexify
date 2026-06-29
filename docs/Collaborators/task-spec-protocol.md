# Task Spec Protocol

In Codexify, a Codexify Task Prompt is essentially a Task Spec or Work Packet.

The name is flexible. What matters is the shape.

## Expected Shape

A good task packet usually includes:

- one focused task
- explicit files
- explicit scope
- non-goals
- validation commands
- `git add`
- `git commit`
- closeout summary

## Why The Shape Matters

This shape makes semi-autonomous work loops easier to trust:

1. The task is bounded.
2. The agent executes within that boundary.
3. Validation evidence is reported.
4. A human reviews the result.
5. The knowledge base can be updated if needed.
6. The next task becomes clearer because the previous one is well-scoped.

That is the point of the protocol: make collaboration repeatable without turning it into fog.

## Naming Is Flexible

People may call the same thing a Task Spec, a Work Packet, or a Codexify Task Prompt.

The protocol shape matters more than the label.

## Good Packet Traits

- Narrow enough to finish and review in one pass
- Clear enough that implementation does not depend on hidden context
- Explicit about what should not change
- Honest about validation and closeout expectations
- Small enough that unrelated work can stay outside the task

## Related Docs

- [Agent Protocol Operations Index](../architecture/agent-protocol-operations.md)
- [Codexify Issue Template Contract](../Ops/codexify-issue-template-contract.md)

## Packet Discipline

- Treat issue text as the work packet, not proof that work is done.
- Treat validation results as evidence, not a substitute for review.
- Treat the closeout summary as the handoff record for the next person.
