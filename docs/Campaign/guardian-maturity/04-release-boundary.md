# Release Boundary

## Purpose

Explicitly state what the Guardian Maturity Program does **not** prove, support, or claim as release-ready. This document is a negative-space contract: it defines the boundary between planning intent and release promise.

## Authority

[`docs/architecture/00-current-state.md`](../../architecture/00-current-state.md) is the canonical short-form source of truth for release readiness. If this document conflicts with `00-current-state.md` on any release claim, `00-current-state.md` wins.

This scaffold is planning structure only. None of the campaigns, charters, proof packs, or templates in this program constitute a release promise.

## Explicit Denials

The Guardian Maturity Program does **not** prove or claim:

### Execution and Autonomy

- **Pi/Coder live execution support.** The Pi Invocation Boundary Contract defines a validation-only backend seam. Live Pi SDK calls, runtime dispatch, and autonomous execution are not part of this program's scope and are not release-supported.
- **Autonomous recursive coding-agent behavior.** The bounded tool-turn contract permits exactly one tool turn per completion. This program does not introduce recursive agent loops, planner loops, or multi-turn autonomous execution.
- **Unreviewed coding delegation execution.** C03 creates governed delegation drafts with explicit permissions. Execution without human review is explicitly out of scope.

### Provider and Runtime

- **Cloud-provider beta support.** The supported posture remains local-only (`LLM_PROVIDER=local`, `ALLOW_CLOUD_PROVIDERS=false`). Cloud-capable configuration flags do not constitute provider support.
- **Whoosh'd live reachability without model inventory proof.** Local runtime preset configuration does not prove model availability. Live inventory evidence (`/v1/models` or equivalent) is required.
- **Provider readiness from configuration alone.** A configured API key or base URL does not prove provider reachability, model warmth, or execution capability.

### UI and Surface

- **UI-triggerability without backend proof.** A UI button, component, or panel does not prove the corresponding backend behavior exists. Every UI affordance must be verified against a live backend route.
- **Release readiness from docs-only planning.** Planning documents, charters, and proof pack templates prove intent, not capability. Live supported-path evidence is required for any release claim.

### Platform and Infrastructure

- **Graph-write release support.** Graph writes remain default-off on the supported Compose path.
- **Federation release support.** Federation remains high-blast-radius and trust-policy sensitive.
- **Packaged desktop shell as the supported path.** Local Docker Compose remains the supported install path.

### Planning and Governance

- **This scaffold as a release artifact.** The planning scaffold documents what needs to be done, not what has been done. Campaign completion is tracked per campaign, not at the scaffold level.
- **Governing authority over ADRs.** ADRs remain the authoritative architectural decision record. This scaffold organizes around them but does not override them.

## Current Supported Reality

Per `00-current-state.md` (2026-06-16):

- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload → embed → readback, and workspace-local retrieval are in the supported claim set.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.

## Boundary Enforcement

When any campaign in this program approaches a release claim:

1. Verify the claim against `00-current-state.md`.
2. If the claim is not in the supported set, it must be explicitly denied here.
3. If the claim would widen the release promise, stop and escalate.
4. Live supported-path proof is the minimum bar for any release-adjacent claim.

## Interpretation Rule

When in doubt, fail closed. A surface, route, or behavior that has not been proven on the supported path is not release-supported, regardless of its presence in docs, code, or UI.
