## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-08

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. `main` is stable at the current release-truth point; the last week added no new shipped runtime surface that changes the supported beta story.

## What changed recently
- No material `main`line changes since the prior weekly audit.
- The release-truth docs and operator routing stayed stable.
- Docs-only contracts remain docs-only; no new runtime proof landed on `main`.
- `main` now includes internal command-bus exposure for the Guardian Codex Runner JSON preflight adapter; it does not add a UI, new API route, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- `main` now includes a controlled operator-proof packet for the Guardian Codex Runner command-bus bridge; it validates command-bus lifecycle wiring and boundary preservation only, and it does not prove live Codex Runner execution, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a live validate-only proof packet for the Guardian Codex Runner command-bus bridge; it does not prove live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a retry live validate-only proof packet for the Guardian Codex Runner command-bus bridge; it does not prove live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds an opt-in local Docker container visibility contract for the Guardian Codex Runner bridge; it exists to address the failed live validate retry proof where the backend container could not see `/Volumes/Dev_SSD/Codex-Runner`; it does not prove live validation, live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a mounted validate-only live proof packet for the Guardian Codex Runner command-bus bridge; it uses the opt-in read-only Codex Runner mount; it does not prove live validation, live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds an opt-in executable availability seam for the Guardian Codex Runner bridge; it addresses the mounted proof failure where `codexrun` was not on container PATH; it does not prove live validation, live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a module validate-only live proof packet for the Guardian Codex Runner command-bus bridge; it does not prove live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds an orchestration receipt prerequisite contract for the Guardian Codex Runner command-bus bridge; it follows the validate-only module live proof PASS and defines receipt requirements for future dry-run orchestration proof; it does not prove live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a validation receipt availability proof for the Guardian Codex Runner command-bus bridge; it follows the orchestration receipt prerequisite contract; it does not prove live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a selected validation receipt proof for the Guardian Codex Runner command-bus bridge; it follows the validation receipt availability proof BLOCKED result; it does not prove live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation beyond command-bus run/event records.
- this branch adds a live dry-run orchestration proof packet for the Guardian Codex Runner command-bus bridge; it follows selected validation receipt proof SELECTED_AVAILABLE; it does not prove UI integration, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, WorkOrder mutation, Execution Ledger writes, or durable mutation beyond command-bus run/event records.
- this branch adds a local-auth override contract for the opt-in Guardian Codex Runner bridge compose profile; it normalizes the compose auth variance; it does not prove UI integration, remote deployment support, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, WorkOrder mutation, Execution Ledger writes, or durable mutation beyond command-bus run/event records.
- this branch adds a proof-chain index for the Guardian Codex Runner bridge; the index summarizes the validated preflight proof chain through command bus; it does not prove UI integration, remote deployment support, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, WorkOrder mutation, Execution Ledger writes, or durable mutation beyond command-bus run/event records.
- this branch adds a Guardian Evidence Packet and Reducer Profile contract; the contract defines how future Guardian-facing evidence summaries may reduce proof chains, command runs, receipts, and validation output; this does not implement runtime reducer behavior, persistence, UI, dev-build buttons, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a static GuardianEvidencePacket example fixture for the Guardian Codex Runner bridge proof chain; this demonstrates evidence reduction shape only; this does not implement runtime reducer behavior, persistence, UI, dev-build buttons, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- `main` now includes a backend contract-only module for the Guardian Codex Runner preflight bridge; it does not implement adapter execution, routes, UI, Pi Loop invocation, Codexify ingestion, or durable mutation.
- A docs-only Codexify-side Guardian/Codex Runner preflight bridge contract now exists in `docs/architecture/guardian-codex-runner-preflight-bridge-contract.md`; it does not add shipped runtime behavior, UI integration, a backend command adapter, Pi Loop invocation, or Codexify ingestion.
- this branch adds a static GuardianEvidencePacket example fixture for the Guardian Codex Runner bridge proof chain; this demonstrates evidence reduction shape only; this does not implement runtime reducer behavior, persistence, UI, dev-build buttons, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a Guardian Evidence Packet static validator contract; this defines future packet shape and guardrail validation only; this does not implement runtime validator behavior, runtime reducer behavior, persistence, UI, dev-build buttons, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Packet static validator script; the script validates packet shape and guardrail presence only; this does not implement runtime reducer behavior, persistence, UI, dev-build buttons, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Packet batch validator script; the script validates all current packet fixtures for shape and guardrail presence only; this does not implement runtime reducer behavior, persistence, UI, dev-build buttons, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Makefile entrypoint, `guardian-evidence-packets-validate`, for validating current Guardian Evidence Packet fixtures for shape and guardrail presence only; this does not implement runtime reducer behavior, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a Guardian Evidence Packet authoring template and guide to support future static packet authoring and validation; this does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a second GuardianEvidencePacket fixture for the local validation toolchain; this demonstrates the packet schema beyond the bridge proof-chain domain and does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a Guardian Evidence Packet future runtime reducer design contract; the contract defines future reducer boundaries and allowed handoffs only and does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a pure Guardian Evidence Packet backend contract package; the package defines code-level constants and pure shape helpers for future reducer work and does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch aligns local Guardian Evidence Packet validators to the pure backend contract package; this prevents packet literal drift between local tooling and future reducer work and does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds pure Guardian Evidence Packet reducer interface contracts; the package defines code-level input/output classes, lifecycle constants, and pure helpers for future reducer work and does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a pure Guardian Evidence Packet reducer dry-run skeleton; the skeleton returns diagnostics only and does not produce packets or implement runtime reducer behavior, packet generation, validation behavior, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Packet reducer dry-run CLI; the CLI returns diagnostics only and does not produce packets or validation results, and does not implement runtime reducer behavior, packet generation, validation behavior, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Packet reducer dry-run CLI Makefile target; the target returns diagnostics only and does not produce packets or validation results; this does not implement runtime reducer behavior, packet generation, validation behavior, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a static Guardian Evidence Reducer input bundle template and local tooling fixture; these define future reducer input shape only and do not implement runtime reducer behavior, input-bundle loading, packet generation, validation behavior, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a Guardian Evidence Reducer input-bundle static validator contract; the contract defines future shape and guardrail validation rules for input-bundle templates and fixtures only; this does not implement input-bundle validation, input-bundle loading, runtime reducer behavior, packet generation, validation behavior, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Reducer input-bundle static validator script; the script validates bundle shape and guardrails only and does not read source_ref targets; this does not implement input-bundle loading, runtime reducer behavior, packet generation, validation behavior beyond local static bundle validation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Reducer input-bundle batch validator script; the script validates known input-bundle templates and fixtures for shape and guardrails only and does not read source_ref targets; this does not implement input-bundle loading, runtime reducer behavior, packet generation, validation behavior beyond local static bundle validation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Make target for Guardian Evidence Reducer input-bundle batch validation; the target validates known input-bundle templates and fixtures for shape and guardrails only and does not read source_ref targets; this does not implement input-bundle loading, runtime reducer behavior, packet generation, validation behavior beyond local static bundle validation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- Continuity remains quarantined behind `test-continuity`.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` is legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- OpenAI export import and Task Prompt Archive are present on `main`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface is test-only, API-key-gated, and profile-quarantined under `test-continuity`.
- Shared Presence, chat transport recovery, and thread lenses are docs-only contracts, not supported runtime surfaces.
- `main` currently matches the prior release-readiness state; no new supported surface was added this week.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts mean shipped runtime support.
- Do not assume the Turn Intake fixture projection means a live classifier, router, or prompt builder exists.
- Do not assume shared presence, chat transport recovery, or thread lenses are shipped runtime behavior.
- Do not assume the collab chat identity contract or personal-facts guardrails are release-proven runtime behavior from docs alone.
- Do not assume chat transport visibility or adaptive stream recovery semantics are already emitted as live runtime behavior from docs alone.
- Do not assume Scout/iOS contract docs mean shipped Scout runtime support.
- Do not assume the Turn Intake Compiler contract means a live runtime intake classifier, action router, retrieval-router integration, or model-prompt packet builder is implemented.
- Do not assume the Turn Intake Fixture Pack means executable tests exist.
- Do not assume the Turn Intake Token Domain Proposal means turn-intake runtime tokens, registries, or classifier behavior exist.
- Do not assume the Turn Intake machine-readable fixture projection means a runtime classifier, executable test harness, token registry, prompt packet builder, retrieval-router integration, or action-gate integration exists.
- Do not assume command bus, delegation, federation, or graph-write surfaces are part of the present release promise.
- Do not assume Thread Lenses exist as a shipped runtime organization surface; any Thread Lens language is docs-only and must not be read as project-membership mutation or supported beta behavior.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not infer a wider release promise from docs-only onboarding, scaffolds, or audit artifacts.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not assume hosted rooms, participant node attachment, Shared Room KB, or cross-node document handoff are implemented from the Hosted Room and Sovereign Node Participation Contract; that contract is future docs-only architecture and does not widen the supported beta release surface.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- The new turn-intake docs are guidance only; the runtime classifier/intake pipeline and machine-readable projection are still not release-proven.
- No new blocker was introduced by this week's mainline state.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep docs-only contracts clearly separated from shipped runtime claims.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Recheck blocker status only when `main` moves.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] OpenAI export import and Task Prompt Archive are documented as present on `main`.
- [x] The Zac Mac Studio bring-up path is documented without widening the release promise.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.
- [ ] New docs-only contracts must stay out of the supported runtime claim set until proven on `main`.
- [ ] Any new release claim needs fresh proof on `main`, not branch-local evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
