## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-10

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. `main` is absorbing Guardian Codex Runner bridge proof and contract work, not expanding the supported beta runtime surface.

## Current canonical authority decision
- VaultNode has been selected as the canonical runtime and audit authority.
- GitHub `main` remains the canonical code authority for accepted code, documentation, schemas, and contracts.
- Existing audit artifacts from other machines remain historical or provisional until revalidated on VaultNode.
- Canonical evidence automation and trusted `latest` promotion are not implemented yet.
- The current campaign remains in `NEXT_PROOF_NEEDED` posture until exact-head VaultNode proof exists.

## Phase 2 canonical evidence model

- ADR-042 and `schemas/audit/canonical-audit-evidence.schema.json` now define the intended canonical audit evidence model.
- A test-backed repository-local canonical evidence validator now validates one manifest's schema, bounded semantics, artifact hashes, and eligibility; it is local tooling, not runtime proof.
- Canonical audit producers and consumers have not yet been migrated, and trusted `latest` promotion remains unimplemented.
- A bounded repository-local identity collector now observes machine and Git identity; it is not runtime proof, does not establish VaultNode authority from hostname, and does not produce or promote canonical evidence. Historical artifacts are not automatically canonical.
- Existing artifacts remain historical or provisional until revalidated under the new model.
- Campaign posture remains `HOLD / NEXT_PROOF_NEEDED`; the next implementation slice is VaultNode evidence identity collection or schema-validation integration, not feature expansion.

## What changed recently
- `main` added Guardian bridge proof and contract work for selected validation receipt, validation receipt availability, orchestration receipt prerequisite, and module live-validate coverage.
- `main` added a mounted live-validate proof packet plus an opt-in container visibility contract.
- `main` added an executable-availability seam for the bridge when `codexrun` is not on container PATH.
- `main` added backend bridge contracts and a JSON adapter for the Guardian Codex Runner seam.
- `main` did not add a new supported install path or widen the beta release promise.
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
- this branch adds a docs-only Guardian Evidence Reducer input-bundle dry-run loader contract; the contract defines a future seam only; this does not implement input-bundle loading, runtime reducer behavior, packet generation, validation behavior beyond existing local static bundle validation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Guardian Evidence Reducer dry-run input-bundle loader; the loader validates a bundle JSON file, maps metadata only, and runs diagnostics-only dry-run; it does not read source_ref targets and does not produce packets or validation results; this does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Make target for Guardian Evidence Reducer dry-run input-bundle diagnostics; the target validates a bundle JSON file, maps metadata only, and runs diagnostics-only dry-run; it does not read source_ref targets and does not produce packets or validation results; this does not implement runtime reducer behavior, packet generation, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Make target for diagnostics-only reducer dry-run inspection of a checked-in GuardianEvidencePacket fixture; it does not implement runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a docs-only Guardian Evidence Packet generator contract; the contract defines a future packet-generation seam only; this does not implement packet generation, runtime reducer behavior, source_ref reading, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a docs-only Guardian Evidence bounded read contract; the contract defines a future evidence-read seam only; this does not implement source_ref reading, packet generation, runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds local Guardian Evidence bounded-read tooling; the tooling reads explicitly allowed local source_ref files from validated input bundles and returns bounded read artifacts only; this does not implement packet generation, runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a local Make target for Guardian Evidence bounded-read tooling; the target reads explicitly allowed local source_ref files from validated input bundles and returns bounded read artifacts only; this does not implement packet generation, runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a static Guardian Evidence bounded-read result fixture for the local-tooling input bundle; the fixture records bounded reader output shape only; this does not implement packet generation, runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- static fixture path: `docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`; this is bounded-reader output shape only, not packet output or runtime truth.
- this branch adds local stdout-only Guardian Evidence Packet generator tooling; the tool consumes bounded-read result JSON, emits generated packet output to stdout, and validates it statically; this does not implement runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- local generator path: `scripts/guardian/generate_evidence_packet.py`; this is stdout-only local tooling, not runtime support.
- this branch adds a local Make target for stdout-only Guardian Evidence Packet generator tooling; the target consumes bounded-read result JSON, emits generated packet output to stdout, and validates it statically; this does not write packet fixtures, implement runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds a static generated GuardianEvidencePacket fixture for the local-tooling generator pipeline; the fixture was produced by the local stdout-only generator from the bounded-read fixture, then the top-level `packet` object was extracted and checked in; this preserves evidence refs with content hashes, uncertainty with skipped-source representation, forbidden interpretations with boundary label, all authority locks false, and no absolute paths or secrets; the focused test `tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py` asserts structural equivalence with fresh generator output; this does not implement runtime reducer behavior, packet generation by itself, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- static fixture path: `docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`; this is generated fixture output shape only, not runtime reducer output or source truth.
- this branch adds a local diagnostics-only evidence-packet inspection CLI option through `reducer_dry_run.py --evidence-packet`; it loads a GuardianEvidencePacket fixture, validates it with the static packet validator, and returns bounded diagnostics with packet metadata and all-false authority state; mutually exclusive with `--input-bundle` and `--input`; this does not implement runtime reducer behavior, packet generation, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- this branch adds bounded count diagnostics for `reducer_dry_run.py --evidence-packet` inspection of a checked-in GuardianEvidencePacket fixture; this does not implement runtime reducer behavior, evidence ingestion, persistence, UI, dev-build buttons, CI gating, release gating, Execution Ledger adoption, WorkOrder mutation, write flags, Pi Loop invocation, source mutation, provider execution, Codexify ingestion, or durable mutation.
- Continuity remains quarantined behind `test-continuity`.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` remains legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- The current `main` tip includes docs-first operator routing for current-state interpretation and release readiness.
- OpenAI export import and Task Prompt Archive are present on `main`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface remains test-only, API-key-gated, and profile-quarantined under `test-continuity`.
- Guardian bridge work on `main` is proof/contract only and does not widen the supported runtime promise.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts mean shipped runtime support.
- Do not assume shared presence, hosted rooms, chat transport recovery, thread lenses, or Guardian orientation docs are shipped runtime behavior.
- Do not assume the Guardian delegation loop or Guardian Codex Runner bridge docs imply an end-to-end supported delegation/runtime path.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not assume the new Guardian bridge proof chain means live orchestration support.
- Do not infer a wider release promise from docs-only onboarding, scaffolds, or audit artifacts.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not assume hosted rooms, participant node attachment, Shared Room KB, or cross-node document handoff are implemented from planning docs alone.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- New docs-only contracts and bridge proofs are guidance only until runtime proof lands on `main`.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep Guardian bridge proof separated from shipped runtime claims.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Recheck blocker status only when `main` moves.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] OpenAI export import and Task Prompt Archive are documented as present on `main`.
- [ ] Queue, config, delegation, and federation risks stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.
- [ ] New docs-only contracts and bridge proofs must stay out of the supported runtime claim set until proven on `main`.
- [ ] Any new release claim needs fresh proof on `main`, not branch-local evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
