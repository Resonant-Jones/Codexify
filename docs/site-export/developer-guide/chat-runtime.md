# Chat Runtime

Codexify chat is queue-backed. A user-facing request enters a route, is accepted into a task path, and is later completed by worker execution.

## What Completion Means

Three signals are easy to confuse:

- route acceptance
- task-event publication
- actual turn completion

They are not the same thing.

Route acceptance only means the request entered the queued execution path.
Task-event publication only means visibility was emitted on the event channel.
Worker completion plus a persisted assistant row is stronger proof that the turn actually finished.

## Two State Machines

Chat runtime needs to keep two state machines separate:

- provider runtime state, which describes whether the selected model runtime is reachable, warming, ready, generating, degraded, or offline
- request execution state, which describes what a specific completion attempt is doing after acceptance

The contract docs define canonical token sets for both. The exported guide preserves that distinction because it is required for truthful operator interpretation.

## Identity Boundary

Message identity and attempt identity are separate.

- message identity tracks the authored conversational turn
- attempt identity tracks a specific execution attempt for that turn

That separation is what keeps replay, timeout, and orphan handling from collapsing transcript integrity.

## Supported Interpretation

The live runtime should be read with these rules in mind:

- warming is not the same as offline
- an accepted task is not a completed answer
- a published event is not guaranteed UI receipt
- a retry is a new attempt, not a new message

## Current Support Caveat

The canonical state vocabulary exists in the architecture contracts, but this guide does not claim that every state is emitted literally by every backend path today.
Use `runtime-truth.md`, `operator-truth.md`, and the current-state docs when you need release interpretation.
