# Codexify Email Provider Capability and Routing Contract

Status: PROPOSED architecture contract pending human review.

Execution lane: architecture-impact

Task kind: docs

Evidence posture: documented contract

Source task: GitHub Issue #618

Date: 2026-07-23

## Purpose

This contract defines the Codexify Email provider capability discovery surface, routing and alias distinctions, mailbox projection, cursor and watch semantics, throttling, error translation, and the first Google Workspace adapter mapping. It refines ADR-047's provider-adapter boundary into an actionable capability and translation surface without leaking Google-specific concepts into the provider-independent Email domain.

This contract provides documentation proof only. It does not implement Email runtime behavior, provider connectivity, staging readiness, or production readiness.

## Governing Authority

- ADR-047: Codexify Email User-Owned Routing Identity, Mailbox Governance, and Provider Adapter Contract — accepted and governs downstream bounded contract work.
- `docs/architecture/provider-capability-contract.md` — defines declared, verified, and effective capability layers and requires routing by effective capability rather than provider name.
- `docs/architecture/00-current-state.md` — release truth; Email remains in inspection and planning only.

## Truth Boundary

### CURRENT

- ADR-047 is accepted on GitHub `main`.
- `OAuthConnection` (`guardian/db/models.py`) is a user-scoped provider-connection record with `(user_id, provider, mode)` uniqueness, encrypted token fields, scoped status, and expiry. It is not an email routing identity, mailbox authority model, or collaborator-resource authorizer.
- `Persona` (`guardian/db/models.py`) has `user_id` and optional `project_id`. `PersonaProfile` is a distinct profile model with different ownership semantics.
- No Email runtime path, provider adapter, mailbox connection, alias integration, synchronization, or sending exists.
- The supported release posture remains governed by `docs/architecture/00-current-state.md`.
- Google Workspace is the selected first hosted provider for the Codexify Email campaign.

### PROPOSED

- A provider-independent Email capability vocabulary and state machine.
- A Google Workspace adapter mapping that keeps provider-specific IDs, error vocabulary, label semantics, cursor mechanics, and watch behavior inside the adapter.
- Capability discovery, verification, and effective-capability derivation after policy, credentials, consent, environment, and proof posture are applied.
- Routing by effective capability, not by provider name alone.

### FUTURE

- Replacement of Google Workspace with another hosted provider.
- Simultaneous providers.
- A self-hosted transport adapter.
- Production mailbox cutover and collaborator opt-in provider connections.

None of these may be inferred as current from this document.

## Relationship to the Provider Capability Contract

This contract extends `docs/architecture/provider-capability-contract.md` for the Email provider domain. It preserves:

- `declared_capabilities` — what the provider, runtime, or adapter advertises.
- `verified_capabilities` — what Codexify has checked with discovery, health, or probe evidence.
- `effective_capabilities` — what the workflow engine may rely on after applying user authority, OAuth scope, provider policy, administrator privilege, consent, feature gate, and current proof state.

Routing decisions must use `effective_capabilities`. Provider-name matching alone is insufficient. A capability that is declared but not verified must be surfaced as such. A capability that is verified but policy-disallowed must be excluded from effective routing. Missing, ambiguous, expired, revoked, or policy-disallowed capabilities fail closed.

## Conceptual Email Provider Capability Record

A provider capability record for Email must conceptually carry at least the following without prescribing a database schema:

