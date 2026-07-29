## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-28

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` changes are mostly release cleanup, health/probing fixes, UI polish, and release-truth documentation, plus email implementation-target inspection work that does not widen runtime support.

## What changed recently
- Added Hosted Room actor participant identity: Guardian is now a canonical resident actor with stable identity. User-owned Personas can be referenced through `local_persona` bindings. Actor lifecycle is durable across enable/disable. Luna is not a Codexify-native actor.
- Added explicit asynchronous Hosted Room Guardian invocation for authenticated owners and valid guest sessions. The owner and guest routes accept only an explicit human `message_id`, revalidate the current room/thread/source/Guardian/requester authority, construct bounded invocation metadata, and delegate acceptance to the canonical chat enqueue path. Mentions remain ordinary text.
- Added Hosted Room human message read/write API: owners and guest sessions can read one canonical transcript and post human messages with structured participant provenance. Mentions are ordinary text with no agent invocation.
- Added Hosted Room guest session exchange: pending invitations can be exchanged once for a signed HTTP-only room-session cookie. Exchange creates one durable human member participant and marks the invitation accepted. Session inspection revalidates room/invite/participant lifecycle truth on every request.
- Added Hosted Room invitation management API: authenticated room owners can issue room-scoped invitations with one-time plaintext credentials, list invitation metadata, and revoke invitations. Only token verifiers (SHA-256) are persisted; plaintext tokens are never stored.
- Added Hosted Room owner lifecycle API: authenticated owners can create, list, inspect, update, and close Hosted Rooms backed by canonical chat threads. Room creation is atomic (room, thread, owner participant). Account isolation is enforced on all owner routes.
- Added a supported account-scoped retry endpoint for failed zero-write OpenAI account-import jobs (`POST /api/imports/openai-account/{job_id}/retry`).
- Repaired tester account-import staging continuity so both backend and worker resolve shared import staging from one canonical project directory.
- Added an email implementation-target inspection and campaign index on `main`; this is planning and target mapping only.
- Removed the legacy document generation UI from the frontend.
- Fixed mobile composer viewport settling.
- Updated health checks to probe the cloud-provider endpoint instead of returning a stub degraded status.
- Pinned friends/family chat to DeepSeek V4 Flash.
- Separated live Continuity database proof from broader operator routes.
- Restored thread-first project retrieval.
- Removed Zac's last name from the email campaign materials.
- Added a docs/proof-only Project Pulse exact-ID read proof fixture contract and static fixture after implementation-target inspection. This does not implement Project Pulse, routes, services, adapter methods, schemas, migrations, UI, CLI, workers, command bus, provider calls, retrieval changes, graph use, browser capture, export/restore, tests, runtime fixture loading, database seeds, writes, or supported-beta activation.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` remains legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- The friends/family chat profile is pinned to DeepSeek V4 Flash on `main`.
- Thread-first project retrieval is restored on `main`.
- Supported Compose live proof receipts exist as a bounded proof and validation seam, not a release expansion.
- OpenAI export import and Task Prompt Archive are present on `main`.
- Failed zero-write account-import jobs have an explicit owner-scoped retry endpoint that requires canonical staged-data visibility, preserves original failure evidence, and prevents duplicate queue publications.

### Hosted Room owner API

