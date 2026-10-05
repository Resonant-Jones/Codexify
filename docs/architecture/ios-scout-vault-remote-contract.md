# Codexify iOS Scout <-> Vault Remote Contract

> Classification: architecture contract
> Status: normative
> Normative language: "must", "must not", "should", and "non-goal" are intentional contract terms.

Purpose: Define the boundary for the native Scout client and its remote connection to the user's Codexify home server, Vault, while keeping Guardian as the operator and Codexify Core as the long-term authority.

Last updated: 2026-10-04

## Purpose

- Scout is a native iOS companion for Codexify.
- Vault is the user's Codexify home server.
- Guardian remains the operator and orchestrator.
- The phone is a command shell, viewport, and local fallback surface.
- Scout exists to make Codexify feel native and reachable from iPhone without moving the system's long-term intelligence onto the phone.

## Current Truth and Scope

What is true now:

- Codexify is in local-first beta hardening on `main`.
- Local Docker Compose remains the supported install path.
- Local-only provider posture remains the supported posture.
- Chat completion, task events, health surfaces, upload -> embed -> readback, and workspace-local retrieval are current supported beta paths.
- Scout's SwiftUI source is tracked under `mobile/scout-ios/` in this monorepo.
- `mobile/scout-ios/CodexifyScout.xcodeproj` is the tracked canonical application project with the `Codexify Scout` target and shared scheme. The client integration from current main passes all 66 SwiftPM tests and the signed proof-Simulator build; see [the integration receipt](../../mobile/scout-ios/SCOUT_MAINLINE_INTEGRATION_815.md) for its exact source/base and qualification boundaries.
- Local/operator `X-API-Key` behavior is implemented. Focused tests show the Guardian-health probe rejects generic HTTP success and does not infer authentication from credential presence. See `mobile/scout-ios/SCOUT_V1_BUILD_PROOF.md` for the bounded build and test evidence.
- Historical source-branch evidence qualifies hosted `remoteSession` through separate Cloudflare Access admission and canonical Guardian account-session handoff. The real Simulator completed protected reads, two thread/message/task-event/persisted-output turns, resume, document browsing and logout denial. See [the October 4 live proof](../../mobile/scout-ios/SCOUT_LIVE_CONTINUITY_2026-10-04.md) for exact revisions and evidence limits. The mainline integration has fresh tests/build proof, but no new authenticated live run. These qualifications do not widen `main` release support.

What is not yet true:

- Scout is not a supported Codexify Beta surface. The hosted Simulator proof does not establish current physical-device continuity or distribution readiness.
- Cloud/Vault synchronization, Recording Authority, federation, and phone-side local model fallback are not established by the current Scout evidence.
- No public remote-access promise or App Store readiness is established.

This contract describes the implemented client boundary and remaining remote work; this documentation reconciliation:

- Adds no routes or authentication behavior.
- Records only the linked, bounded hosted runtime evidence; grants no access-policy or deployment authority.
- Does not widen the supported Beta runtime promise from `00-current-state.md`.

## Nodes and Trust Boundaries

Nodes:

- Scout: the native iPhone client.
- Vault: the user's Codexify home server, typically running on the supported local-first path.
- Guardian: the server-side operator/orchestrator running within Vault.
- Optional local runtime providers behind Vault's local provider posture.

Trust boundaries:

- Device boundary: iPhone versus Vault host.
- Network boundary: private-network transport such as Tailscale versus public internet exposure.
- Authority boundary: Scout may present and cache state, but Vault remains the authoritative Codexify runtime.

Threat model for this first contract:

- Personal nodes may use a trusted private-network path; the hosted lane also handles untrusted clients and malformed or mixed credential selectors at its explicit admission and account boundaries.
- Authentication must still be explicit.
- Tailscale or another trusted private network is transport, not identity or authorization by itself.

Authentication boundary:

- Transport selection and Guardian authentication are independent. Endpoint reachability, including a valid `/health` response, does not prove a user session or authorization.
- The implemented local/operator lane may send `X-API-Key`; credential presence alone does not establish authentication. The Guardian-health probe fails closed on unrelated or malformed HTTP success responses.
- ADR-051 governs the separation between local API-key and remote session/Bearer behavior for private clients. Scout must not silently reinterpret its local API key as a remote user session, send both credentials, or fall back to the local credential after remote authentication loss.
- `remoteSession` uses the existing exact-purpose Guardian `account_session`, stored only in a profile/origin Keychain record. Personal nodes use Guardian Bearer when supported. The qualified hosted composition sends Access in Authorization and the account session in `X-Guardian-Account-Session`; ADR-092's separately approved amendment accepts edge-consumed Authorization only after fixed-host/private-preview signed Access validation. No Access credential is reconstructed or moved to an origin header. Cloudflare/browser admission and private-network transport cannot substitute for independent Guardian account authentication.
- Login, restoration, expiry, reauthentication and logout are explicit. Invalid account credentials fail closed, and unrelated/operator-route failures cannot indiscriminately destroy a valid session. Hosted logout can verify one denied protected replay using the already prepared credential in memory, after canonical revocation succeeds; it never restores or exports local authority.

## Hosted and personal connection composition

The connection model is `connection = endpoint/transport + explicit authentication mode`.

- The implemented convenience/default hosted lane is `https://preview.codexify.space` with `remoteSession`, selected explicitly through Use hosted Codexify and qualified in the linked Simulator proof.
- Personal/self-hosted nodes remain first-class: a user chooses their own HTTPS endpoint and an authentication mode actually supported by that node. Connecting to one's own node must not require a Resonant Constructs paid-service account.
- Tailscale, LAN/private DNS, Cloudflare Tunnel, and user-controlled ingress are transport options. They do not choose a Codexify authentication mode or establish account identity.
- Cloudflare Access is a distinct mandatory ingress boundary on the qualified hosted lane. Its Google/email-code browser flow and registered public native OAuth/PKCE client admit ingress only. The existing Guardian browser login then uses a one-time origin-bound S256 handoff to issue an independent native account session for the same canonical account; browser session bytes are never exported to Scout.
- Access, account-session and local-key records are isolated by profile UUID and canonical endpoint origin. Changing connections clears volatile account/thread projections and cancels an in-flight sign-in. Tests qualify credential selection, wrong-origin refusal and stale-read isolation; the hosted live proof does not newly qualify a personal node.
- Guardian/Vault owns durable accounts, threads, messages, tasks, and documents. Scout's volatile projections remain subordinate to that authority.

The continuity slice shares observable persisted-message state between thread and task views. A successful `task.completed` triggers a persisted read and publishes that read to the conversation; a failed read cannot claim refresh success. Failed/cancelled tasks do not create assistant messages. Selection includes profile identity, endpoint URL, authentication mode, and thread ID; changed connections clear volatile views, and stale or overlapping reads cannot replace newer/other-node state. Display-only profile metadata changes preserve selection. Foreground/resume refresh is bounded to the selected conversation. Completed output and foreground/resume are live-qualified on the hosted Simulator; failed/cancelled outcomes and cross-node switching retain unit-test proof only.

See [the mainline integration receipt](../../mobile/scout-ios/SCOUT_MAINLINE_INTEGRATION_815.md) for the bounded transplant and fresh validation, and [the live proof](../../mobile/scout-ios/SCOUT_LIVE_CONTINUITY_2026-10-04.md) for the historical #815 closeout. App Entities/App Intents (#816) and deeper integrations remain separate downstream tasks, gated on both integrations reaching main; no Beta, TestFlight, or App Store readiness advances.

## Repository Posture

- Scout is implemented inside the Codexify monorepo under `mobile/scout-ios/`.
- This keeps the mobile client close to backend routes, API contracts, runtime docs, and Guardian orchestration semantics while the client shape is still being discovered.
- Scout may later be extracted into a standalone repository when there is a clear need for independent release cadence, TestFlight or App Store preparation, separate CI/CD, mobile-specific contributors, or product separation.
- Until extraction is explicitly approved, Codex should assume `mobile/scout-ios/` is the correct implementation root for future SwiftUI tasks.
- The original monorepo-first incubation choice is now realized in tracked source and the canonical Xcode project; extraction remains a separate decision.