| Field | Meaning |
|---|---|
| `provider_id` | Canonical provider identity. |
| `provider_account_id` | Provider-account identity scoped to the owning user and connection. |
| `owning_user_id` | Codexify user identity. |
| `adapter_version` | Adapter or contract version for compatibility tracking. |
| `discovery_source` | How the capability data was obtained (static contract, OAuth metadata, probe, admin response). |
| `observed_at` | Timestamp of the most recent observation. |
| `declared_capabilities` | Capabilities advertised by the provider, adapter, or static contract. |
| `verified_capabilities` | Capabilities confirmed by discovery, health, or probe evidence. |
| `effective_capabilities` | Capabilities available after policy, scope, consent, and proof filtering. |
| `granted_scope_posture` | Redacted authorization scope posture (scope family, not token values). |
| `administrator_required` | Capabilities that require administrator authority beyond the user's token. |
| `read_only_capabilities` | Observation-only capability subset. |
| `mutation_capabilities` | Reversible mutation capability subset. |
| `consequential_capabilities` | Capabilities whose exercise requires explicit user approval per ADR-047. |
| `observed_quota` | Quota or throttle observations (families, not hardcoded numeric limits). |
| `cursor_support` | Whether the provider supports incremental history cursors. |
| `watch_support` | Whether the provider supports push-notification subscriptions. |
| `limitations` | Known capability limitations, degradations, or revocations. |
| `limitation_reason` | Why a capability is limited (scope omission, policy, expiration, error). |
| `provenance` | Actor, source, and governing decision for the capability record. |
| `proof_classification` | Static, probed, live-verified, or stale. |

## Email Capability Families

The following families describe what an Email provider may support, expressed semantically without claiming final canonical runtime tokens. Every capability belongs to exactly one authority class and carries an initial-read-only-gate posture.

### Authority Classes

- **OBSERVE**: read-only observation. No mutation of provider state.
- **MUTATE**: reversible mutation of provider state (label creation, draft save).
- **CONSEQUENTIAL**: mutation with durable external effect requiring explicit user approval per ADR-047 (send, delete, alias creation).
- **ADMIN**: operation requiring administrator authority beyond the user's OAuth token.

### Initial Read-Only Gate

The initial Codexify Email implementation is read-only. Only OBSERVE-class capabilities are permitted in the first gate. MUTATE and CONSEQUENTIAL capabilities remain contract-defined but disabled until later gates with explicit approval, idempotency, and reconciliation proof.

### Capability Families

| Capability Family | Authority Class | ADR-047 Approval Required | Initial Read-Only Gate |
|---|---|---|---|
| Account profile verification | OBSERVE | No | Permitted |
| Mailbox or label discovery | OBSERVE | No | Permitted |
| Bounded message listing | OBSERVE | No | Permitted |
| Message fetch (metadata and body) | OBSERVE | No | Permitted |
| Incremental history synchronization | OBSERVE | No | Permitted |
| Push-watch subscription and renewal | OBSERVE | No | Permitted |
| Attachment metadata and byte retrieval | OBSERVE | No | Permitted |
| Provider health, quota, and diagnostic observation | OBSERVE | No | Permitted |
| Message label or flag mutation | MUTATE | No | Disabled |
| User-label creation, update, and deletion | MUTATE | No | Disabled |
| Draft creation and revision | MUTATE | No | Disabled |
| Directory user-alias listing | OBSERVE | No | Permitted |
| Directory user-alias creation | CONSEQUENTIAL | Yes | Disabled |
| Directory user-alias deletion | CONSEQUENTIAL | Yes | Disabled |
| Gmail send-as listing | OBSERVE | No | Permitted |
| Gmail send-as creation | CONSEQUENTIAL | Yes | Disabled |
| Gmail send-as verification | MUTATE | No | Disabled |
| Gmail send-as update | CONSEQUENTIAL | Yes | Disabled |
| Gmail send-as deletion | CONSEQUENTIAL | Yes | Disabled |
| Message or draft sending | CONSEQUENTIAL | Yes | Disabled |
| Sent observation and reconciliation | OBSERVE | No | Permitted |
| Message deletion or permanent removal | CONSEQUENTIAL | Yes | Disabled |

### Unsupported or Unavailable Operations

A capability may be:
- **unsupported** by the provider entirely;
- **unavailable** because of scope, policy, or administrator restriction;
- **degraded** because of quota, throttling, or transient error.

