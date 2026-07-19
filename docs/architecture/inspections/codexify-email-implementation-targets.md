# Codexify Email implementation-target inspection

Status: PROPOSED inspection

Execution lane: standard

Task kind: proof

Evidence posture: code-path only

Source task: GitHub Issue #604

Inspection date: 2026-07-19

## Purpose and evidence boundary

This document maps the proposed Codexify Email campaign to current repository seams. It is a read-only implementation-target inspection. It does not define accepted architecture, change release truth, access a provider, or prove email runtime behavior.

- **CURRENT** means a cited repository path and symbol exists on the inspected branch. It does not imply that it supports email.
- **PROPOSED** means a candidate implementation target or ownership assignment that still requires an accepted Task Spec and, where identified, an ADR.
- **GAP** means the required email contract or proof was not found in the inspected paths.

Codexify Email has **no runtime behavior** in the evidence inspected here. Google Workspace remains the proposed initial hosted provider, but provider state, credentials, aliases, messages, and mailboxes were not accessed. Collaborator identities and mailboxes remain separate human-owned infrastructure and are not implementation or test targets.

## Governing product contract

The proposed primary loop is:

`ingest -> normalize -> classify/triage -> Guardian brief -> propose action -> user approval when consequential -> execute -> reconcile -> receipt`

Guardian briefing is the primary interaction model. A human inbox and reader remain secondary review, correction, debugging, exceptional-workflow, and audit surfaces. Agent addresses are user-owned routing identities. Logical mailbox separation must not create a separate principal or authority boundary. Postgres is durable truth; Redis is operational coordination only. Email and attachments are untrusted external data.

## Current implementation seams

### Identity, authentication, and scope

- **CURRENT:** `guardian/db/models.py::User`, `Project.user_id`, `ChatThread.user_id`, and `ChatThread.project_id` provide account, project, and thread ownership anchors. `guardian/core/auth_dependencies.py::get_current_user_id` and `guardian/core/dependencies.py::get_current_user` resolve request identity.
- **CURRENT:** `guardian/db/models.py::Persona` has `user_id` and optional `project_id`. `PersonaProfile` is a distinct profile model and must not be assumed to provide the same ownership semantics.
- **CURRENT:** `guardian/db/models.py::OAuthConnection` is user-scoped and records provider, mode, scopes, status, encrypted token fields, expiry, and refresh failure state. Its uniqueness boundary is `(user_id, provider, mode)`.
- **CURRENT:** `docs/security/auth-boundary-decision.md` limits static browser API-key use to local mode and requires session or bearer identity for remote browser access.
- **PROPOSED owner:** Guardian authentication and identity maintain the human account boundary; a new Email domain owns user-to-routing-identity and persona-to-routing-identity mappings.
- **GAP:** No durable email routing identity, logical mailbox, alias lifecycle, revocation, reassignment, or persona binding contract was found. `OAuthConnection` alone is not an email identity model and does not authorize collaborator resources.

### Command bus, approval, and consequential actions

- **CURRENT:** `guardian/command_bus/contracts.py::InvokeRequest` carries actor, authentication subject, project/thread context, idempotency key, provenance, permission profile, and external target policy. `CommandSpec` classifies risk, effect, idempotency, and approval mode.
- **CURRENT:** `guardian/command_bus/invoke.py::execute_invoke` evaluates permission and external policy, records confirmation state, and uses an idempotency lookup before command execution.
- **CURRENT:** `guardian/command_bus/store.py::CommandBusStore.create_run`, `get_run_by_idempotency_key`, and `append_event` persist command runs and ordered run events. `guardian/db/models.py::CommandRun` enforces uniqueness for `(command_id, idempotency_key)`.
- **CURRENT:** command-bus approval modes are `none` and `blocked_phase1`; write commands are classified as unsafe and blocked in `guardian/command_bus/manifest.py`.
- **CURRENT:** `guardian/browser/approval.py::{create_approval_request,decide_approval}` and `guardian/routes/browser.py` provide a browser-operation-specific approval surface. `guardian/db/models.py::BrowserApproval` is not an email approval record.
- **PROPOSED owner:** Command bus owns invocation policy and execution envelopes. The Email domain owns immutable draft/send approval snapshots and supplies a command-bus adapter only after the ADR defines the boundary.
- **GAP:** There is no accepted email send command, immutable snapshot of recipients/content/attachments, approval-version binding, mutation invalidation, or autonomous-send prohibition in executable contracts. Browser approval must not be repurposed as the durable email approval model.

### Durable persistence and transactions