## Core Architectural Principle

Guardian is the operator.

- The iOS app is not the operator.
- Scout sends authenticated intent to Guardian.
- Guardian routes that intent through Codexify Core, tools, memory, media, documents, tasks, and future orchestration surfaces.
- Long-term memory authority remains server-side in Codexify Core / Vault.
- Scout is a remote cockpit, not a full native clone of the web UI.

State ownership and continuity posture:

- Vault is the authority for threads, messages, tasks, documents, artifacts, retrieval, provenance, graph, and account export/restore semantics.
- Scout may hold local cache, local chat history, and offline drafts, but those are subordinate client views rather than durable system truth.
- Unless a later contract explicitly expands the role, Scout-side memory is cache, draft state, or short-horizon continuity only.

## V1 Client UI Surfaces

- Guardian Chat
- Activity / Task Stream
- Artifacts
- Server Status
- Settings / Auth

## Primary User Loop

1. The user submits intent from Scout.
2. Guardian receives the instruction on Vault.
3. Guardian executes the task, tool, or action through Codexify.
4. Vault emits task and event updates.
5. Guardian returns a result, status, and any artifacts.
6. Scout displays the response, current status, and available artifacts.

## Minimum API Contract

V1 mobile work should prefer canonical `/api/*` routes as the Scout contract rather than older mirrored legacy aliases. This contract does not add or rename routes.

The currently proven first-send path on `main` remains thread creation plus thread-scoped message send and completion. This contract still keeps the mobile boundary on `/api/*` surfaces and treats any missing mobile-friendly alias as follow-through work for a later implementation slice rather than a reason to fall back to legacy mirrored routes.

Core chat:

- `POST /api/chat/messages`
- `POST /api/chat/{thread_id}/messages`
- `POST /api/chat/{thread_id}/complete`
- `GET /api/chat/threads`
- `GET /api/chat/{thread_id}/messages`

Server and model health:

- `GET /health`
- `GET /api/health/llm`
- `GET /api/health/retrieval`
- `GET /api/llm/catalog`

Events and tasks:

- `GET /api/events`
- `GET /api/tasks/{task_id}/events`
- `POST /api/tasks/{task_id}/cancel`

Artifacts:

- `GET /api/threads/{thread_id}/documents`
- `GET /api/documents/{document_id}`
- `GET /api/media/images`
- `GET /api/media/images/{image_id}`
- `GET /api/media/documents`
- `GET /api/media/documents/{document_id}`

## Explicit Non-Goals

The first iOS app contract must not require:

- full native UI parity with the web app
- every personal-facts endpoint
- every media upload or generation endpoint
- full project management
- full Obsidian configuration
- debug inspection panels
- migration or import flows
- graph visualization
- every mirrored legacy route
- phone-side ownership of durable long-term memory
- standalone iOS repository creation in the first implementation pass

## Local Fallback Posture

- Scout may eventually support on-device chat and image analysis when offline.
- Offline local model support must be treated as a fallback lane, not the primary long-term memory authority.
- Scout may hold local chat cache or history and offline drafts.
- Vault remains the authority for long-term memory, retrieval, provenance, graph, documents, and account export or restore semantics.
- Local Scout memory must be treated as cache, draft state, or short-horizon continuity unless a later architecture contract explicitly expands that role.

## Tailscale and Private-Network Assumption

- This contract may assume a trusted private-network path, such as Tailscale, for early V1 development.
- It must not claim public internet exposure or production remote-access hardening.
- Authentication must remain explicit even on a trusted private network.
- This contract must not weaken the existing local-first supported posture from `00-current-state.md`.

## Security and Sovereignty Invariants

