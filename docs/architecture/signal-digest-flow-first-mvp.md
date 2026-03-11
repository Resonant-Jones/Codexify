Purpose: Record the architecture decision to ship Signal Digest as a Flow-first MVP that proves the end-to-end loop on existing Codexify runtime rails before introducing a first-class backend domain.
Last updated: 2026-03-11
Source anchors:
- docs/architecture/flows.md
- guardian/routes/flows.py
- guardian/flows/spec.py
- guardian/flows/compiler.py
- guardian/flows/runner.py
- guardian/flows/primitives.py
- guardian/cron/scheduler.py
- guardian/cron/executor.py
- guardian/workers/cron_worker.py
- guardian/routes/channels.py
- guardian/channels/adapters/slack.py
- guardian/core/research/Modules/browser/crawl_ai.py

# Signal Digest Flow-First MVP

## Core Decision

Signal Digest MVP will be implemented primarily through the existing Flow builder/orchestration surface.

This MVP does not introduce a first-class backend Signal Digest domain yet. In this phase, do not add a fully normalized `guardian/signal_digest/` subsystem, dedicated profile or source models, dedicated run or delivery tables, or a new CRUD API surface for Signal Digest.

The MVP goal is to validate orchestration, ranking quality, and digest usefulness, not to establish a permanent Signal Digest storage or API surface.

The point of this slice is to prove the end-to-end loop quickly by reusing existing Codexify runtime rails where they already exist: Flow orchestration, cron scheduling, worker execution, provider routing, and existing persistence surfaces.

## MVP Flow Shape

The MVP flow is:

1. Scheduled or manual trigger
2. Source fetch from `reddit` and `google_news` only
3. Normalization into a shared candidate shape
4. Full-content read attempt where possible
5. LLM relevance scoring against a user profile
6. Ranking and thresholding
7. Digest composition
8. Delivery to one channel first

The first delivery channel remains explicitly undecided in this ADR. Current inspection confirms existing channel paths, but it does not yet prove a lowest-friction Flow-native delivery path, so choosing the first channel here would overstate certainty.

## What Lives In The Flow Layer For MVP

For the MVP, the Flow layer owns:

- Scheduling trigger
- Source calls
- Fan-out over candidate items
- Structured scoring prompts
- Ranking and filtering logic that can be expressed in Flow steps
- Digest composition
- Delivery orchestration in Flow, using an existing channel path where already supported, or a thin helper where current Flow primitives do not yet expose delivery directly.

This keeps the experiment centered on orchestration rather than on building a permanent backend product surface too early.

## Allowed Thin Backend Helpers Only

Only the following helper primitives are allowed for the MVP, and only if the existing Flow builder/runtime cannot reliably cover the need:

- Candidate normalization helper, only if Flow nodes cannot provide a stable shared schema
- Full-content extraction helper, only if existing Flow-accessible tools cannot reliably read article content
- Run lock or idempotency helper, only if needed to prevent duplicate scheduled sends
- Persisted run artifact helper, only if existing Flow execution history is insufficient

These helpers are thin primitives, not a new Signal Digest subsystem. They exist only to unblock the Flow-first MVP where the current Flow surface is too thin or too unstable to express the required step directly.

## Explicit Deferrals

The following are intentionally deferred to a later phase:

- Normalized tables for run items and deliveries
- Fuzzy-title dedupe
- Novelty scoring against prior delivered history
- Multi-channel delivery hardening
- A new full backend CRUD surface for profiles, sources, and runs
- A new scheduler subsystem
- Any new secret-management abstraction unless already proven necessary by existing infrastructure

These are not omissions by accident. They are deferred by design so the MVP can answer whether the digest is useful before Codexify commits to a permanent backend shape.

## Implementation Boundary

- Reuse existing Codexify cron, worker, provider-routing, and persistence rails where possible.
- Prefer configuration and orchestration over new backend models.
- Only promote Signal Digest into a first-class backend domain after the Flow-first MVP proves value and exposes stable requirements.

This boundary is intentional. Signal Digest should earn a dedicated storage and API surface only after the Flow-first MVP shows that the orchestration loop, ranking quality, and digest output are worth hardening into product infrastructure.

## MVP Acceptance

The MVP is successful when it can demonstrate all of the following:

- One profile
- `reddit` plus `google_news`
- One delivery channel
- Scheduled or manual execution
- Full-content read attempt with snippet fallback
- A fresh top-ranked digest artifact produced successfully even if one source partially fails

The acceptance target is end-to-end usefulness, not backend completeness.

## Next Implementation Task

The next engineering task after this ADR should be:

1. Inspect the current Flow builder and runtime surfaces
2. Map which steps are already possible with no code
3. Identify the minimum missing helper primitive, if any
4. Avoid writing the full backend domain unless that inspection proves it necessary

## Validation

No automated tests apply.
