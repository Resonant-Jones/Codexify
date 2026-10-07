# ADR-101: Clone-to-Ready Bootstrap and Readiness

**Status:** Proposed
**Date:** 2026-10-02
**Evidence:** Branch source qualification on macOS and a Linux runner; native adapter unit proof and packaged WebUI build proof. No release claim.

## Canonicalization history

This branch draft originally used ADR-099. During reconciliation with `main`,
Cloudflare Edge Platform Boundary already owned ADR-099 and Campaign
Continuation Authority Contract owned ADR-100. The clone-to-ready draft is
therefore registered as ADR-101. Its Proposed status, original date, semantics,
and qualification limits are unchanged.

## Context

Source setup, native desktop startup, and frontend gates independently describe startup. Requiring a model before opening the workspace prevents users from configuring capabilities through the UI. A coding agent must be able to invoke the same deterministic installer as a human, without becoming an installer authority or modifying application source.

## Decision

`contracts/bootstrap/readiness.v1.json` is the versioned semantic authority. `scripts/generate-bootstrap-bindings.py` generates Python, Rust, TypeScript, and prerequisite-only shell bindings; its `--check` mode rejects drift. Adapters consume generated tokens. Commands, provider implementations, copy, and platform behavior remain outside the contract.

Four dimensions remain separate:

- Workflow progress: inspecting, configuring, downloading, starting, migrating, verifying, paused, action_required, failed, complete.
- Core capability: `coreReady` permits opening the workspace after required application services and migrations pass observed checks.
- Inference capability: `inferenceReady` requires the configured local provider/model health checks. Chat remains unavailable without it.
- Human action: none, consent_required, credentials_required, provider_model_choice_required, network_unavailable, prerequisite_unavailable.

`./scripts/setup` is the canonical source-clone entrypoint. It starts with the shell and Python standard library, before Guardian, Textual, or inference is available. The packaged launcher remains a separate native execution adapter. Both stage the existing Compose services, migrate through the existing migrator, and defer model preparation and optional graph services. This introduces no deployment topology.

Saved progress is evidence, never runtime authority. Resume re-inspects configuration, prerequisites, and health. Required downloads use bounded retries and preserve completed work. Configuration backfills missing defaults and valid secrets remain unchanged. Existing volumes remain owned durable state; missing credentials require recovery rather than destructive resets.

After core readiness, a dismissible and resumable personal setup surface explains unavailable inference. A deliberate Finish personal setup action may invoke the existing native configuration helper. The web client has no host mutation authority and hands host actions to `./scripts/setup`. Neither path invents a generalized Guardian execution endpoint. Provider/model alternatives, credentials, packages, runtime/model downloads, elevation, external accounts, exposure, and new permissions require a human decision.

Installation intent is operational authorization to invoke/observe setup. It does not authorize source changes. Agents stop for explicit change authorization when they encounter an installer defect, and never answer host consent prompts for the human.

Personal Compose ports bind to loopback. Container networking retains existing semantics. No LAN flow is added.

## Authority and state

The installation lives on the user's local device; Docker containers cross the host boundary, and asset acquisition crosses the network boundary. The user owns configuration, credentials, and durable PostgreSQL state. The installer has bounded local configuration/startup authority; remote assets and logs are evidence only. Treat interrupted downloads and buggy components as expected failures. The installer cannot grant external accounts or new host permissions.

Configuration writes are atomic. Reruns converge from observed state; migrations retain the existing schema authority and versioning. Checkpoints are versioned diagnostic snapshots and cannot substitute for health after restart. Account onboarding remains separately account-scoped.

## Governing contracts

This aligns with [ADR-069](069-codexify-beta-runtime-support-boundary.md): `core_ready` without inference is an onboarding intermediate, not a new supported Beta category. Local inference remains part of the named supported runtime promise. Shared semantics do not promote packaged desktop to supported Beta.

This aligns with [ADR-071](071-connections-control-plane-boundary.md): configuration, authorization, and health are distinct. Existing Connections inspection does not become mutation authority. Canonical-token doctrine requires generated shared state vocabulary rather than independent registries.

Neither ADR is superseded. `00-current-state.md` remains unchanged. Current-main release qualification remains a separate gate.

## Qualification gate

Completion requires contract drift rejection; focused Python, native, and frontend proof; both Compose loopback configurations; isolated migration/core/no-inference workspace proof; later actual inference/chat proof; rerun/state preservation and restart/resume; and actual macOS/Linux qualification. Unit tests, rendered mocks, and a container prerequisite check do not establish full runtime or platform proof. Until those observations pass, this decision records intended semantics and branch implementation only.

## Implementation observations (branch only)

Disposable source installs have reached core readiness on the real macOS host and in a Linux Docker CLI runner with a native Linux source volume. The Linux runner uses the same Docker Desktop daemon as macOS; this does not prove independent Linux host installation or packaged desktop release support.

Linux qualification has additionally observed configured local inference readiness, an actual queued chat completion with an independently read-back persisted assistant reply, byte-identical configuration on rerun, and preservation of the thread/messages after application-container stop and setup resume. Inference used an already-running local runtime; no inference runtime or model was installed by bootstrap. Core-only Settings and the setup card have been observed in a real browser, including a deliberate provider-choice stop and persisted dismissal after reload.

Missing optional embedding assets exposed eager startup in both backend dependencies and the document worker. Those paths now defer model construction until capability use unless `LOCAL_EMBEDDINGS_REQUIRED` explicitly requires startup validation. Offline model recovery rejects download before network access. Document/retrieval capabilities still require their real model; chat persistence is not embedding proof.

Source frontend installation now uses the canonical root workspace and frozen lockfile. Native config uses project-volume inventory to distinguish new storage credentials from preservation of existing implicit credentials. Required core-service inventory participates in native readiness. The packaged adapter retains its existing `webui` service and stages its workspace build using canonical root dependency manifests. A personal workspace Dockerfile preserves the existing nginx proxy contract without changing other deployment recipes. Saved image-state metadata now also requires observed core-image presence; it cannot establish asset readiness alone. Existing Compose project identity is used for volume inventory.

MacOS qualification has additionally observed enabled Send after local inference health, a real browser-submitted chat with an independently read-back persisted assistant reply, byte-identical configuration on rerun, and preservation of both messages after container stop and setup resume.

The final task snapshot has passed the required contract/setup, native, frontend, documentation, and both resolved Compose checks. Both isolated source installs have rerun and resumed with byte-identical selected configuration and independently read-back original chat messages. Native evidence covers adapter semantics and a real packaged WebUI asset build; it does not claim an installed Tauri application or packaged release qualification. The release HOLD and `00-current-state.md` remain unchanged.

### Packaged qualification isolation

The installed-adapter proof uses the explicit opt-in `CODEXIFY_DESKTOP_QUALIFICATION_ID` namespace described in [the packaged qualification procedure](../../desktop-qualification.md). One ID scopes the packaged runtime, desktop data/logs, persistent macOS WebKit datastore, Compose project and volumes, published loopback ports, and desktop Guardian Keychain service. Absent the control, normal packaged behavior is unchanged. This is a bounded proof mechanism, not a general profiles system or a new supported deployment path. ADR-101 remains Proposed; implementation and structural-signature checks do not establish installed-runtime qualification or change overall HOLD.