- Scout must not store server secrets outside iOS Keychain.
- Scout must not silently mutate identity memory.
- Scout must not bypass Guardian authorization.
- Scout must not claim ownership of Codexify long-term memory.
- Scout must not introduce parallel memory truth.
- Scout must not turn command or task execution into an unrestricted remote-control surface.
- Scout must not treat local or offline model output as canonical Vault memory without explicit synchronization and review semantics defined by a later contract.

## Runtime and Event Semantics

- Route acceptance is not completion.
- Task-event publication is not UI receipt.
- Scout must represent request and task state using the existing runtime semantics where applicable.
- Scout must distinguish server reachability, provider readiness, request execution, and task visibility.
- Scout must not collapse slow local model warmup into "server offline."
- Scout must treat events and task streams as visibility surfaces, not durable proof by themselves.
- Scout must not introduce new runtime token values for this lane; it should reuse the provider and request vocabulary already defined in `chat-runtime-contract.md` and `runtime-protocol-token-contract.md`.

## Historical Phased Implementation Outline

The original outline below records the sequence proposed before Scout source and the Xcode project were tracked. Some client surfaces now exist, but the outline itself is not implementation, launch, remote-authentication, or release proof. Use the current source, tests, and `SCOUT_V1_BUILD_PROOF.md` for those classifications.

Phase 1:

- create `mobile/scout-ios/` SwiftUI app workspace inside the Codexify monorepo (completed as tracked source and project)
- Settings / Auth screen
- server status check
- thread list
- Guardian chat
- send message
- receive response
- basic event stream display

Phase 2:

- task stream UI
- task cancellation
- artifact viewer
- model catalog display

Phase 3:

- push or local notifications
- offline draft queue
- background refresh
- rich artifact previews
- Guardian action approval cards
- local model fallback interface for chat and image analysis

## Extraction Trigger

- Extract Scout to a standalone repository only when there is a concrete need for independent release cadence, TestFlight or App Store build isolation, separate CI/CD, or separate product ownership.

## ADR Impact

Classification: aligned with existing ADRs and architecture contracts

Governing docs and contracts:

- `00-current-state.md`
- `chat-runtime-contract.md`
- `runtime-protocol-token-contract.md`
- `account-export-restore-contract.md`
- `self-extending-agent-plugin-system.md`
- `agent-protocol-operations.md`

Reason:

- The original contract defined the Scout client boundary and monorepo-first incubation. The tracked implementation and build now exist beneath that boundary.
- ADR-051 preserves the separation between local API-key and remote session/Bearer authentication. ADR-092 governs exact credential purpose and the approved bounded hosted alternate account transport; its amendment is separately reviewable at backend commit `5836ed986e4cc6175b5184fe6b5d2fb23a989ed1`. This reconciliation records implemented/proven behavior without changing server APIs, memory authority or release support.

## Invariants

- Do not widen release claims.
- Do not change runtime behavior.
- Do not infer launch, live Guardian behavior, physical-device operation, or Beta support from source, test, or build evidence.
- Do not treat local `X-API-Key` behavior as remote-session authentication.
- Do not treat endpoint reachability or a supplied credential as authentication proof.
- Do not create a standalone iOS repository in this task.
- Do not add new routes.
- Do not modify backend auth behavior.
- Do not imply Scout owns durable memory.
- Do not bypass Guardian as operator.
- Do not weaken the local-first supported posture.
- Do not introduce new runtime token values.
- Do not claim Tailscale or private networking is production remote-access hardening.

## Proof Surface

- This file exists at `docs/architecture/ios-scout-vault-remote-contract.md`.
- `docs/architecture/README.md` links to this contract.
- Tracked `mobile/scout-ios/` source and `CodexifyScout.xcodeproj`, the 66-test SwiftPM result, the signed Simulator build and the linked live receipts support only their stated proof tiers.
- `mobile/scout-ios/SCOUT_V1_BUILD_PROOF.md` records the evidence tiers and remaining proof gates.
- This documentation reconciliation changes no code or Xcode project files.