Unsupported and unavailable capabilities must fail closed with a visible reason. Degraded capabilities may operate at reduced throughput with explicit backpressure.

## Provider-Independent Adapter Responsibilities and Operation Envelopes

### Adapter Responsibilities

The Email core domain owns normalized correspondence meaning. Provider adapters own:

- provider authentication and capability discovery;
- provider accounts and provider-scoped resource identities;
- aliases, folders, labels, filters, and routing operations;
- cursors, history identifiers, watches, and invalidation behavior;
- throttling, quotas, retries, and provider error translation;
- sending APIs or SMTP submission behavior; and
- Sent observation and reconciliation mechanics.

### Operation Envelopes

Every normalized adapter operation must carry at minimum:

| Envelope Field | Meaning |
|---|---|
| `owning_user_id` | Authenticated Codexify user identity. |
| `provider_connection_id` | Provider connection reference (not credentials). |
| `operation_id` | Durable operation identity for idempotency where applicable. |
| `requested_capability` | Capability family being exercised. |
| `logical_mailbox_scope` | Optional logical mailbox narrowing. |
| `routing_identity_scope` | Optional routing identity narrowing. |
| `provider_resource_refs` | Provider resource identifiers confined to adapter metadata. |
| `authorization_snapshot_ref` | Reference to the governing authorization and policy snapshot. |
| `page_or_batch_params` | Bounded page size, page token, or batch limits. |
| `provider_observed_at` | Provider timestamp for the observation. |
| `normalized_result` | Provider-independent result or failure class. |
| `retry_guidance` | Safe, unsafe, conditional, or delayed retry classification. |
| `ambiguity_posture` | Whether the provider outcome is known, unknown, or ambiguous. |
| `provenance` | Actor, source, and observation provenance. |
| `redaction_posture` | What must be redacted before audit, log, or frontend exposure. |

### Agent Access Boundary

Raw provider commands (Gmail API methods, Admin SDK operations, IMAP commands, SMTP submission) must not be exposed directly to agents as ambient tools. Future agents may receive semantic governed operations only after authorization, approval, and command-bus contracts exist.

## Google Workspace Adapter Mapping

Google Workspace is the first intended adapter, not a core dependency. Google-specific identifiers and error vocabulary remain inside the Google Workspace adapter or provider observation records.

### Distinct Concepts

The following must not be silently conflated:

| Concept | Owner | Description |
|---|---|---|
| Google Workspace account | Google Workspace tenant | A licensed Gmail mailbox within a Google Workspace domain. |
| Directory user alias | Admin SDK Directory API | An alternate email address for a Directory user, administered through `users.aliases`. May require administrator authority. |
| Gmail send-as identity | Gmail API `users.settings.sendAs` | An address the authenticated user may send from, including primary, default, custom-from, and verification posture. |
| Gmail system label | Gmail API `users.labels` | A predefined label (e.g., `INBOX`, `SENT`, `TRASH`, `SPAM`, `UNREAD`, `STARRED`, `IMPORTANT`, `DRAFT`, `CATEGORY_*`). System labels are provider-owned and cannot be created or deleted by users. |
| Gmail user label | Gmail API `users.labels` | A user-created label with a provider-scoped `id` and mutable `name`, `messageListVisibility`, and `labelListVisibility`. |
| Codexify logical mailbox | Codexify Email domain | A provider-independent routing and presentation construct scoped to one user. May project onto provider labels or folders. |
| Codexify user-owned routing identity | Codexify Email domain | A durable, user-owned identity record per ADR-047. May bind to a provider account, a Gmail send-as identity, a Directory alias, or a provider address. |

### Directory Alias Boundaries

