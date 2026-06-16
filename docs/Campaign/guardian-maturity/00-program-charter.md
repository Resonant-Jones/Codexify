# Guardian Maturity Program Charter

## Classification

**Architecture-impacting.** This scaffold creates a governance surface for future architecture-impacting Guardian maturity work. It defines campaign boundaries, proof gates, release-boundary controls, and execution discipline. It does not alter runtime behavior.

- Classification: Aligned with existing ADR(s)
- Governing ADRs/contracts:
  - ADR-020: Guardian Mediated Coding Agent Execution Contract
  - ADR-022: Guardian Intent Spine and Cross-Surface Control Plane
  - Chat Runtime Contract
  - Agent Tool Loop Contract
  - Pi Invocation Boundary Contract
  - Config and Ops
  - Agent Protocol Operations Index
  - 00-current-state.md (release-truth authority)
- Brief reason:
  - This scaffold organizes future architecture-impacting Guardian maturity work into explicit campaign boundaries, proof gates, and release-boundary controls. It does not change accepted runtime semantics, but it creates the planning control plane that will govern such changes.

## Program Purpose

Turn the Guardian Experience Maturity work into an execution scaffold. Guardian's UI and operational experience lag behind Codexify's runtime architecture. This program organizes the gap-closing work into bounded, provable campaigns with explicit proof gates, dependency ordering, and release-boundary controls.

## Scope

This program owns:

- Campaign boundary definition (C00–C14)
- Proof gate design and enforcement
- Dependency graph and wave ordering
- Release-boundary documentation
- Campaign charter, proof pack, and decision log templates

This program does **not** own:

- Backend route implementation
- Frontend component implementation
- Database schema changes
- Provider behavior changes
- Worker orchestration changes
- Pi/Coder execution behavior
- Release support claims

## Non-Goals

- This program does not close the entire Guardian gap in one giant campaign.
- This program does not prove Pi/Coder execution, autonomous coding, or cloud-provider beta support.
- This program does not mutate memory, identity, persona ownership, runtime token semantics, queue semantics, or export/restore lineage.
- This program does not treat docs, contracts, scaffolds, prompts, or route presence as runtime proof.
- This program does not replace `00-current-state.md` as the release-truth authority.

## Current Truth Anchors

What is true now (per `00-current-state.md`, 2026-06-16):

- Codexify is in local-first beta hardening on `main`.
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Whoosh'd is a supported local runtime preset on Apple Silicon paths.
- Live model availability is proven only by inventory from `/v1/models` or `/api/tags`.
- Chat completion, upload → embed → readback, and workspace-local retrieval remain the supported beta paths.
- Guardian delegation and Pi/Coder execution are not release-supported.
- Graph writes remain default-off on the supported Compose path.

What is not yet true:

- Cloud-provider beta support is not claimed.
- Guardian delegation is not a release-supported path.
- Pi/Coder execution does not exist as a live runtime path.
- Recursive autonomous coding-agent behavior is not supported.
- UI triggerability for backend behavior is not assumed without backend proof.
- A single health endpoint does not prove runtime support.

## Invariants

The following invariants must be preserved across all campaigns:

1. **Do not widen release promises.** The release boundary defined in `00-current-state.md` is authoritative.
2. **Do not treat docs, contracts, route presence, or type presence as runtime proof.** Proof requires live supported-path evidence.
3. **Do not treat task acceptance as completion.** Queue enqueue ≠ execution ≠ UI receipt.
4. **Do not treat task-event publication as UI receipt.** Events may be published without being consumed.
5. **Do not conflate Pi/Coder harness execution with model/provider lanes.** Pi is an execution substrate; providers are inference providers.
6. **Do not bypass Guardian as policy, lineage, transcript, and result-return owner.** All coding-agent results must return through Guardian.
7. **Do not create a second shadow control plane.** The Command Center aggregates and presents truth — it does not create independent truth.
8. **Do not mutate identity, memory, persona ownership, runtime token semantics, queue semantics, or export/restore lineage** as a side effect of any campaign.

## Wave Summary

| Wave | Campaigns | Purpose |
|------|-----------|---------|
| 0 | C00, C11 | Establish truth baseline and audit API route surface |
| 1 | C01, C02 | Operator truth surface and correct chat runtime presentation |
| 2 | C03, C05, C06 | Governed coding delegation, tool observability, operator workspace |
| 3 | C04, C07, C08 | Pi/Coder invocation boundary, persona config, local runtime management |
| 4 | C09, C10 | Execution ledger, recovery and operator repair |
| 5 | C12, C13, C14 | Cross-cutting hardening: auth/session, SSE reliability, state management |

## Operator Outcome

When this program is complete, an operator should be able to:

1. Answer "Can I run?" from a single truth surface with evidence-linked verdicts.
2. Distinguish "model warming" from "provider offline" without reading code.
3. Inspect request lifecycle state per message (QUEUED, AWAITING_MODEL, AWAITING_FIRST_TOKEN, STREAMING, ORPHANED, REPLAYED).
4. Create a governed coding delegation draft with source lineage and explicit permissions.
5. Inspect a Pi/Coder invocation envelope before execution.
6. Observe tool-turn state, command run results, and loop stop reasons.
7. Use a persistent operator workspace (scratchpad, shelf, inspector).
8. Inspect active profile configuration, tool permissions, and retrieval policy.
9. Verify local runtime model inventory and readiness.
10. Review execution ledger rows with proof artifacts for every delegation.
11. Diagnose why work is stuck and perform safe recovery actions.

## Proof Philosophy

- **Health alone is not enough.** Multiple surfaces must agree.
- **Route presence is not runtime proof.** A registered route may not be wired.
- **UI presence is not execution proof.** A button may have no backend.
- **Task acceptance is not completion.** Queue, worker, provider, and persistence are separate layers.
- **Event publication is not UI receipt.** SSE events may be dropped or delayed.
- **Docs-only scaffold is not release support.** Planning documents prove intent, not capability.

Proof categories:

- **Docs proof**: Documentation is complete, consistent, and follows conventions.
- **Backend seam proof**: API routes exist and return structured, validated responses.
- **Frontend UI proof**: UI components render correctly and display truthful data.
- **Live supported-path proof**: Behavior is verifiable on the supported local Compose path.
- **Operator usability proof**: An operator can answer key questions without log spelunking.