What is now implemented:
- Hosted Room persistence exists (ADR-053 persistence foundation).
- Authenticated owners can create Hosted Rooms.
- Creation produces one canonical backing chat thread.
- Creation produces one owner participant.
- Authenticated owners can list and inspect their own rooms.
- Authenticated owners can update title and enabled-agent configuration.
- Authenticated owners can close rooms.
- Authenticated owners can issue room-scoped invitations.
- Plaintext invitation credentials are returned exactly once.
- Only a SHA-256 verifier (token hash) is persisted.
- Owners can list invitation metadata (without tokens or hashes).
- Owners can revoke pending and accepted invitations.
- Invitation routes are account- and room-scoped.
- Closed rooms reject new invitations.
- Pending invitations can be exchanged once for a guest session.
- Exchange creates one durable human member participant.
- Exchange marks the invitation accepted.
- Exchange issues a signed HTTP-only room-session cookie.
- Guest sessions resolve one room and one participant.
- Session inspection revalidates room, invite, and participant state on every request.
- Invitation revocation, participant removal, room closure, invitation expiry, and session expiry invalidate access.
- Logout clears the browser cookie.
- Room owners and valid guest sessions can read one canonical Hosted Room transcript.
- Room owners and valid guest sessions can post human messages.
- Messages persist to the room's backing `chat_messages` thread.
- Human messages carry structured participant provenance.
- Sender identity is not embedded in content.
- Owner and guest routes enforce active room and participant state.
- Deterministic bounded polling-compatible pagination exists.
- Account isolation is enforced on all owner and invitation routes.
- Owners can invoke the one active resident Guardian with `POST /api/hosted-rooms/{room_id}/actors/{participant_id}/invoke`.
- Valid guest sessions can invoke the one active resident Guardian with `POST /api/hosted-room-session/actors/{participant_id}/invoke`.
- Both invocation routes accept exactly `{"message_id": <positive integer>}` and return asynchronous acceptance metadata only; they do not return assistant content or credentials.
- Invocation preparation revalidates the explicit source human message, canonical active Guardian participant, backing thread, and owner/guest requester lineage before calling `enqueue_chat_completion`.

What remains unimplemented:
- Luna invocation.
- Non-Guardian agent participant provenance.
- Automatic assistant responses.
- RoomShell.
- Participant removal API.
- Contacts binding.
- Ambient presence.
- Automatic Tailscale onboarding.
- Cross-node rooms.
- Release qualification.

Enabled-agent configuration is stored and the active resident Guardian binding grants only the explicit Guardian invocation routes described above; it does not create mention-driven behavior.
Generated join paths (e.g., `/join/{token}`) are not yet functional guest-entry routes.
Guest sessions authorize session inspection, human message read/write, and explicit Guardian invocation when the current invitation and participant lineage remain valid.
Mentions (e.g., `@Guardian`, `@Luna`) are currently ordinary persisted text; no model is invoked by posting a mention.
The worker validation branch is reachable only through those explicit routes and
still does not widen the release-qualified Hosted Room feature boundary.

## Not yet true / do not assume
- Do not assume Hosted Room automatic agent responses, Luna invocation, or a release-qualified end-to-end Guardian path.
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts or implementation-target inspections mean shipped runtime support.
- Do not assume the email campaign index or inspection implies an email runtime, mailbox, or send path.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not assume the Guardian delegation loop or Guardian Codex Runner bridge docs imply an end-to-end supported delegation/runtime path.
- Do not assume shared presence, release-qualified or cross-node Hosted Rooms, chat transport recovery, thread lenses, or Guardian orientation docs are shipped runtime behavior.
- Do not infer a wider release promise from docs-only onboarding, scaffolds, or audit artifacts.
- Do not assume any local runtime is available without live endpoint and model inventory proof.
- Do not assume partial-write account-import jobs are retryable (zero-write only).
- Do not assume failed account-import jobs are retried automatically.
- Do not assume missing historical staging is copied automatically.
- Do not assume historical payloads in obsolete worktrees are canonical.
- Do not assume the retry endpoint repairs or deduplicates partial imports.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- Email remains in inspection and planning only; no runtime behavior is shipped yet.

## This week's priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep Guardian bridge proof separated from shipped runtime claims.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Recheck blocker status only when `main` moves.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] Health endpoints return real probe-based status on the supported path.
- [ ] Queue, config, delegation, and federation risks stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.
- [ ] New docs-only contracts, inspections, and bridge proofs must stay out of the supported runtime claim set until proven on `main`.
- [ ] Any new release claim needs fresh proof on `main`, not branch-local evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