- A Directory user alias is administered through the Admin SDK Directory API (`users.aliases`). Creating or deleting a Directory alias may require administrator authority beyond an ordinary user's OAuth token.
- A Directory alias does not by itself establish a Codexify routing identity, logical mailbox, send approval, or independent principal.
- Listing Directory aliases is an OBSERVE operation permitted in the initial read-only gate. Creation and deletion are CONSEQUENTIAL operations requiring explicit user approval and possible administrator authority.

### Gmail Send-As Identity Boundaries

- A Gmail send-as identity is managed through the Gmail API `users.settings.sendAs` resource. It represents an address the authenticated user may send from.
- A send-as identity has a `sendAsEmail`, `displayName`, `isDefault`, `isPrimary`, `verificationStatus`, and `treatAsAlias` posture.
- A send-as identity does not by itself prove inbound routing, Directory alias ownership, Codexify ownership, or user consent.
- A pending verification state must be surfaced explicitly and must not be treated as a confirmed identity.

### Google Workspace Capability Mapping

| Provider Operation | Google API Family | Authority Class | Administrator Required | Initial Read-Only Gate |
|---|---|---|---|---|
| Get Gmail profile | `users.getProfile` | OBSERVE | No | Permitted |
| List Gmail labels | `users.labels.list` | OBSERVE | No | Permitted |
| Get Gmail label | `users.labels.get` | OBSERVE | No | Permitted |
| Create Gmail user label | `users.labels.create` | MUTATE | No | Disabled |
| Update Gmail user label | `users.labels.update` | MUTATE | No | Disabled |
| Delete Gmail user label | `users.labels.delete` | MUTATE | No | Disabled |
| List messages | `users.messages.list` | OBSERVE | No | Permitted |
| Get message | `users.messages.get` | OBSERVE | No | Permitted |
| List history | `users.history.list` | OBSERVE | No | Permitted |
| Create watch | `users.watch` | OBSERVE | No | Permitted |
| Stop watch | `users.stop` | MUTATE | No | Disabled |
| Get attachment | `users.messages.attachments.get` | OBSERVE | No | Permitted |
| List send-as identities | `users.settings.sendAs.list` | OBSERVE | No | Permitted |
| Get send-as identity | `users.settings.sendAs.get` | OBSERVE | No | Permitted |
| Create send-as identity | `users.settings.sendAs.create` | CONSEQUENTIAL | No | Disabled |
| Verify send-as identity | `users.settings.sendAs.verify` | MUTATE | No | Disabled |
| Update send-as identity | `users.settings.sendAs.update` | CONSEQUENTIAL | No | Disabled |
| Delete send-as identity | `users.settings.sendAs.delete` | CONSEQUENTIAL | No | Disabled |
| Create draft | `users.drafts.create` | MUTATE | No | Disabled |
| Send message or draft | `users.messages.send` / `users.drafts.send` | CONSEQUENTIAL | Yes (ADR-047) | Disabled |
| List Directory user aliases | Admin SDK `users.aliases.list` | OBSERVE | Possibly | Permitted |
| Create Directory user alias | Admin SDK `users.aliases.insert` | CONSEQUENTIAL | Usually | Disabled |
| Delete Directory user alias | Admin SDK `users.aliases.delete` | CONSEQUENTIAL | Usually | Disabled |

No capability is claimed as verified until live proof exists. This table reflects contract design only.

## Mailbox Projection Rules

- Provider labels and folders are adapter observations. They retain provider identity and provenance.
- Gmail system labels (e.g., `INBOX`, `SENT`, `TRASH`) and user labels each retain their provider-scoped `id`, `name`, and visibility metadata.
- One provider message may project into multiple labels without being duplicated as multiple canonical messages. The canonical message identity is provider-scoped and message-unique; label membership is an N:M projection.
- A Codexify logical mailbox may project onto one or more provider labels or folders. Logical mailbox membership cannot widen user authority.
- Provider label deletion or rename must not silently destroy Codexify routing identity, logical mailbox membership, or audit history. A label deletion or rename event enters provider observation history and may trigger logical-mailbox reconciliation but does not delete canonical messages.

