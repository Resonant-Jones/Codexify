# Codexify iOS Scout <-> Vault Remote Contract

> Classification: architecture contract
> Status: normative
> Normative language: "must", "must not", "should", and "non-goal" are intentional contract terms.

Purpose: Define the boundary contract for a future lightweight native iOS companion app, Scout, that connects to the user's Codexify home server, Vault, while keeping Guardian as the operator and Codexify Core as the long-term authority.

Last updated: 2026-06-19

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
- The Codexify repo is the correct place to document this contract.

What is not yet true:

- No iOS app exists as a supported Codexify surface.
- No `mobile/scout-ios/` implementation exists as part of this task.
- No Scout <-> Vault transport is implemented by this task.
- No phone-side local model fallback is implemented by this task.
- No public remote-access promise is made by this task.
- No standalone Scout repository exists or is required by this task.

This contract is documentation only:

- It does not implement an iOS app.
- It does not create `mobile/scout-ios/`.
- It does not add routes.
- It does not modify backend auth behavior.
- It does not widen the supported beta runtime promise from `00-current-state.md`.

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

- Early V1 assumes a trusted private-network path and an honest-but-buggy operator environment.
- Authentication must still be explicit.
- Tailscale or another trusted private network is transport, not identity or authorization by itself.

## Repository Posture

- The first Scout implementation should be incubated inside the Codexify monorepo under `mobile/scout-ios/`.
- This keeps the mobile client close to backend routes, API contracts, runtime docs, and Guardian orchestration semantics while the client shape is still being discovered.
- Scout may later be extracted into a standalone repository when there is a clear need for independent release cadence, TestFlight or App Store preparation, separate CI/CD, mobile-specific contributors, or product separation.
- Until extraction is explicitly approved, Codex should assume `mobile/scout-ios/` is the correct implementation root for future SwiftUI tasks.
- This contract does not create `mobile/scout-ios/`; it defines the intended future implementation location only.

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

## V1 Supported UI Surfaces

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

## Phased Implementation Outline

Phase 1:

- create `mobile/scout-ios/` SwiftUI app workspace inside the Codexify monorepo
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

- This task defines a new client and control-plane boundary for Scout <-> Vault interaction and establishes a monorepo-first incubation posture for future iOS work.
- It does not implement runtime behavior, create the app, change server APIs, alter memory authority, or widen release support.

## Invariants

- Do not widen release claims.
- Do not change runtime behavior.
- Do not add Swift or iOS code in this task.
- Do not create `mobile/scout-ios/` in this task.
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
- The contract explicitly names `mobile/scout-ios/` as the future monorepo implementation root.
- The contract explicitly states that no iOS app is implemented by this task.
- No code files are changed by this task.
