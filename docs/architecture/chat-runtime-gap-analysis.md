# Chat Runtime Gap Analysis

Purpose: Capture the gap between the current runtime KB and the chat runtime contracts so frontend/shared-runtime readers can reason about slow local-model startup, transport visibility loss, timeout ambiguity, provider-state misclassification, replay ambiguity, and transcript integrity without treating the companion docs as the normative spec.
Last updated: 2026-03-29
Source anchors:
- docs/architecture/flows.md
- docs/architecture/completion_pipeline.md
- docs/architecture/tech-debt-and-risks.md
- docs/architecture/00-current-state.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/adr/038-chat-transport-visibility-and-adaptive-stream-recovery-contract.md

## Purpose

This document captures the gap between the current runtime KB and the chat runtime contracts at `docs/architecture/chat-runtime-contract.md` and `docs/architecture/adr/038-chat-transport-visibility-and-adaptive-stream-recovery-contract.md`.

The contracts are the normative sources for request, provider, and transport-visibility vocabulary. This companion explains why those contracts were needed, what the current docs already proved, and which ambiguity classes they are meant to shrink. The focus is the current ambiguity window around slow local-model startup, transport visibility loss, timeout interpretation, provider-state misclassification, replay ambiguity, and transcript integrity.

## Problem Statement

Current architecture docs already establish that route acceptance does not prove completion, task-event publication does not prove UI receipt, and Redis-backed coordination plus worker state must be read together to understand chat health. That still leaves a bug class around slow local inference startup.

When a large local model is cold or the network is unstable:
- the backend/runtime may still be reachable while slow to produce first visible progress
- the visible stream may stall even though the request is still running
- the UI may classify that interval too early as offline or failed
- the request may still be running, may have been dropped visually, or may later appear to have been answered only after a subsequent send

Working theory, not yet a single proven root cause: current provider/runtime/request semantics were coarse enough that warmup, first-token wait, dropped work, stream loss, and replay could collapse into one ambiguous operator story. That ambiguity matters because a later visible assistant turn can be hard to bind confidently to the correct user message or attempt, which is a transcript-integrity problem rather than a cosmetic status-label problem.

## What the Current Docs Already Establish

- `docs/architecture/flows.md` and `docs/architecture/completion_pipeline.md` already establish that acceptance is not completion.
- Those same docs already establish that task-event publication is not UI receipt.
- `docs/architecture/tech-debt-and-risks.md` already treats operator truth as multi-surface rather than single-endpoint truth.
- The current runtime docs already describe Redis as an operational coordination point for queueing, locks, task-event streams, heartbeat, cancellation, and turn anchors.
- `docs/architecture/runtime-protocol-token-contract.md` already establishes the broader KB rule that repeated runtime meanings should become canonical tokens rather than ad hoc literals.

## What Was Missing Before the Contract

Before the new contract, the KB still lacked a formal shared-runtime vocabulary for this ambiguity class:

- no canonical provider warmup state
- no formal request lifecycle states such as `AWAITING_MODEL`, `AWAITING_FIRST_TOKEN`, `ORPHANED`, or `REPLAYED`
- no formal transport-visibility states such as `CONNECTED`, `SUSPECTED_STALLED`, `RECOVERING`, `RECOVERED`, or `FAILED`
- no formal separation between stable `messageId` and per-attempt `requestId`
- no UI-facing rule for distinguishing reachable-but-slow from truly offline
- no explicit replay semantics for unresolved requests
- no explicit contract that stream recovery preserves transcript integrity instead of replaying the turn

The result was that the KB could describe queue and visibility boundaries, but not yet classify ambiguous chat-runtime behavior precisely enough for frontend/shared-runtime interpretation.

## What the Contracts Add

The normative sources for these semantics are `docs/architecture/chat-runtime-contract.md` and `docs/architecture/adr/038-chat-transport-visibility-and-adaptive-stream-recovery-contract.md`. This companion does not restate the full state machine. It summarizes the additions that matter to the rest of the KB:

- canonical provider runtime states, including warmup-aware semantics
- canonical request lifecycle states
- canonical transport visibility states
- an explicit message-versus-attempt identity split
- UI status mapping for frontend/shared-runtime interpretation
- transition rules for moving between request and provider states
- anti-ghost-turn behavioral rules intended to preserve transcript integrity when requests are unresolved, orphaned, replayed, stalled, or recovered
- recovery boundaries that treat transport repair as observation repair, not request replay
- future follow-up specs for TTFT tuning, stall timers, keepalives, and reconnect behavior

## Immediate Follow-on Documentation Updates

The following architecture docs are updated in this same task so the KB reflects the new contract without pretending the runtime implementation is already complete:

- `docs/architecture/flows.md`: adds the conceptual split between provider runtime state, request execution state, and lifecycle visibility state, then points readers to the normative contract vocabulary
- `docs/architecture/completion_pipeline.md`: ties the existing acceptance-versus-execution-versus-terminal-visibility distinctions to the new frontend/shared-runtime contracts
- `docs/architecture/tech-debt-and-risks.md`: records the remaining ambiguity class this contract is meant to reduce and keeps implementation proof as an open requirement
- `docs/architecture/00-current-state.md`: notes that the documentation layer now has chat runtime and transport-visibility contracts without turning that into a live-runtime release claim

## Non-Goals

- no backend protocol redesign in this pass
- no queue architecture rewrite
- no provider catalog overhaul
- no new release claims
- no runtime implementation guarantee beyond documentation alignment

## Exit Criteria

- contract and companion doc exist
- runtime docs now reference the new lifecycle and transport-visibility vocabulary
- offline-versus-warmup ambiguity is documented
- stalled-stream-versus-backend-failure ambiguity is documented
- replay ambiguity is documented
- scope remains documentation-only
