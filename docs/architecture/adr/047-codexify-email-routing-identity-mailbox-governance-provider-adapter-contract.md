---
tags:
* architecture
* adr
* email
* identity
* provider-adapter
* approval
  aliases:
* ADR-047
* Codexify Email User-Owned Routing Identity Mailbox Governance and Provider Adapter Contract
---

# ADR-047: Codexify Email User-Owned Routing Identity, Mailbox Governance, and Provider Adapter Contract

## Status

Accepted. Resonant Jones gave human architecture acceptance through GitHub
Issue #606 on 2026-07-19. Dependent bounded contract Task Specs may rely on
this decision.

## Date

2026-07-19

## Context

The Codexify Email campaign and implementation-target inspection establish a
proposed agent-native correspondence subsystem. Guardian briefing and
agent-mediated triage are the primary interaction model. A human inbox, reader,
draft review, approval, correction, receipt, and audit surface remains mandatory
as a secondary control and exceptional-workflow path.

Repository truth contains adjacent identity, OAuth connection, command-bus,
approval, Postgres, Redis, retrieval, frontend, and Tauri seams. None is an
Email runtime implementation. In particular:

- Guardian authentication resolves a human user identity.
- `guardian/db/models.py::Persona` is user-scoped and optionally project-scoped.
- `PersonaProfile` is distinct and cannot silently establish the same ownership.
- `OAuthConnection` is user-scoped provider-connection infrastructure, not an
  email identity, mailbox, or routing model.
- command-bus records govern invocation, actor, subject, idempotency, policy,
  provenance, and run events.
- browser approvals are browser-operation records, not email approvals.
- Postgres is durable application truth; Redis queues and events provide
  operational coordination and visibility.
- retrieval has adjacent user-scoping and provenance seams but no email trust
  or indexing contract.

The architecture must decide ownership and failure semantics before schemas,
provider connections, synchronization, retrieval ingestion, approval, or
sending can begin.

## Truth boundary

### CURRENT

- GitHub `main` is canonical for accepted code and architecture contracts.
- VaultNode is the canonical runtime and audit authority.
- The adjacent repository seams described above exist, but no Codexify Email
  runtime path exists.
- The supported release posture remains governed by
  `docs/architecture/00-current-state.md`.

### PROPOSED

- User-owned routing identities and provider-independent logical mailboxes.
- Provider adapters, provider connections, synchronization, normalized
  correspondence, drafts, immutable approval snapshots, sending,
  reconciliation, receipts, Guardian briefing, and mandatory human review.
- Google Workspace as the first intended hosted-provider adapter.

### FUTURE

- Replacement or simultaneous use of hosted providers.
- A self-hosted transport adapter.
- Production mailbox migration and collaborator opt-in connections.
- Autonomous sending or deletion, subject to a superseding ADR and explicit
  proof and human authorization.

This ADR establishes architecture doctrine only. It does not implement or
prove Email runtime support, provider connectivity, staging readiness, or
production readiness.

## Decision

Codexify adopts one human-account authority boundary for Email. Agent addresses
and logical mailboxes are subordinate routing and presentation constructs. The
core domain owns normalized correspondence meaning; provider adapters own
provider-specific mechanics. Consequential correspondence actions require an
Email-domain immutable approval record before command-bus invocation may
execute them.

Ambiguous identity, consent, approval, provider outcome, or ownership fails
closed and remains visible for human review.

## Human authority and canonical persona binding

The authenticated human user is the sole mailbox authority and accountable
principal. A persona is not a sovereign mailbox owner, credential holder,
independent legal principal, or source of infrastructure authority.

A routing identity may bind only to:

1. its owning human user; and
2. optionally, a `guardian/db/models.py::Persona` owned by that same user; and
3. optionally, a project within that user's authorized scope.

A future identity contract may explicitly supersede `Persona`, but until then:

- `PersonaProfile`, display names, labels, public email strings, and
  provider-side aliases do not establish ownership;
- a persona or project binding cannot change the owning user;
- every lookup and mutation must resolve the owning user first; and
- missing, conflicting, or ambiguous ownership fails closed.

## User-owned routing identity

An agent address is a durable user-owned routing identity, not an independent
principal. Its provider-independent record must contain at minimum:

- owning user identity;
- optional canonical persona identity;
- optional project scope;
- provider connection and provider-account reference;
- public address;
- provider-side alias or routing reference when present;
- logical mailbox target;
- lifecycle status;
- activation, revocation, and reassignment history; and
- audit provenance identifying the actor, source, and governing decision.