## Cursor and Incremental Synchronization Semantics

- Gmail `historyId` is a provider cursor, not a canonical message identity. History IDs are increasing but not guaranteed contiguous.
- A `history.list` response carries a `historyId` representing the current mailbox state at the time of the response. That ID becomes the next request's `startHistoryId` for incremental polling.
- An invalid or expired history cursor enters an explicit recovery state. Recovery requires a bounded full resynchronization (`messages.list`) against durable message uniqueness before cursor advancement resumes.
- No cursor is advanced until the corresponding normalized message state is durably committed to Postgres and replay-safe.
- Pagination completion and the returned current history state must be represented explicitly. A partially consumed history page must not silently appear complete.

## Push-Watch Semantics

- Gmail watches (`users.watch`) are created per mailbox and return a `historyId` plus an `expiration` time (typically 7 days for Gmail). Watches are renewable and expire.
- Watch renewal before expiration is required for continuous push delivery. Expired watches produce no notifications; the system must detect expiration through `stop` response, explicit expiry check, or watch-list inspection.
- Google Cloud Pub/Sub is the notification delivery mechanism. A Pub/Sub notification is a wake-up hint carrying a `historyId` and optional `emailAddress`. It is not a complete durable correspondence truth, message payload, or synchronization completion receipt.
- Watch creation, renewal, expiration, stop, delivery lag, duplication, and loss must each have visible provider-observation states in Postgres.
- Notification replay or loss must be recoverable through durable cursor reconciliation. A received notification triggers a `history.list` from the last known durable `historyId`; the sync worker must not trust the notification's `historyId` as the sole synchronization signal.
- No Pub/Sub setup, topic creation, subscription, or webhook endpoint is implemented by this contract.

## Throttling and Backpressure Doctrine

- The adapter must honor per-user, per-project, bandwidth, concurrency, and method-cost limits where the provider or Codexify policy imposes them.
- Gmail API quota units (`quotaUser` parameter, per-user and per-project rate limits) must be respected. Hardcoded current numeric quotas must not enter the provider-independent contract; quota families and observation posture are sufficient.
- The adapter must classify provider retry guidance rather than retrying every error. Transient, retryable errors use bounded exponential backoff with jitter. Non-retryable errors surface immediately.
- Account-scoped concurrency must be serialized or bounded where provider constraints require it. Multiple simultaneous writes to the same Gmail mailbox, for example, must be coordinated through Postgres-based lease or lock mechanisms.
- Cooldown or degraded state must surface visibly. An unbounded retry storm must not be created regardless of provider 429, 5xx, or timeout frequency.
- Backpressure from provider throttling propagates to queue workers as bounded delay, not as unbounded queue growth. Dead-letter or explicit blocked-task states are required for persistently throttled operations.

## Normalized Error Families

The following error families translate provider-specific errors into provider-independent semantic categories. They are contract-level distinctions, not final runtime tokens registered by this document.

| Error Family | Retry Safety | Meaning |
|---|---|---|
| `invalid_request` | Unsafe | Malformed parameters, unsupported operation, or contract violation. |
| `authentication_expired` | Requires reauthorization | OAuth token expired, revoked, or invalid. |
| `insufficient_scope` | Requires reauthorization | OAuth scope missing for the requested capability. |
| `administrator_required` | Requires administrator action | Operation requires admin privilege beyond user token. |
| `domain_policy_blocked` | Unsafe | Domain-wide policy prevents the operation. |
| `resource_not_found` | Unsafe | Target resource ID does not exist or was revoked. |
| `cursor_expired` | Requires full resync | `historyId` is too old or invalid; full resynchronization required. |
| `verification_pending` | Conditional | Send-as or alias verification not yet complete. |
| `rate_limited` | Delayed | Provider 429 or quota exhaustion; retry after backoff. |
| `concurrency_limited` | Delayed | Provider concurrency limit; serialize and retry. |
| `transient_unavailable` | Retryable with backoff | Provider 5xx, temporary outage, or DNS/network blip. |
| `permanent_rejection` | Unsafe | Provider permanent error; do not retry. |
| `network_timeout` | Conditional | No response before submission confirmation; provider outcome ambiguous. |
| `outcome_ambiguous` | Requires reconciliation | Submission may have succeeded or failed; reconcile before retry. |
| `normalization_failure` | Unsafe | Provider response cannot be mapped to a canonical record. |

