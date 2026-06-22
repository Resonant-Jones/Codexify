# Scout iOS Native Client

> Build proof: [SCOUT_V1_BUILD_PROOF.md](./SCOUT_V1_BUILD_PROOF.md)

Scout is a native SwiftUI client for operating against an existing Codexify/Guardian (Vault) backend. It is a mobile operator console, not a full clone of the Codexify web UI.

This implementation follows the concepts defined in [`../../docs/architecture/ios-scout-vault-remote-contract.md`](../../docs/architecture/ios-scout-vault-remote-contract.md).

**Guardian is the operator. Vault remains the long-term memory authority.** Scout observes and operates through Guardian/Vault surfaces; Vault remains the interpretation and persistence authority.

## Current V1 Capability Surface

Scout V1 implements five tabs:

| Tab | Purpose |
|---|---|
| Guardian Chat | Thread-scoped operations (Conversation + Inspector) |
| Server Status | Vault health and runtime evidence |
| Activity | Cross-thread task receipt timeline |
| Artifacts | Global document listing |
| Settings | Endpoint profile and API key configuration |

## Guardian Chat Lifecycle

Scout supports the full thread operation loop:

1. **Empty list** — When no threads exist, the list shows "No threads yet" with a direct "New Thread" button.
2. **New Thread** — Creates a thread container via `POST /api/chat/threads`. Thread creation does not send a message automatically.
3. **Auto-enter** — After creation, Scout navigates into the new thread immediately.
4. **Empty thread ready state** — A new empty thread shows "Thread ready" with an invitation to send the first message. No completion has been requested yet.
5. **Send message** — Posts a user message via `POST /api/chat/{thread_id}/messages`. Sending a message does not request completion automatically.
6. **Request completion** — Enqueues a Guardian response via `POST /api/chat/{thread_id}/complete`. Route acceptance does not prove completion.
7. **SSE task observation** — Connects to `GET /api/tasks/{task_id}/events` to stream live task events.
8. **Terminal refresh** — On `task.completed`, automatically refreshes persisted thread messages. On `task.failed` or `task.cancelled`, shows a neutral status without synthesizing assistant output.
9. **Rename thread** — Patches the thread title via `PATCH /api/chat/threads/{thread_id}`. The navigation title updates immediately and the thread list refreshes on return.

### Conversation / Inspector Split

Each thread detail is organized into two tabs:

- **Conversation** — Messages, composer, send, completion request, refresh messages
- **Inspector** — Thread Documents, Retrieval Evidence, Task Receipts, with dedicated refresh buttons

## Server Status

The Server Status tab provides Vault-level observability with Status and Evidence tabs:

- **Status** — Endpoint info, reachability (validation state + probe message), authentication state
- **Evidence** — Health snapshot (latency, service, health status, timestamp), LLM health (provider, model), Catalog (model count, providers, model names)

All evidence is display-only. Scout does not interpret health, readiness, or provider state.

## Activity

The Activity tab aggregates cross-thread task receipts using existing per-thread probes (`ScoutGuardianThreadsProbe` + `ScoutThreadTasksProbe`). It shows a unified timeline of task events across all threads with thread context. No global task-history backend route exists yet — Activity uses N+1 per-thread loading.

Future planned surfaces (not yet implemented): Active Tasks, SSE Observations, Completion Requests, Notifications.

## Artifacts

The Artifacts tab lists global documents via `GET /api/media/documents`. It is distinct from the thread-scoped Inspector: Inspector shows evidence attached to a specific thread; Artifacts shows user-owned outputs across all threads.

## Settings

Settings configures the Vault endpoint profile and API key:

- **Endpoint Profile** — Name, base URL, transport type with local draft validation
- **API Key** — Stored in iOS Keychain, never written to UserDefaults
- **Connectivity** — Validate draft, test connection with health probe
- **Persistence** — Non-secret profile fields saved to `@AppStorage`; API key in Keychain only

## Boundaries and Non-Claims

- Scout is not the full Codexify web UI.
- Scout is not the durable memory authority.
- Scout does not add backend routes.
- Scout does not replace the supported local Docker Compose path.
- Scout does not prove model availability by itself.
- Scout does not widen release support for delegation, federation, graph writes, or cloud providers.
- Scout observes and operates through Guardian/Vault surfaces; Vault remains the interpretation and persistence authority.
- Route acceptance is not completion. Task-event publication is not UI receipt. Scout does not infer completion success from HTTP 2xx.
- Scout does not synthesize assistant messages locally.

## Validation / Smoke Checklist

Manual operator checklist for verifying a Scout V1 build:

- [ ] Configure endpoint URL and API key in Settings
- [ ] Validate draft — check local validation feedback
- [ ] Test Connection — verify reachability and authentication state
- [ ] Load Server Status — confirm health, LLM, and catalog evidence
- [ ] Create a new thread — verify auto-navigation into thread
- [ ] Confirm empty thread ready state is shown
- [ ] Send a message — verify it appears in the conversation
- [ ] Request Guardian Response — verify task acceptance evidence
- [ ] Observe SSE task events — verify live task status stream
- [ ] Wait for terminal event — verify messages auto-refresh
- [ ] Rename thread — verify title updates in nav bar
- [ ] Return to thread list — verify renamed title appears
- [ ] View Activity tab — verify cross-thread task receipts
- [ ] View Artifacts tab — verify global document listing