Address text is not the durable identity key. Revocation and reassignment create
new history rather than rewriting prior ownership. Reassignment must fail if it
would silently transfer another user's or collaborator's address, data, or
provider resource.

## Logical mailbox governance

A logical mailbox is a provider-independent routing and presentation construct.
It may project onto provider folders, labels, filters, aliases, or local views,
but it does not create a separate account, credential, authority boundary, or
accountable principal.

Logical separation may scope triage, retrieval eligibility, display, drafts,
and receipts. Authorization always begins at the owning human account and then
narrows to the logical mailbox, optional persona, and optional project. Logical
mailbox membership cannot widen user authority.

## Collaborator consent boundary

Collaborators remain separate principals. Tenant or organization membership
does not imply mailbox consent, shared ownership, or operator authority.

- Collaborator accounts, aliases, credentials, messages, settings, and provider
  resources are never user-controlled infrastructure by default.
- Participation requires explicit informed consent and a separately governed,
  authenticated, account-scoped provider connection.
- Consent must be specific, observable, and revocable.
- Revocation stops future credential and provider access before synchronized
  data removal, export, retention, or tombstone handling begins.
- Existing synchronized records retain consent and provenance history required
  for audit, subject to the later retention and deletion contract.

No collaborator mailbox may be used as staging infrastructure merely because it
shares a provider tenant.

## Provider adapter boundary

The Email core domain owns:

- user and routing identity semantics;
- logical mailboxes;
- normalized messages, threads, participants, and attachments;
- drafts and revisions;
- approval snapshots;
- sync and send request identities;
- provider-neutral outcomes, reconciliation, and receipts; and
- retention, export, revocation, and deletion semantics.

Adapters own:

- provider authentication and capability discovery;
- provider accounts and provider IDs;
- aliases, folders, labels, filters, and routing operations;
- cursors, history identifiers, watches, and invalidation behavior;
- throttling, quotas, retries, and provider error translation;
- sending APIs or SMTP submission behavior; and
- Sent observation and reconciliation mechanics.

Google Workspace is the first intended adapter, not a core dependency. Google
labels, aliases, history cursors, watches, authentication details, and error
vocabulary must not enter the provider-independent domain contract. A later
hosted or self-hosted adapter must preserve the same user authority, routing
identity, approval, idempotency, reconciliation, and receipt meanings.

Raw IMAP, SMTP, provider SDK, or alias operations are adapter capabilities. They
must not be exposed directly to agents as ambient tools.

## Provider connection and secret custody

A backend/native secret broker owns provider-secret custody, retrieval,
rotation, and revocation. `OAuthConnection` may be reused or extended only as a
provider-connection record; it must not become a routing identity or proof of
mailbox authority.

Frontend surfaces receive only redacted connection state, capability metadata,
expiry/revocation posture, and actionable non-secret diagnostics. Provider
credentials must never enter frontend persistence, prompts, logs, vector
indexes, ordinary audit payloads, fixtures, proof artifacts, or committed files.

OAuth is the preferred durable Google Workspace authentication path unless
later evidence requires a superseding ADR. An app password may be used only as
an explicitly operator-managed staging mechanism under a separately approved
Task Spec. It is not implicit production doctrine and must not be persisted or
handled through ordinary frontend configuration.

## External untrusted content doctrine

Email bodies, headers, links, quoted text, MIME structure, and attachments are
external untrusted evidence. They cannot:

- become system or developer instruction;
- grant tool or provider permission;
- approve an action;
- change identity or routing ownership;
- override Guardian or command-bus policy; or
- mutate durable memory.

Durable memory mutation from correspondence is a separate governed action that
requires explicit user consent and provenance. Retrieval policy remains a
backend control plane under ADR-004, not a prompt or provider-side heuristic.

Any retrieval envelope must preserve source provider, provider connection,
owning user, canonical message and thread identity, sender, timestamps, logical
mailbox scope, trust classification, content boundaries, and transformation
provenance. Quoted or forwarded material must remain distinguishable from the
current sender's authored content.

Attachment extraction and indexing require allowlisted processors, bounded
resource handling, malware/quarantine posture, and an explicit eligibility
state. Ineligible content remains excluded rather than silently indexed.

## Immutable approval snapshot

The Email domain owns durable draft revisions, send requests, and immutable
approval state. The command bus governs invocation and policy enforcement after
the Email-domain approval contract is satisfied. Browser approval records must
not be reused as email approval records.

