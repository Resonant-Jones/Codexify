Grounding note: this spec maps to the current queue-backed runtime and operator-truth doctrine. Critical Flows states that route acceptance means the turn lock was acquired and the task was enqueued, but it does not prove dequeue, eventual success, or UI receipt. Config/Ops also warns that catalog, health, supported profile, and provider registry must be read together because no single green endpoint proves the whole supported posture. Agent operations doctrine likewise says not to treat task acceptance as completion or route/catalog presence as proof of live support.

# Synchronization and Operating Rhythm

## Purpose

Define the Codexify interpretation of weekly team cadence, dashboards, and operating meetings.

In Codexify, these are not merely management rituals. They are synchronization loops for distributed cognition.

## Core Thesis

A meeting is a human synchronization protocol.

A dashboard is an operator truth surface.

A weekly rhythm is a state reconciliation loop.

## Codexify Translation

| Business Ritual | Codexify Equivalent |
| --- | --- |
| Monday planning | Dispatch planning |
| Daily check-in | Health and queue observation |
| KPI review | Runtime/operator truth review |
| Friday debrief | Eval, audit, and proof review |
| Team dashboard | Command Center / diagnostics surface |
| Ownership check | Subsystem and invariant review |
| Hiring decision | Capability allocation decision |

## System Responsibility

This layer answers:

- What is true now?
- What is accepted but not completed?
- What is degraded?
- What is blocked?
- What needs human review?
- What proof exists?
- What changed since the last sync?
- What must not be assumed?

## Related Existing Surfaces

- `/health`
- `/health/chat`
- `/api/health/llm`
- `/api/llm/catalog`
- task events
- eval snapshots
- audit artifacts
- daily audit reports
- Command Center
- runtime state panels
- supported-profile proofs

## Synchronization Loop

```text
observe current truth
  -> compare against supported profile
  -> inspect queue / worker / provider state
  -> review completed tasks and failed attempts
  -> identify degraded or ambiguous states
  -> assign next action
  -> preserve proof
  -> update docs or defer explicitly
```

## Invariants

- Acceptance is not completion.
- Publication is not UI receipt.
- Health is not release readiness.
- Catalog presence is not supported-provider proof.
- Debug traces are diagnostic, not durable proof.
- Runtime proof must come from supported-path evidence.
- Internal-only surfaces must not leak into release claims.

## Failure Modes

| Failure | Consequence |
| --- | --- |
| Treating acceptance as completion | False operational confidence |
| Trusting one green endpoint | Hidden drift |
| No proof capture | Repeated rediscovery |
| No debrief loop | Architecture amnesia |
| Dashboard without doctrine | Decorative telemetry |
| Release claims outrun proof | Trust erosion |

## Product Language

This is the system's "operating rhythm."

It keeps distributed cognition from dissolving into vibes, fog, and cheerful nonsense with a progress bar.
