## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-27

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. Mainline now includes admin observability, a `whooshd-deepseek` local profile, private Chrome side-panel work, and campaign control-plane dry-run scaffolding, but the supported release promise is still the local Docker Compose stack with local-only providers.

## What changed recently
- Added admin account observability, a `whooshd-deepseek` local profile, and settings density updates.
- Shipped a private Chrome side-panel chat MVP with task correlation/cancellation and Tailscale session support.
- Added campaign control-plane dry-run scaffolding on `main`.
- Reverted live-proof receipt manifest integration.
- Kept email work in implementation-target inspection and planning; no runtime email path was added.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` remains legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` within the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Admin account observability is present on `main`.
- OpenAI export import and Task Prompt Archive are present on `main`.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the Chrome side-panel client is a public or generally supported release surface.
- Do not assume campaign control-plane dry run implies campaign execution support.
- Do not assume live-proof receipt manifest promotion or trusted `latest` release approval.
- Do not assume an email runtime, mailbox, or send path.
- Do not assume end-to-end Guardian delegation runtime.
- Do not infer a wider release promise from docs-only contracts, inspections, or dry-run scaffolding.
- Do not assume any local runtime is available without live endpoint and model inventory proof.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Federation remains high-blast-radius and trust-policy sensitive.
- Email runtime remains unshipped.
- Proof-receipt manifest promotion is unresolved after the revert.

## This week's priorities
1. Keep the current-state doc aligned to `origin/main` and strip stale release claims.
2. Preserve the local-only beta contract while labeling Chrome side-panel and campaign work as internal or dry-run only.
3. Recheck queue, worker, and config drift before widening any release promise.
4. Keep proof-receipt behavior bounded until manifest promotion is re-established on `main`.

## Release definition right now
- [x] Local Docker Compose is the supported install path.
- [x] The release posture remains local-only with local providers only.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval remain in the supported claim set.
- [x] Health and admin observability surfaces exist on `main`.
- [ ] Chrome side-panel, campaign-control, email, delegation, federation, and graph-write claims require separate proof.
- [ ] Live-proof receipt promotion is not part of the current release promise.
- [ ] Queue/worker/config drift must stay explicitly documented and rechecked before any wider release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