### Retry Safety Classifications

- **Safe**: Retry with bounded exponential backoff and jitter. The operation is idempotent or the provider guarantees at-most-once semantics.
- **Unsafe**: Do not retry. The error is permanent, policy-driven, or requires human or administrator action.
- **Conditional**: Retry may be safe, but the provider outcome is ambiguous. Reconcile provider state before retrying. Blind resubmission after `network_timeout` or `outcome_ambiguous` is prohibited.
- **Delayed**: Retry after backoff plus jitter. Rate-limiting or concurrency errors require cooldown, not immediate retry.
- **Requires reauthorization**: Do not retry until OAuth scope or token is refreshed, consent is re-obtained, or a new authorization grant is issued.
- **Requires administrator action**: Do not retry until an administrator explicitly authorizes the operation.
- **Requires full resynchronization**: Do not retry the incremental operation. Perform a bounded full resync before cursor advancement resumes.

## Provider Acceptance vs Final Codexify Completion

Provider acceptance of a request (HTTP 200 from Gmail API, queue acceptance of a send, or Pub/Sub delivery of a notification) is not Codexify completion.

Sending remains outside the initial read-only implementation gate. When sending is enabled in a later gate, it cannot be considered successful without:

1. An immutable approval snapshot per ADR-047.
2. A durable send-attempt idempotency record.
3. A provider outcome classification (accepted, rejected, or ambiguous).
4. Post-send Sent-folder reconciliation.
5. A durable receipt stored in Postgres.

Provider acceptance alone does not prove delivery, Sent-folder visibility, or final reconciliation. Ambiguous outcomes must remain visible and unresolved until reconciliation evidence confirms acceptance or rejection.

## Capability Discovery and Cache Invalidation

- Discovery observations are timestamped and scoped to one user and one provider connection.
- Capability state may be derived from static adapter contracts, OAuth scope metadata, probe responses, or administrator-configured posture.
- Scope changes, token refresh failure, administrator-policy changes, provider revocation, watch expiration, or failed probes can invalidate verified or effective capability state.
- Stale capability state must not authorize a consequential operation. An operation classified as CONSEQUENTIAL must re-verify its effective capability posture before execution.
- Postgres must eventually own durable capability and provider-observation truth when implemented. In-memory or Redis state is coordination only.

## Redacted Frontend and Operator Visibility

Surfaces visible to frontend or operator tools may show:

- capability availability (present, absent, degraded);
- capability limitation reason (scope, policy, expiration, admin-required);
- last verification time;
- degraded state and required user or admin action;
- proof posture (static, probed, live-verified, stale).

Surfaces must never expose:

- OAuth access tokens or refresh tokens;
- raw authorization headers;
- secret-bearing provider API payloads;
- provider credentials of any form.

This requirement is non-negotiable per ADR-047 and the security boundary decision.

## Failure-Mode Examples

### Expired History Cursor

A `history.list` call returns `404` with `historyNotFound`. The adapter classifies this as `cursor_expired`. Recovery requires a bounded `messages.list` full resynchronization against durable message uniqueness. Once complete, the new `historyId` is committed durably and cursor-based incremental sync resumes. Messages already known by provider ID are not duplicated.

### Expired Watch

