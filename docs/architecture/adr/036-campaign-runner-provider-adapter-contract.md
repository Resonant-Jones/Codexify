# ADR-036 Campaign Runner Provider Adapter Contract

- Status: Proposed
- Date: 2026-05-25

## Title

Campaign Runner uses provider adapters rather than hardcoded provider assumptions, and this module forbids direct Codex/Claude dependency coupling.

## Context

Campaign Runner and Guardian-owned coding-agent execution accumulated direct Codex/Claude coupling across adapter kinds, shell-out adapters, runner provider branching, TUI provider choices, and runtime configuration. That posture made Campaign Runner core aware of direct provider binaries and encouraged contributor setup assumptions that are outside the desired provider-agnostic architecture.

ADR-020 already establishes Guardian-owned execution contracts. ADR-028 establishes Execution Ledger / Campaign Runner seams. This ADR narrows the provider posture so Campaign Runner core remains orchestration-first while adapters remain replaceable integrations.

## Decision

Campaign Runner will depend on provider adapters rather than hardcoded provider assumptions.

- runner core, adapter, broker, and provider are explicit separate roles
- adapters are replaceable integrations
- backend receipts are required for provider transparency wherever brokered execution is claimed
- direct Codex/Claude binaries are not Campaign Runner dependencies
- Codex/Claude may appear only as downstream resolved provider/model identities through a broker adapter such as Pi

## Consequences

- Campaign Runner core stops treating direct Codex/Claude execution as a supported runtime path
- adapter registration and worker routing must fail closed on legacy direct adapter kinds
- TUI and CLI provider choice must reflect broker-first posture
- runtime docs and operations guidance must stop requiring direct Codex/Claude binaries for this module

## Non-goals

- making Pi globally mandatory for all Codexify execution
- redesigning the global provider registry
- changing chat runtime semantics outside the coding-agent/Campaign Runner seam
- proving live Pi receipt coverage on every current path

## Rationale

- Provider-agnostic core semantics are easier to reason about and audit.
- Broker adapters preserve provider plurality without teaching runner core how to launch each provider.
- Backend receipts are necessary to preserve transparency when a broker may resolve different downstream providers/models.
- Removing direct CLI assumptions lowers contributor setup burden and runtime image complexity.

## Dependency posture

- no hard dependency on Codex
- no hard dependency on Claude
- no required Codex CLI binary for Campaign Runner
- no required Claude CLI binary for Campaign Runner
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

- runtime surfaces reject direct `codex` / `claude` / `claudecode` execution for this module
- broker-first provider choices are visible in CLI and TUI surfaces
- runtime images stop installing direct Codex/Claude CLIs for this module
- Compose wiring stops requiring direct Codex/Claude binary env vars for coding-worker paths
- docs and ADRs align with current supported local-first truth without widening release promises

## Documentation follow-through

- create `docs/specs/campaign-runner/PROVIDER_ADAPTER_CONTRACT.md`
- create `docs/specs/campaign-runner/PI_ADAPTER_CONTRACT.md`
- create ADR-037 for Pi broker posture
- update runbook and architecture doctrine notes that previously treated direct Codex/Claude adapters as supported runtime choices