- **CURRENT:** SQLAlchemy models live in `guardian/db/models.py`; Alembic uses `Base.metadata` and Postgres transactions in `guardian/db/migrations/env.py`. Existing models demonstrate foreign keys, uniqueness constraints, JSON metadata, and status records.
- **CURRENT:** `ChatMessage`, `UploadedDocument`, `MediaAsset`, `ThreadDocument`, and `ProjectDocumentLink` are candidate patterns for content ownership and attachment linkage, not email storage.
- **CURRENT:** `SyncJob` records connector, state, attempts, errors, and metadata. Its inspected model does not establish the complete user/mailbox/message identity needed by email synchronization.
- **CURRENT:** `EventOutbox` and `guardian/core/event_bus.py::emit_event` provide a durable event-store seam plus in-memory fanout. `guardian/core/outbox.py` bounds tenant identifiers, polling, batches, and event cursors.
- **PROPOSED owner:** A new Email persistence module owns routing identities, logical mailboxes, provider cursors, normalized messages, participants, attachment metadata, drafts, approval snapshots, send attempts, reconciliation outcomes, and receipts. Alembic owns schema evolution.
- **GAP:** No email tables, provider-ID uniqueness constraints, message revision model, attachment quarantine state, cursor transaction, send-attempt ledger, reconciliation receipt, retention policy, or deletion/tombstone semantics exist.
- **Migration hazard:** Adding email semantics to `ChatMessage`, `SyncJob`, or generic JSON metadata would couple correspondence lifecycle to unrelated chat/connector records and weaken database-enforced idempotency. New purpose-specific tables are the smaller auditable target.

### Redis queues, workers, retry, cancellation, and events

- **CURRENT:** `guardian/queue/redis_queue.py` provides named Redis queues, enqueue/dequeue operations, reconnect handling, cancellation markers, and turn locks. Queue acceptance is not durable completion.
- **CURRENT:** `guardian/queue/task_events.py::{publish_with_visibility,read_events,describe_terminal_state}` distinguishes progress visibility from terminal task events and reports event-publication failure separately from continued execution.
- **CURRENT:** `guardian/workers/chat_worker.py` demonstrates queue consumption, cancellation, locking, lifecycle events, and durable result persistence. `guardian/workers/document_embed_worker.py` demonstrates durable status transitions and scoped vector metadata. `guardian/workers/cron_worker.py::process_cron_message` demonstrates durable run state around queued work.
- **PROPOSED owner:** Dedicated Email sync and send workers own provider I/O; Redis carries coordination messages only; Postgres records accepted work, leases/attempts, deduplication, terminal state, and receipts.
- **GAP:** No email queue names, job schemas, worker entry points, retry/backoff policy, dead-letter path, provider rate-limit behavior, sync lease, cancellation boundary, or send reconciliation flow exists.
- **Failure warning:** Redis task streams can disappear or publish late. A terminal event may improve visibility but cannot be the durable evidence that a provider accepted a send.

### Provider adapter and secret boundary

- **CURRENT:** `OAuthConnection` and its database access methods in `guardian/core/db.py` are the nearest provider-connection seam. They are not proof of a Google Workspace mail adapter.
- **CURRENT:** `frontend/src/lib/runtimeConfig.ts` stores non-secret desktop endpoint/share overrides in browser local storage and hydrates Tauri runtime configuration. That storage is explicitly unsuitable for provider credentials.
- **CURRENT:** `src-tauri/src/commands.rs` is the native command surface candidate for desktop-mediated configuration; no email-specific secret command was found.
- **PROPOSED owner:** An Email provider interface owns normalized provider-neutral operations. A Google Workspace adapter implements the first hosted integration. A backend/native secret broker owns token retrieval and rotation; frontend state receives only redacted connection status and capability metadata.
- **GAP:** No provider interface, Google Workspace adapter, capability negotiation, credential broker contract, scope policy, webhook/watch renewal, provider cursor model, alias API boundary, or secret-redaction proof exists.
- **Security constraint:** Provider credentials must never enter frontend persistence, prompts, logs, vector indexes, ordinary audit payloads, or committed files. The inspection did not read credential values or provider state.

### Normalization, synchronization, and idempotency

- **CURRENT:** command-run idempotency and scoped vector insertion show reusable techniques, but not email semantics.
- **PROPOSED owner:** Email normalization owns canonical message/thread/address/attachment forms and preserves raw provider identifiers only in adapter records. Email sync owns cursor advancement in the same durable transaction as normalized writes.
- **GAP:** No canonical message identity, provider-to-canonical mapping, RFC address normalization policy, threading policy, duplicate-delivery key, sync cursor contract, or attachment digest contract exists.
- **Required invariant:** repeated synchronization must not duplicate messages. A database uniqueness key must bind provider account, provider mailbox, and stable provider message identity before cursor advancement.
- **Required invariant:** repeated send requests must not duplicate provider submissions. A durable send-attempt idempotency key must precede provider I/O and reconciliation must distinguish unknown, accepted, failed, and confirmed-delivered states.