The watch expiration time passes without renewal. Pub/Sub notifications stop arriving. The system detects expiration through scheduled watch inspection. Watch state transitions to `expired` in Postgres. A new `users.watch` call creates a fresh watch with a current `historyId`. The sync worker reconciles any gap between the last durable `historyId` and the new watch `historyId`.

### Duplicate Notification

Pub/Sub delivers the same `historyId` notification more than once. The sync worker processes `history.list` from the last known durable cursor. Idempotent message insertion per `(user_id, provider_connection_id, provider_mailbox, provider_message_id)` prevents duplicate canonical messages. The duplicate notification produces no new writes.

### Missing OAuth Scope

A capability request requires `https://mail.google.com/` scope, but the OAuth grant only includes `https://www.googleapis.com/auth/gmail.readonly`. The adapter classifies this as `insufficient_scope`. The operation fails closed. Frontend surfaces the missing scope as a required reauthorization action without exposing token values.

### Administrator-Only Alias Operation Attempted by Ordinary User Token

A request to create a Directory user alias is made with an OAuth token that lacks administrator privilege. The Admin SDK returns `403` with `insufficientAdminPrivileges`. The adapter classifies this as `administrator_required`. The operation fails closed and surfaces the admin-required posture. No retry occurs without explicit administrator action.

### Send-As Verification Pending

A Gmail send-as identity has `verificationStatus: pending`. The adapter classifies this as `verification_pending`. The identity may be observed but must not be used for sending or treated as a confirmed Codexify routing identity. Frontend surfaces the pending state without exposing verification tokens or verification email content.

### Label Renamed or Deleted

A user label that projected onto a Codexify logical mailbox is renamed or deleted at the provider. The provider observation records the change. The Codexify logical mailbox projection is updated but canonical messages are not deleted. A deleted label's messages remain accessible through other label projections or logical mailbox views. Audit history retains the label lifecycle.

### Provider Throttling (429)

A `users.messages.list` call returns HTTP `429` with `rateLimitExceeded`. The adapter classifies this as `rate_limited`. The sync worker applies bounded exponential backoff with jitter and surfaces a degraded-state indicator. If throttling persists, the operation enters a blocked state rather than retrying indefinitely. No other user's throughput is affected.

### Network Loss After Consequential Provider Submission

A `users.messages.send` call times out after the TCP handshake but before an HTTP response arrives. The adapter classifies this as `network_timeout` with `outcome_ambiguous`. The send-attempt record enters `provider_outcome_unknown`. A subsequent Sent-folder reconciliation attempt determines whether the message was accepted. Blind resubmission is prohibited. The ambiguous state remains user-visible until reconciliation resolves it.

## Rejected Alternatives

1. **Route by provider name alone.** Rejected because capability presence varies by account, scope, policy, administrator posture, and proof state. Provider-name matching is necessary for adapter selection but insufficient for routing decisions.

2. **Treat all aliases as one resource type.** Rejected because Directory user aliases, Gmail send-as identities, and Codexify routing identities have distinct ownership, authority, lifecycle, verification, and API surfaces. Conflating them would produce silent authority errors and cross-user leakage.

3. **Treat labels as canonical mailboxes or duplicate messages per label.** Rejected because a single provider message belongs to the mailbox once; label membership is an N:M projection. Duplicating messages per label would break deduplication, inflate storage, and confuse canonical message identity.

4. **Store Google error text as core domain state.** Rejected because Google-specific error messages, codes, and JSON structures are provider adapter concerns. The domain must receive normalized error families with retry guidance to survive provider replacement.

5. **Treat Pub/Sub delivery as synchronization completion.** Rejected because Pub/Sub notifications are wake-up hints carrying a `historyId` and optional metadata. They do not contain message payloads, do not prove delivery completeness, and can duplicate or arrive late. Durable `history.list` reconciliation is the only completion evidence.

6. **Treat a declared capability as verified.** Rejected because declared capabilities are static advertising without runtime proof. A provider may declare send-as support while the current connection lacks the required OAuth scope, administrator privilege, or verified identity.