An immutable approval snapshot binds exactly:

- draft identity and source revision;
- sender and routing identity;
- To, CC, and BCC recipients;
- reply-to and reply/reply-all behavior;
- subject;
- canonical body representation and rendered form where applicable;
- attachments, content hashes, names, and disposition;
- source-message and thread references;
- applicable policy version; and
- approver identity, decision, and decision time.

The snapshot has a deterministic digest or equivalent durable identity. A send
attempt must reference the approved snapshot and re-verify its digest and
authority before provider I/O.

Any material mutation after approval invalidates the approval. Material changes
include recipients, sender/routing identity, subject, body, attachments,
attachment hashes, reply behavior, source references, or governing policy. A
new draft revision, snapshot, digest, and decision are required. Approval never
floats forward to a modified draft.

## Synchronization idempotency and recovery

Synchronization is queue-backed and eventually consistent. Queue acceptance is
not completion under ADR-001.

Durable message uniqueness must bind at minimum:

- owning user;
- provider connection and provider account;
- provider mailbox; and
- stable provider message identity.

Provider revision or content identity may be added where the provider requires
it, but arrival order, filename, address text, or Redis task identity is not a
sufficient deduplication key.

Cursor advancement occurs in the same durable transaction as the normalized
message state or only after that state is safely committed and replay-safe.
Worker restart, Redis loss, or repeated delivery must replay from Postgres and
must not duplicate messages.

Provider UID validity changes, history expiration, watch loss, or cursor
invalidation enter an explicit recovery state. Recovery must rescan against
durable uniqueness and surface uncertainty; it must not silently discard or
duplicate correspondence.

## Send idempotency, outcomes, and reconciliation

A durable send request and append-only attempt ledger must exist before any
provider I/O. The stable send request identifies the user action; each attempt
has its own identity and remains linked to that request and approved snapshot,
consistent with ADR-003's distinction between authored identity and execution
attempt identity.

Retries within the same idempotency boundary must return or reconcile the
existing attempt state rather than create duplicate provider submissions.
Timeout or connection loss after submission is not safe evidence for blind
resubmission.

The later domain contract must register exact canonical tokens. It must preserve
at least these distinct meanings:

- `queued`
- `running`
- `blocked`
- `cancelled`
- `provider_outcome_unknown`
- `provider_accepted`
- `provider_rejected`
- `reconciliation_pending`
- `reconciled`
- terminal failure

These terms are required semantic distinctions, not runtime tokens introduced
by this docs-only ADR. Provider or SMTP acceptance does not prove delivery.
Final success requires a stored sent artifact plus successful reconciliation,
or the system must retain an explicit visible unresolved state. Unknown outcomes
must never collapse into success or automatic retry.

## Durable receipts and event projections

Postgres stores canonical sync, approval, send-request, send-attempt,
provider-result, reconciliation, revocation, and audit receipts. Provider
observations retain their provenance and do not silently overwrite local
user-authored drafts or decisions.

Redis queues, Redis task events, SSE, and in-memory fanout may project
acceptance, progress, blockage, and terminal visibility. They are operational
coordination and presentation only. They cannot be canonical receipts, and
event publication does not prove UI receipt or provider outcome.

## Retention, export, disconnect, and deletion

Email records are account-scoped and must participate in the versioned account
export and restore contract with stable identities, relationships, hashes,
provenance, and explicit restore reporting.

Disconnect and deletion are separate operations:

1. disconnect revokes future credential and provider access first;
2. durable connection and routing identities enter explicit revoked states;
3. queued work is blocked or cancelled against durable state;
4. synchronized data follows the accepted retention/deletion policy; and
5. tombstones or revocation markers propagate to retrieval and derived views.

Deletion must not silently erase audit or consent history required by policy.
Exact retention periods, legal holds, provider deletion behavior, and encrypted
export key management are deferred to later contracts.

## Product surfaces and visible failure

Guardian briefing and agent-mediated triage are primary. The human inbox,
reader, draft review, approval, receipt, correction, and audit surfaces remain
mandatory secondary controls.

The product must visibly distinguish unavailable, blocked, degraded,
`provider_outcome_unknown`, `reconciliation_pending`, provider rejection,
revoked connection, and terminal failure states. A missing event, stale cursor,
or hidden secondary surface must not manufacture apparent completion.

## Compatibility and migration requirements

Future implementation must preserve:

- provider replacement without changing core routing identity semantics;
- durable activation, revocation, and reassignment history;
- account-scoped export, restore, retention, and deletion behavior;
- no accidental collaborator-account adoption;
- migration from explicitly approved operator-managed staging credentials to
  durable OAuth without converting credentials into routing identity;
- backward-compatible rollout behind explicit feature gates; and
- rollback capability before any production mailbox cutover.

No runtime or data migration occurs in this ADR task.

## Consequences

Positive consequences:

- Human accountability remains explicit across persona-mediated correspondence.
- Provider replacement does not redefine core email identity or receipts.
- Approval and provider uncertainty remain durable and inspectable.
- Queue/event loss cannot erase canonical correspondence state.
- Collaborator consent and revocation become architecture boundaries rather
  than operator convention.

Costs and tradeoffs:

- Purpose-specific schemas and state machines are required before a live slice.
- Provider adapters must translate capability and failure differences rather
  than leak them into the domain.
- Every consequential mutation needs snapshot construction, digest validation,
  and durable decision history.
- Retrieval and attachment processing require additional quarantine,
  provenance, revocation, and deletion machinery.
- Unknown provider outcomes may remain unresolved and user-visible instead of
  being hidden by optimistic retries.

## Rejected alternatives

### Treat aliases as independent principals

Rejected because an address or alias cannot own credentials, authority, or
accountability independently of the human user.

### Bind routing identity by display name or email string alone

Rejected because mutable labels and addresses do not establish durable,
user-scoped ownership.

### Store email state in generic chat or job JSON records

Rejected because correspondence identity, relationships, lifecycle,
idempotency, retention, and receipts require purpose-specific constraints and
auditability.

### Reuse browser approvals as email approvals

Rejected because browser-operation approvals do not bind immutable draft,
recipient, attachment, routing, and policy state.

### Treat Redis events or SSE as durable receipts

Rejected because operational visibility can be delayed or lost and cannot prove
provider reconciliation.

### Expose raw IMAP or SMTP operations to agents

Rejected because provider operations require adapter, capability, approval,
idempotency, and policy enforcement.

### Allow email content to authorize actions

Rejected because correspondence is external untrusted evidence, not authority.

### Embed Google-specific semantics in the core domain

Rejected because Google Workspace is the initial adapter, not a permanent core
dependency.

### Use collaborator mailboxes as staging infrastructure without consent

Rejected because tenant membership does not transfer ownership or informed
consent.

## Required follow-through

Separate architecture-impact Task Specs must provide, in dependency order:

1. provider capability, routing, and adapter contract;
2. provider-neutral correspondence domain and schema contract;
3. authentication and secret-custody contract;
4. purpose-specific Postgres schema and migrations;
5. read-only provider connection and synchronization proof;
6. normalization and duplicate-suppression proof;
7. retrieval trust, provenance, attachment eligibility, and deletion contract;
8. immutable approval and send-attempt contract;
9. sending, provider-outcome, reconciliation, and receipt contract;
10. Guardian briefing and mandatory human-review UI contracts;
11. operator documentation, staging proof, recovery proof, and production gate;
12. system overview, flows, data/storage, module ownership, runtime/UI diagrams,
    and current-state updates only after their evidence gates are satisfied.

Dependent bounded contract Task Specs may now rely on this accepted ADR. This
does not implement or prove Email runtime support.

## Non-goals

This ADR does not implement schemas, migrations, provider interfaces,
connections, OAuth, app-password handling, queues, workers, routes, commands,
retrieval, UI, Tauri behavior, synchronization, sending, deletion, aliases,
folders, labels, filters, DNS, or mailbox changes. It does not access provider
state, credentials, messages, attachments, aliases, or mailboxes. It does not
authorize autonomous sending or deletion, production cutover, or collaborator
participation.

## Related documents

- `docs/architecture/00-current-state.md`
- `docs/Campaign/codexify-email-agent-native-campaign-index.md`
- `docs/architecture/inspections/codexify-email-implementation-targets.md`
- `docs/security/auth-boundary-decision.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/adr/001-Queue-Based-Completion-Acceptance-Model.md`
- `docs/architecture/adr/003-Message-Identity-vs-Request-Identity.md`
- `docs/architecture/adr/004-Retrieval-Policy-as-Control-Plane.md`
- `docs/architecture/adr/039-operator-user-access-boundary.md`
- `docs/architecture/adr/041-vaultnode-canonical-machine-and-audit-authority.md`
- `docs/architecture/adr/042-canonical-audit-evidence-contract.md`