### Guardian briefing and human review surfaces

- **CURRENT:** Guardian chat and thread lifecycle live under `frontend/src/features/chat/` and Guardian routes/workers. `GuardianApprovalInbox` is a read-only intervention aggregate; `GuardianThreadApprovalRail` links thread intervention to existing browser approvals when possible.
- **CURRENT:** `frontend/src/App.tsx`, `frontend/src/components/dashboard/DashboardView.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, and `frontend/src/features/settings/SettingsView.tsx` are candidate application-shell surfaces. Persona configuration lives under `frontend/src/features/personaStudio/`.
- **PROPOSED owner:** Guardian owns classification/triage presentation and daily briefing orchestration. Email frontend modules own the secondary inbox, reader, correction, audit, and exceptional-workflow views. Settings may expose redacted provider connection status; Persona Studio may expose routing bindings only after the identity ADR.
- **GAP:** No email brief schema, classification taxonomy, triage correction loop, inbox route, reader, audit view, unread-state contract, or email-specific approval UI exists.
- **Coupling warning:** `approvalInbox.ts` normalizes browser approvals and delegation-run statuses heuristically. Email approvals need a typed source contract, not string matching against operation, target, or reason fields.

### Retrieval, provenance, and untrusted content

- **CURRENT:** `guardian/context/broker.py` and `guardian/context/retrieval_router_policy.py` are retrieval policy seams. `guardian/vector/store.py::VectorStore.search` requires a user identity and filters stored metadata by user; thread and project namespaces are derived from metadata.
- **CURRENT:** `guardian/workers/document_embed_worker.py` attaches user, project, and thread metadata when embedding documents.
- **CURRENT proof targets:** `tests/context/test_retrieval_scope_boundaries.py`, `tests/context/test_retrieval_trace_provenance.py`, `tests/core/test_retrieval_user_isolation_and_widening.py`, `tests/identity/test_retrieval_isolation.py`, and `tests/test_document_rag_retrieval_gate.py` cover adjacent scoping and provenance behavior.
- **PROPOSED owner:** Email retrieval ingestion owns sanitization, trust labels, provenance, attachment extraction policy, user/logical-mailbox scope, and revocation/tombstone propagation. Retrieval policy decides if and how correspondence may enter a prompt.
- **GAP:** No email trust classification, prompt-injection boundary, attachment malware/quarantine contract, quoted-content isolation, retrieval eligibility state, mailbox scope filter, provenance schema, or deletion propagation proof exists.
- **Security constraint:** Email bodies, headers, links, and attachments are external untrusted data. They must never supply executable instructions or silently widen authority.

## Proposed implementation ownership map

| Capability | PROPOSED owning subsystem or role | Required collaboration |
| --- | --- | --- |
| Provider interface and Google adapter | Email provider module | Guardian auth, secret broker, operators |
| Provider secret lifecycle | Backend/native secret broker | Security review; frontend receives redacted status only |
| Routing identities and logical mailboxes | Email identity module | User/persona identity, ADR governance |
| Message and attachment persistence | Email persistence module | Alembic, media safety, retention |
| Read-only synchronization | Email sync worker | Queue, provider adapter, Postgres |
| Normalization and deduplication | Email normalization module | Sync worker, persistence |
| Guardian triage and briefing | Guardian Email orchestration | Classification policy, frontend chat |
| Human inbox and reader | Email frontend feature | Guardian APIs, audit/provenance |
| Retrieval and provenance | Retrieval policy plus Email ingestion | Vector store, attachment processing |
| Drafts and approval snapshots | Email composition/approval module | Command bus, Guardian UI |
| Send attempts | Email send worker | Provider adapter, approval verifier |
| Reconciliation and receipts | Email reconciliation module | Postgres, event/outbox surfaces |
| Desktop configuration | Tauri/backend configuration boundary | Secret broker, Settings UI |

Provider-specific authentication, aliases, folder/label semantics, watch/cursor behavior, routing, throttling, and error translation stay behind the adapter. Core routing identity, logical mailbox, approval, message, and receipt semantics must survive replacement by another hosted provider or a future self-hosted adapter.

## Dependency-ordered target sequence

1. Accept the Email identity, mailbox governance, and provider-adapter ADR.
2. Define provider-neutral domain contracts, trust labels, state machines, idempotency keys, and authorization checks.
3. Add purpose-specific Postgres schemas and migration/rollback proof.
4. Define the secret broker and redacted connection-status surface.
5. Implement a read-only Google Workspace adapter and synchronization worker behind feature gates.
6. Prove normalization, cursor transactions, duplicate suppression, account isolation, and attachment quarantine.
7. Add Guardian triage/briefing contracts and correction receipts.
8. Add secondary inbox/reader/audit surfaces and scoped retrieval ingestion.
9. Add drafts and immutable consequential-action approval snapshots.
10. Add queue-backed sending, durable attempt idempotency, reconciliation, and receipts.
11. Run adversarial, staging, and explicit production-gate Task Specs before any production mailbox cutover.

After steps 1 and 2 are accepted, schema design, frontend information architecture, adapter scaffolding, and test-fixture design may proceed in parallel. Provider access, mailbox/alias creation, DNS changes, staging credentials, and production cutover remain human-required actions under separate informed approval.

## Test and proof targets

The following are required future proof families; none are provided by this inspection:

- Unit: address normalization, provider error translation, trust labeling, state transitions, approval snapshot hashing, redaction, and idempotency key derivation.
- Database: migration upgrade/downgrade, foreign keys, account-scoped uniqueness, cursor/write atomicity, send-attempt uniqueness, immutable approval versions, and tombstones.
- Worker: retry/backoff, cancellation, rate limits, dead-letter handling, crash recovery, duplicate sync, duplicate send request, and unknown provider outcome reconciliation.
- Authorization: cross-user, cross-project, cross-logical-mailbox, persona binding, revoked alias, and collaborator-resource denial.
- Retrieval: untrusted content, malicious attachments, quoted prompt injection, provenance, eligibility, scope, revocation, and deletion propagation.
- API/UI: Guardian brief primary flow; secondary inbox/reader; explicit approval; mutation invalidation; receipt rendering; unavailable/degraded states.
- Adapter contract: provider-neutral fixtures plus Google-specific behavior confined to the adapter.
- Staging: consented non-production identities only, with no collaborator mailbox used as infrastructure.

Adjacent reusable test patterns include `tests/command_bus/`, `tests/test_migrations.py`, `tests/workers/`, the retrieval tests cited above, `frontend/src/features/chat/components/__tests__/GuardianApprovalInbox.test.tsx`, `frontend/src/features/chat/__tests__/GuardianThreadApprovalRail.test.tsx`, and Settings/Persona Studio tests. Their presence is not email proof.

## Risks and unresolved contracts

- Identity ambiguity: `Persona` and `PersonaProfile` have different ownership shapes; an email binding must target the accepted user-owned persona identity, not infer ownership by name.
- Approval fragmentation: browser approvals and command-bus phase-one blocking do not provide immutable email approval snapshots.
- Persistence shortcuts: generic message/job/JSON records would obscure referential integrity and replay safety.
- Event ambiguity: task events and outbox events expose progress or receipts but cannot substitute for provider reconciliation.
- Secret leakage: frontend local storage and ordinary audit/event payloads are prohibited credential targets.
- Retrieval contamination: direct indexing of bodies or attachments could turn hostile correspondence into prompt authority.
- Provider lock-in: Google label, alias, watch, and authentication concepts must not leak into the provider-independent model.
- Migration danger: collaborator accounts must never be discovered, claimed, aliased, or migrated as user-controlled infrastructure.

## ADR impact

A new ADR is required before implementation. Proposed subject:

**Codexify Email User-Owned Routing Identity, Mailbox Governance, and Provider Adapter Contract**

It should decide user-owned agent routing identities, logical mailbox separation without a new principal, persona bindings, accountability, provider abstraction, secret ownership, approval snapshot boundaries, durable correspondence governance, idempotency/reconciliation, retrieval trust, alias revocation/reassignment, and collaborator exclusion. This inspection does not author or accept that ADR.

## Documentation follow-through

This task adds only this inspection. Later Task Specs should author the ADR and then update system overview, flows, data/storage, module ownership, runtime/UI diagrams, provider operator documentation, and release truth only when their respective evidence gates are met. `docs/architecture/00-current-state.md` remains unchanged.

## Known limitations and unproven assumptions

- This is static repository inspection at one commit, not runtime, provider, integration, staging, or production proof.
- No provider capability, mailbox, alias, credential, message, attachment, webhook, or DNS state was inspected.
- Candidate paths may change after ADR and contract review.
- The safe encryption, rotation, and operational deployment of `OAuthConnection` token fields was not proven by this task.
- Existing retrieval and approval tests prove only their named current surfaces, not correspondence safety.
- No email runtime behavior was implemented or activated.