7. **Retry every 4xx, 5xx, timeout, or ambiguous outcome.** Rejected because `invalid_request`, `resource_not_found`, `domain_policy_blocked`, and `permanent_rejection` are not safe to retry. `network_timeout` after a consequential submission requires reconciliation before retry. Indiscriminate retry produces duplicate sends and suppresses real failure signals.

8. **Expose raw provider APIs to agents.** Rejected because provider operations require adapter, capability, approval, idempotency, and policy enforcement per ADR-047. Raw API exposure would bypass the authority boundary, approval contract, and error normalization.

9. **Infer collaborator consent from tenant membership.** Rejected because Google Workspace tenant co-membership does not transfer mailbox authority, consent, or operator control. Collaborator consent requires explicit, informed, revocable authorization per ADR-047.

## Dependency Follow-Through

This contract enables the following dependent work, listed in dependency order:

1. Provider-neutral correspondence domain and schema contract.
2. Authentication and secret-custody contract.
3. Operator-controlled Google Workspace staging proof.
4. Google Workspace adapter implementation (read-only gate first).
5. Synchronization and duplicate-suppression proof.
6. Approval, sending, reconciliation, and receipt contracts.
7. Operator and UI documentation for provider connection, capability posture, and error visibility.

No dependent contract may claim implementation is complete until its own proof gates are satisfied.

## Non-Goals

This task does not implement or authorize:

- provider adapter code, Python interfaces, or protocol implementations;
- SQLAlchemy models, Alembic migrations, or Postgres schema changes;
- canonical runtime-token registration;
- OAuth implementation, secret storage, or credential handling;
- Google Cloud project, OAuth client, Pub/Sub topic, subscription, or webhook configuration;
- mailbox connection, verification, or provider state access;
- alias, send-as, label, filter, routing, draft, send, delete, move, or mark-read operations;
- IMAP or SMTP implementation;
- production MX or DNS changes;
- collaborator mailbox access;
- `docs/architecture/00-current-state.md` updates; or
- any claim that Codexify Email is currently supported or live.

## Compatibility and Migration Impact

No runtime or data migration occurs.

This contract preserves:
- future provider replacement without changing core routing identity semantics;
- account-scoped capability records;
- historical routing and provider observations;
- safe cursor recovery after expiry;
- capability invalidation on scope change, token failure, or policy update;
- OAuth-scope evolution without breaking the capability model;
- rollback before production mailbox cutover; and
- strict exclusion of collaborator infrastructure.

## Source Evidence

Repository sources:
- GitHub Issues #600, #606, #608, #610
- `docs/Campaign/codexify-email-agent-native-campaign-index.md`
- `docs/architecture/inspections/codexify-email-implementation-targets.md`
- `docs/architecture/adr/047-codexify-email-routing-identity-mailbox-governance-provider-adapter-contract.md`
- `docs/architecture/provider-capability-contract.md`
- `docs/architecture/00-current-state.md`
- `docs/security/auth-boundary-decision.md`
- `guardian/db/models.py`

Official Google provider documentation, verified 2026-07-22:
- Gmail API overview: `https://developers.google.com/workspace/gmail/api/guides`
- Gmail history list: `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list`
- Gmail watch: `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/watch`
- Gmail labels resource: `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels`
- Gmail send-as resource: `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.settings.sendAs`
- Gmail alias and signature guide: `https://developers.google.com/workspace/gmail/api/guides/alias_and_signature_settings`
- Admin SDK Directory user aliases: `https://developers.google.com/workspace/admin/directory/reference/rest/v1/users.aliases`
- Gmail error handling: `https://developers.google.com/workspace/gmail/api/guides/handle-errors`
- Gmail usage limits: `https://developers.google.com/workspace/gmail/api/reference/quota`
- Gmail OAuth scopes: `https://developers.google.com/workspace/gmail/api/auth/scopes`
