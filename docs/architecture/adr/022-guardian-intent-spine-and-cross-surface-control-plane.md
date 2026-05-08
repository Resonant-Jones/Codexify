---
tags:
* architecture
* adr
* guardian
* intent
* control-plane
* voice
* automation
* cli
  aliases:
* ADR-022
* Guardian Intent Spine and Cross-Surface Control Plane
---

# ADR-022: Guardian Intent Spine and Cross-Surface Control Plane

## Status

Proposed

## Date

2026-05-04

## Classification

This ADR is architecture-impacting.

## Governing ADRs

- ADR-003: Message Identity vs Request Identity
- ADR-010: Self-Extending Agent Plugin System
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-020: Guardian Mediated Coding Agent Execution Contract
- ADR-021: Web Agent Boundary and Retrieval Contract

## Context

Codexify already has several adjacent contracts that each solve part of the
"do this on my behalf" problem:

- the command bus defines a durable execution lane for commands and receipts
- the delegation runtime defines source-thread provenance and run persistence
- the coding-agent contract defines Guardian-owned request and result handling
- the web-agent boundary defines separate retrieval and interaction modes
- Persona Studio defines profile and capability surfaces, but not live runtime
  enforcement

What Codexify does not yet have is a single canonical control-plane contract
that normalizes user intent across chat, voice, automations, and CLI surfaces
before dispatch. Without that spine, each surface can evolve its own notion of
"run this", "approve this", or "schedule this", which creates drift in
identity, policy, provenance, and receipts.

This ADR defines the missing cross-surface contract without introducing a new
executor or a second command universe.

## Decision

Codexify defines a Guardian-owned **Intent Spine**.

The Intent Spine is the canonical control plane for user-initiated actions
across Codexify surfaces. Every first-class ingress surface must normalize its
request into a single canonical intent envelope before anything dispatches.

This ADR does not claim every listed surface is already wired in the live
runtime; it defines the contract those surfaces should share.

First-class ingress surfaces include:

- chat
- voice
- automations
- CLI / operator entrypoints
- future plugin surfaces that present user-facing action requests

The Intent Spine is not a new runtime. It is the normalization, policy, and
receipt contract that routes intent into existing runtime rails such as the
command bus, cron, delegation, coding-agent execution, or other approved
Guardian-owned surfaces.

## Canonical Terminology

The following terms are canonical and must be used consistently:

| Term | Canonical meaning |
|---|---|
| Intent Spine | The cross-surface control plane that normalizes user intent, applies policy, and routes to existing runtime rails. |
| Intent Envelope | The normalized request object that carries identity, surface, scope, policy, provenance, idempotency, and execution target. |
| Ingress Surface | A user-facing or operator-facing entrypoint such as chat, voice, automation, or CLI. |
| Dispatch Target | An existing runtime rail that executes the intent, such as the command bus, cron, delegation, or coding-agent execution. |
| Receipt | The durable record linking an intent to a dispatched run, rejection, no-op, or terminal outcome. |

Repeated contract-bearing values in this architecture must use canonical tokens
or registry-backed enumerations, not ad hoc literals.

## Contract Shape

The canonical intent envelope must be capable of carrying at least:

- `intent_id`
- `actor_id`
- `source_surface`
- `intent_kind`
- `target`
- `arguments`
- `scope`
- `policy`
- `provenance`
- `idempotency_key`
- `requested_at`
- `approval_state`
- `execution_state`
- `receipt_ref`

The envelope is Guardian-owned. Surfaces may propose intent, but they may not
rewrite the identity, scope, or policy that Guardian resolves.

## Contract Rules

### Ingress Rule

Every supported surface must normalize into the canonical intent envelope
before dispatch.

### Identity Rule

Guardian resolves identity once. A surface may contribute context, but it may
not claim authority over actor identity, request identity, or source lineage.

### Policy Rule

Policy, approval, and boundary checks happen before dispatch. Voice and other
high-friction surfaces do not get a privileged bypass.

### Idempotency Rule

Intent dispatch must be idempotent. Retries, reconnects, or repeated operator
gestures must not silently duplicate execution.

### Dispatch Rule

An intent should dispatch to one primary target unless the envelope explicitly
models fan-out. Fan-out should be exceptional and explicit.

### Receipt Rule

Every accepted or rejected intent must produce a durable receipt or rejection
record that preserves provenance and surface metadata.

### No Second Universe Rule

The Intent Spine must reuse existing execution rails and their receipts instead
of inventing a parallel command system.

## Surface Responsibilities

| Surface | Responsibility | Must not do |
|---|---|---|
| Chat | Capture explicit user intent and surface receipts | Directly execute privileged work without Guardian policy |
| Voice | Transcribe or confirm intent and hand it to Guardian | Bypass identity, approval, or idempotency checks |
| Automation | Materialize deferred or scheduled intent | Skip provenance or mutate scope silently |
| CLI / operator entrypoint | Provide deterministic, explicit intent creation | Invent ad hoc semantics outside the canonical envelope |
| Plugin surface | Produce bounded intent proposals | Own identity or dispatch outside Guardian control |

## Existing Runtime Rails

The Intent Spine may dispatch into existing rails, including:

- command bus invocation
- cron job creation or triggering
- delegation request or result handling
- coding-agent execution under Guardian ownership
- retrieval or browser-boundary actions where those are separately governed

The spine does not replace those rails. It standardizes how requests enter
them.

## Non-Goals

- No new executor runtime
- No new command universe
- No autonomous agent loop
- No bypass of Guardian policy enforcement
- No claim that all supported surfaces are live today
- No replacement of the command bus, cron, delegation, or coding-agent ADRs
- No UI redesign in this ADR

## Consequences

### Positive

- Chat, voice, automation, and CLI can share one request vocabulary
- Identity and policy stay explicit across surfaces
- Receipts become easier to reason about and audit
- Guardian remains the owner of dispatch and persistence boundaries
- Future surfaces can integrate by producing the same envelope

### Negative

- One more canonical contract must be maintained
- Existing surfaces may need adapter work to conform to the envelope
- The system still needs separate execution rails under the hood

## Open Questions

- Should the canonical durable entity be an intent, a request, or a receipt
  record
- Should fan-out be allowed in the first version of the envelope
- Should voice confirmations produce the same envelope shape as chat or a
  narrower variant
- Should operator actions and user actions share the exact same intent kinds or
  a typed subset

## Links

- [[ADR Index]]
- [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]]
- [[010-Self-Extending-Agent-Plugin-System|ADR-010 Self-Extending Agent Plugin System]]
- [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]]
- [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]]
- [[021-Web-Agent-Boundary-and-Retrieval-Contract|ADR-021 Web Agent Boundary and Retrieval Contract]]
- [[00-current-state]]
- [[system-overview|System Overview]]
- [[flows|Critical Flows]]
- [[command-bus-auth-cli-automations|Command Bus, Auth, Tool Calls, and Automations]]
- [[delegation-runtime|Delegation Runtime Contract]]
- [[persona-studio|Persona Studio Architecture]]
