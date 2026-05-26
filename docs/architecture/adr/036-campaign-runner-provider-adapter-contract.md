---
tags:
* architecture
* adr
* campaign-runner
* provider-adapter
  aliases:
* ADR-036
* Campaign Runner Provider Adapter Contract
---

# ADR-036: Campaign Runner Provider Adapter Contract

## Title

Campaign Runner Provider Adapter Contract

## Status

Proposed

## Date

2026-05-26

## Context

Campaign Runner currently spans Guardian-mediated coding execution, the
codex_runner substrate, runtime container images, and operator-facing docs.
Prior iterations left direct Codex and Claude/Claude Code coupling in adapter
registries, shell-out paths, TUI choices, Docker image installs, and Compose
runtime wiring. That coupling makes the module non-truthful about its real
execution seam, broadens dependency posture unnecessarily, and encourages
provider-specific branching inside core orchestration.

Guardian must remain the owner of execution policy, lineage, result return, and
auditability. Campaign Runner core should select adapters by declared contract,
not by shell binary presence or hidden provider-specific branching.

## Decision

Campaign Runner uses provider adapters rather than hardcoded provider
assumptions, and this module forbids direct Codex/Claude dependency coupling.

- Campaign Runner core selects a declared adapter contract.
- Pi is the preferred direct broker adapter for this module.
- Direct Codex/Claude adapter kinds are unsupported.
- Backend receipts are mandatory wherever brokered provider execution is
  claimed.
- Downstream provider/model identity must come from backend receipts, not
  runner-native branching.

## Consequences

### Positive

- removes direct Codex/Claude binary dependency from Campaign Runner
- keeps provider/model routing behind a bounded adapter seam
- narrows runtime image and Compose coupling
- makes operator proof depend on receipts rather than CLI assumptions

### Tradeoffs

- legacy direct-provider requests now fail closed
- compatibility naming such as `pi_codex_runner` may remain temporarily
- operators must inspect receipts for downstream provider/model identity

## Non-goals

- Pi SDK implementation work
- global provider registry redesign
- chat completion runtime changes outside Campaign Runner
- Tauri IPC changes
- cloud-provider support widening

## Rationale

Provider-specific runner logic in core orchestration encourages silent coupling,
ambiguous failure modes, and misleading release claims. A direct adapter
contract keeps Campaign Runner core small: lifecycle, schema validation,
artifacts, git safety, and receipts stay in core; prompt execution, backend
invocation, retry/fallback behavior, and resolved provider/model identity stay
behind the adapter boundary.

## Dependency posture

- no hard dependency on Codex
- no hard dependency on Claude
- no required Codex CLI binary for Campaign Runner
- no required Claude CLI binary for Campaign Runner
- no global install of Codex/Claude CLI packages for Campaign Runner images
- no provider-specific runner logic in the core orchestration layer

## Rejected alternatives

- hard dependency on Codex
- hard dependency on Claude
- required Codex CLI binary for Campaign Runner
- required Claude CLI binary for Campaign Runner
- global install of Codex/Claude CLI packages for Campaign Runner images
- provider-specific runner logic in the core orchestration layer
- silent provider fallback
- treating provider identity as implicit runtime truth
- treating Pi as a model instead of a broker adapter

## Validation / proof expectations

- code-path proof that direct `codex` / `claudecode` adapter kinds are absent or rejected
- code-path proof that runner/TUI provider choices no longer expose direct `codex` / `claude`
- Dockerfile and Compose proof that Campaign Runner no longer depends on direct Codex/Claude binaries
- backend receipt evidence for any Pi-brokered execution claim

## Documentation follow-through

- `docs/specs/campaign-runner/PROVIDER_ADAPTER_CONTRACT.md`
- `docs/specs/campaign-runner/PI_ADAPTER_CONTRACT.md`
- `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`
- `docs/architecture/guardian-build-loop-doctrine.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md`
