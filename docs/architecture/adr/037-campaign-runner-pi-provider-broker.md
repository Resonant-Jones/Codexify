---
tags:
* architecture
* adr
* campaign-runner
* pi
* broker
  aliases:
* ADR-037
* Campaign Runner Pi Provider Broker
---

# ADR-037: Campaign Runner Pi Provider Broker

## Title

Campaign Runner Pi Provider Broker

## Status

Proposed

## Date

2026-05-26

## Context

Campaign Runner needs a lightweight execution seam that avoids direct Codex and
Claude CLI coupling while preserving Guardian ownership of policy, lineage, and
result return. Pi already exists in repo-adjacent runtime seams as a bounded
invocation contract, but Campaign Runner needs an explicit statement that Pi is
the preferred broker adapter for this module when available.

Without that statement, old naming and runtime residue can be misread as
provider-native execution truth.

## Decision

Pi is the preferred lightweight provider-broker adapter for Campaign Runner
when available.

- Campaign Runner treats Pi as a broker adapter, not a model.
- Pi route selection remains explicit.
- Resolved provider/model identity must be surfaced through Pi backend receipts.
- Direct Codex/Claude CLI execution is unsupported for Campaign Runner.

## Consequences

### Positive

- narrows dependency footprint
- keeps provider/model routing behind a broker seam
- preserves adapter plurality at the architecture level
- gives operators a receipt-backed proof surface

### Tradeoffs

- Pi-specific route metadata becomes part of Campaign Runner evidence
- some legacy naming may remain temporarily for compatibility
- Pi unavailability now becomes a first-class failure mode for this module

## Non-goals

- requiring Pi globally for all Codexify execution
- treating Pi as a model
- treating Pi as ResonantOS runtime
- making Campaign Runner depend on Pi internals
- replacing provider adapter plurality with a single broker monopoly

## Rationale

Pi is the smallest change that removes direct Codex/Claude runtime coupling
without forcing Campaign Runner core to absorb provider-specific logic. The
broker seam preserves explicit receipts, explicit fallback reporting, and an
auditable route boundary while keeping Guardian as the authority owner.

## Dependency posture

- Campaign Runner should not install Codex/Claude CLIs for this module
- Campaign Runner should not require Codex/Claude binaries on PATH
- Compose/runtime images should expose Pi-broker configuration rather than direct provider binary env vars

## Rejected alternatives

- requiring Pi globally for all Codexify execution
- treating Pi as a model
- treating Pi as ResonantOS runtime
- making Campaign Runner depend on Pi internals
- replacing provider adapter plurality with a single broker monopoly
- direct Codex binary execution in Campaign Runner
- direct Claude binary execution in Campaign Runner
- Docker/runtime image installs of Codex/Claude CLIs for this module

## Validation / proof expectations

- Campaign Runner direct adapter registry exposes Pi broker path, not direct Codex/Claude support
- Pi-backed execution stores backend receipts with resolved provider/model identity
- Dockerfile and Compose wiring show Pi posture and no direct Codex/Claude binary coupling for this module
- documentation and TUI/CLI surfaces present Pi as the direct module seam

## Documentation follow-through

- `docs/specs/campaign-runner/PI_ADAPTER_CONTRACT.md`
- `docs/specs/campaign-runner/PROVIDER_ADAPTER_CONTRACT.md`
- `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`
- `docs/architecture/guardian-build-loop-doctrine.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md`
