# Codexify Email Agent-Native Campaign Index

## 1. Campaign classification

- Execution lane: `architecture-impact`
- Campaign status: `proposed`
- Task kind: campaign governance documentation
- Evidence posture: `documented-contract`
- Primary product model: Guardian briefing and agent-mediated triage
- Retained secondary surface: human inbox and reader
- Initial hosted provider: Google Workspace
- Architecture review: required before runtime implementation
- Runtime effect: this document creates no runtime behavior and does not activate email support

This campaign index translates the Codexify Email product direction into bounded,
dependency-ordered Task Specs. It does not implement email behavior, create a
mailbox or alias, handle credentials, change DNS, cut over production mail, or
widen the supported beta surface.

## 2. Goal and product loop

Codexify Email is a proposed agent-native correspondence subsystem in which the
primary interaction is a Guardian brief followed by agent-mediated triage and
action proposals. The canonical proposed loop is:

`ingest -> normalize -> classify/triage -> Guardian brief -> propose action -> user approval when consequential -> execute -> reconcile -> receipt`

The human-facing inbox and reader remain available as secondary review,
debugging, correction, audit, and exceptional-workflow surfaces. They are not
the center of the product, but they must remain usable when automation is
uncertain, provenance needs inspection, or a user needs direct control.

## 3. Truth boundaries

### CURRENT

- GitHub `main` is canonical for accepted code, documentation, schemas, and
  contracts.
- VaultNode is the selected canonical runtime and audit authority.
- Guardian, React, Postgres, Redis-backed workers and events, command-bus seams,
  retrieval infrastructure, personas, and Tauri exist according to repository
  truth.
- Postgres is the durable system of record for existing Codexify application
  state. Redis provides operational coordination, queues, locks, and event
  transport; it is not durable correspondence truth.
- The supported release posture remains the local Docker Compose, local-first
  beta described by `docs/architecture/00-current-state.md`.
- Google Workspace is the product-selected hosted mail provider for the initial
  Codexify Email implementation. This is a provider decision for proposed work,
  not proof of a connected Codexify runtime.

### PROPOSED

- Codexify Email runtime behavior, provider adapters, domain schemas,
  synchronization, normalization, user-owned routing aliases, logical mailbox
  views, Guardian triage and briefing, human review, retrieval, drafting,
  approval, sending, reconciliation, and receipts.
- A durable persona-to-routing-identity mapping that preserves owning user,
  persona identity, provider address, routing target, status, revocation state,
  and audit history.
- Queue-backed synchronization and sending with idempotent persistence,
  explicit terminal states, reconciliation, and operator-visible failure paths.
- Consequential actions gated by user approval over an immutable approved
  snapshot of recipients, content, and attachments.

### FUTURE

- Replacement of Google Workspace with another hosted provider.
- Multiple simultaneous mail providers.
- A self-hosted inbound or outbound transport adapter.
- Production mailbox or MX cutover.
- Autonomous sending or deletion, team inboxes, mobile email surfaces, and
  collaborator opt-in mailbox participation.

None of these FUTURE items is authorized or implemented by this campaign index.
The presence of this document, a later issue, a scaffold, a route, a model, or
an adapter must not be represented as runtime proof.

## 4. Identity, authority, and consent boundaries

### User-owned agent routing identities

An address such as `persona_name.agent@provider-domain` is a user-owned routing
identity. It is not an independent principal, account owner, credential holder,
or source of authority. The owning user remains accountable for actions taken
through that address and retains final authority over routing, drafting,
approval, sending, revocation, and reassignment.

A logical mailbox separates a persona's mail through provider folders or labels
and Codexify views. That separation is useful for routing and presentation but
does not create another credential, ownership, or accountability boundary.
Persona context may help triage mail addressed to the persona, but message
content cannot grant authority, change durable identity, or mutate durable
memory without explicit consent through a governed path.

### Collaborators remain separate principals

Zac Matariki Snushall, also referred to as Maatariki or Matariki, is a separate
human collaborator, Codexify engineer, and Resonant Constructs member.
`maatariki@resonantconstructs.ai` is Zac's Google Workspace mailbox. It is not an
agent identity, operator test mailbox, alias target, credential source, or
staging resource.

No collaborator mailbox, credential, message, alias, billing seat, DNS record,
or provider setting may be inspected, used, modified, migrated, or treated as
user-controlled infrastructure without that collaborator's explicit informed
consent. Tenant co-membership does not imply shared authority. The same boundary
applies to every present or future collaborator.

## 5. Provider-independent domain and provider adapter boundary

The provider-independent domain model must express correspondence semantics,
not Google-specific operations. It should cover user and persona ownership,
routing identities, logical mailboxes, normalized messages and threads,
attachments and provenance, sync cursors, drafts and revisions, approval
snapshots, send requests and attempts, reconciliation state, and receipts.

Provider adapters own provider-specific authentication, account discovery,
alias capabilities, labels or folders, filters and routing rules, message IDs,
thread IDs, history or cursor behavior, SMTP or provider send APIs, Sent-folder
reconciliation, rate limits, and error translation. Google Workspace is the
first adapter target; Google-specific nouns and limitations must not become
provider-independent identity or mailbox semantics.

The boundary must preserve:

- replacement of Google Workspace without changing core email identity
  semantics;
- hosted-provider-first implementation;
- a later self-hosted adapter option;
- durable persona-to-routing-identity mappings;
- safe alias revocation and reassignment with retained audit history;
- no accidental migration, import, or reassignment of collaborator accounts.

## 6. State, consistency, and failure doctrine

- Postgres is durable Codexify truth for normalized correspondence state,
  persona routing bindings, sync checkpoints, draft revisions, approval
  snapshots, send attempts, reconciliation results, and receipts.
- The provider remains the external authority for what it accepted, delivered,
  labeled, or exposed in its mailbox. Codexify records observations and
  reconciles them into Postgres with provenance rather than silently inventing
  provider state.
- Redis is operational coordination only. Synchronization and sending are
  queue-backed; loss or replay of Redis work must be recoverable from durable
  Postgres state and provider reconciliation.
- Queue acceptance is not completion. Every accepted sync or send operation
  needs terminal success, failure, blocked, or reconciliation evidence.
- Repeated synchronization must not duplicate messages. Idempotency should bind
  the owning user, provider connection, provider message identity, and stable
  content or revision identity as required by the accepted contract.
- Repeated send requests must not duplicate SMTP submissions or provider API
  submissions. A durable send idempotency key and attempt ledger must be
  established before any live send path is enabled.
- Synchronization is eventually consistent across provider and Codexify state.
  Conflict policy must be explicit: provider observations are appended with
  provenance, local user-authored draft revisions are never silently replaced,
  and ambiguous identity or routing conflicts fail closed for human review.
- Retries require bounded backoff and jitter, rate-limit awareness, dead-letter
  or explicit blocked states, and backpressure.
- Email bodies, headers, links, and attachments are external untrusted data.
  They cannot supply system instructions, approval, identity authority, tool
  permission, or credential material.
- Provider credentials must never enter frontend persistence, prompts, logs,
  vector indexes, ordinary audit payloads, fixtures, proof artifacts, or
  committed files.
- Approved recipients, attachments, and content must not mutate silently. Any
  change after approval invalidates the approval and requires a new immutable
  snapshot and user decision.
- Production correspondence remains isolated until provider, adversarial,
  staging, reconciliation, recovery, and human cutover gates pass.

## 7. Required future ADR

A new ADR is required before runtime implementation. Proposed subject:
**Codexify Email User-Owned Routing Identity, Mailbox Governance, and Provider
Adapter Contract**.

The ADR must govern:

- user-owned agent email routing identities;
- logical mailbox separation without a separate authority boundary;
- persona-to-address bindings, revocation, reassignment, and audit history;
- user accountability and collaborator consent boundaries;
- provider abstraction and hosted-provider-first posture;
- authentication and secret custody;
- approval and immutable approved-snapshot semantics;
- idempotent synchronization, sending, reconciliation, and receipts;
- durable correspondence governance, retention, export, and deletion posture;
- compatibility and migration to another hosted provider or self-hosted adapter.

This task identifies but does not author that ADR. Architecture review is
required after this campaign index and before runtime Task Specs proceed.

## 8. Dependency-ordered construction campaign

Every entry below is a proposed, separately reviewable Task Spec. A proof
posture names what that task should establish; it is not proof in advance.

### 01. Inspect the current implementation targets

- Sequence number: `01`
- Imperative title: Inspect Codexify Email implementation targets
- Execution lane: `proof`
- Task kind: read-only repository reconnaissance
- Owning subsystem or role: architecture and subsystem owners
- Prerequisites: this campaign index accepted for architecture review
- Expected proof posture: `documented-inspection` with exact routes, services,
  workers, queues, models, migrations, retrieval seams, UI surfaces, tests, and
  ownership gaps identified
- Explicit non-goals: no edits, no provider connection, no credentials, no
  runtime claims, and no selection of a collaborator mailbox

### 02. Author and accept the governing ADR

- Sequence number: `02`
- Imperative title: Govern email identity, mailbox, approval, and provider boundaries
- Execution lane: `architecture-impact`
- Task kind: ADR documentation
- Owning subsystem or role: architecture review authority
- Prerequisites: Task 01 inspection; product and identity corrections in Issues
  #599 and #600
- Expected proof posture: accepted `documented-contract` with explicit decision
  owners and follow-through map
- Explicit non-goals: no runtime code, schema, provider setup, alias, mailbox,
  DNS, or current-state release claim

### 03. Define the provider capability and routing contract

- Sequence number: `03`
- Imperative title: Define provider capabilities, aliases, folders, and routing
- Execution lane: `architecture-impact`
- Task kind: provider adapter contract documentation
- Owning subsystem or role: provider integration boundary
- Prerequisites: Task 02 accepted ADR
- Expected proof posture: reviewed `documented-contract` covering capability
  discovery, authentication modes, alias and label/folder operations, routing,
  cursor semantics, rate limits, errors, and Google Workspace adapter mapping
- Explicit non-goals: no Google-specific behavior in the core domain, no live
  provider calls, no self-hosted server, and no collaborator-account access

### 04. Define the correspondence domain and schema contracts

- Sequence number: `04`
- Imperative title: Define durable email domain and schema contracts
- Execution lane: `architecture-impact`
- Task kind: data and storage contract documentation
- Owning subsystem or role: persistence and correspondence domain
- Prerequisites: Task 02 accepted ADR; Task 03 provider boundary reviewed
- Expected proof posture: reviewed `documented-contract` for normalized messages,
  attachments, routing bindings, logical mailboxes, sync checkpoints, drafts,
  approvals, send attempts, reconciliation, receipts, retention, and migration
- Explicit non-goals: no Alembic migration, SQLAlchemy model, provider payload
  leakage, vector indexing, or runtime persistence

### 05. Define authentication and secret custody

- Sequence number: `05`
- Imperative title: Define provider authentication and secret-storage boundaries
- Execution lane: `architecture-impact`
- Task kind: security contract documentation
- Owning subsystem or role: auth, security, and operator configuration
- Prerequisites: Tasks 02 and 03
- Expected proof posture: threat-reviewed `documented-contract` for Google OAuth
  or operator-approved app credentials, token encryption, rotation, revocation,
  least privilege, frontend exclusion, logging redaction, and recovery
- Explicit non-goals: no secret entry, no credential inspection, no OAuth client
  mutation, no app-password handling, and no production authorization

### 06. Prove an operator-controlled Google Workspace staging boundary

- Sequence number: `06`
- Imperative title: Prove the operator-controlled Google Workspace staging mailbox
- Execution lane: `proof`
- Task kind: live provider boundary proof
- Owning subsystem or role: human operator and provider administrator
- Prerequisites: Tasks 03 and 05; explicit confirmation of the operator-owned
  account and isolated test alias
- Expected proof posture: time-bounded `proven-live-provider` evidence for the
  selected operator-controlled mailbox and user-owned alias, with secrets absent
- Explicit non-goals: no Codexify integration, no Zac mailbox, no collaborator
  mailbox, no production correspondence, no DNS/MX cutover, and no autonomous send

### 07. Implement durable schema and persistence foundations

- Sequence number: `07`
- Imperative title: Implement durable correspondence persistence
- Execution lane: `architecture-impact`
- Task kind: backend schema and persistence implementation
- Owning subsystem or role: Postgres persistence layer
- Prerequisites: Task 04 accepted contract; migration and compatibility review
- Expected proof posture: `proven-test` for clean start, existing-instance
  upgrade, downgrade, constraints, ownership isolation, and idempotency
- Explicit non-goals: no provider connection, queue worker, retrieval, UI,
  sending, production migration, or collaborator data

### 08. Implement the authenticated read-only provider adapter

- Sequence number: `08`
- Imperative title: Connect Google Workspace through a read-only adapter
- Execution lane: `architecture-impact`
- Task kind: backend provider and authentication implementation
- Owning subsystem or role: provider adapter and secret-storage boundary
- Prerequisites: Tasks 03, 05, and 06; Task 07 durable connection records
- Expected proof posture: `proven-test` plus bounded `proven-live-provider` for
  least-privilege connection, capability discovery, revocation, and redaction
- Explicit non-goals: no message mutation, alias creation, sending, deletion,
  frontend secret exposure, or collaborator-account access

### 09. Implement queue-backed read-only synchronization

- Sequence number: `09`
- Imperative title: Synchronize provider messages without mutation
- Execution lane: `architecture-impact`
- Task kind: backend queue and worker implementation
- Owning subsystem or role: provider sync worker and Redis coordination
- Prerequisites: Tasks 07 and 08
- Expected proof posture: `proven-test` for enqueue-versus-completion states,
  bounded retries, backoff, cursor recovery, rate limits, cancellation, replay,
  backpressure, and dead-letter or blocked paths
- Explicit non-goals: no provider writes, message deletion, send path, Guardian
  action, UI claim, or production mailbox

### 10. Normalize and persist messages idempotently

- Sequence number: `10`
- Imperative title: Normalize provider messages into durable correspondence records
- Execution lane: `architecture-impact`
- Task kind: backend domain implementation
- Owning subsystem or role: normalization and Postgres persistence
- Prerequisites: Tasks 04, 07, and 09
- Expected proof posture: `proven-test` for duplicate sync, stable provider
  identity, MIME and attachment boundaries, malformed content, provenance,
  transaction rollback, and safe replay
- Explicit non-goals: no vector indexing, persona authority inference, HTML or
  attachment execution, sending, deletion, or silent data loss

### 11. Route aliases into user-owned logical mailboxes

- Sequence number: `11`
- Imperative title: Bind persona aliases to logical mailboxes
- Execution lane: `architecture-impact`
- Task kind: backend identity and routing implementation
- Owning subsystem or role: persona identity, routing, and provider adapter
- Prerequisites: Tasks 03, 04, 07, and 10; accepted persona-address lifecycle
- Expected proof posture: `proven-test` for user scope, persona binding, routing,
  unknown aliases, revocation, reassignment, collision handling, and audit history
- Explicit non-goals: no independent agent principal, no separate credential or
  authority boundary, no collaborator alias, no unapproved provider mutation,
  and no production alias cutover

### 12. Build Guardian classification, triage, and briefing

- Sequence number: `12`
- Imperative title: Brief the user through Guardian-mediated email triage
- Execution lane: `architecture-impact`
- Task kind: backend agent workflow implementation
- Owning subsystem or role: Guardian, correspondence policy, and persona context
- Prerequisites: Tasks 10 and 11; accepted prompt-injection and action policy
- Expected proof posture: `proven-test` for classification provenance,
  uncertainty, malicious content, persona context boundaries, proposed actions,
  and no-action fallbacks
- Explicit non-goals: no email-granted authority, no durable identity or memory
  mutation, no autonomous send/delete, and no hiding uncertain mail from review

### 13. Build the secondary human inbox and reader

- Sequence number: `13`
- Imperative title: Provide human review, correction, debugging, and audit views
- Execution lane: `architecture-impact`
- Task kind: frontend and API implementation
- Owning subsystem or role: React/Tauri review surface and Guardian APIs
- Prerequisites: Tasks 10 through 12; accepted presentation and redaction contract
- Expected proof posture: `proven-test` for account isolation, logical mailbox
  filters, raw-versus-normalized provenance, triage corrections, attachment
  safety, error states, and accessible direct review
- Explicit non-goals: no primary-inbox product pivot, no credential persistence,
  no provider-specific core UI contract, no send enablement, and no production claim

### 14. Add provenance-preserving correspondence retrieval

- Sequence number: `14`
- Imperative title: Retrieve correspondence with provenance and policy gates
- Execution lane: `architecture-impact`
- Task kind: backend retrieval implementation
- Owning subsystem or role: retrieval infrastructure and correspondence policy
- Prerequisites: Tasks 10 and 12; accepted retention, indexing, and injection contract
- Expected proof posture: `proven-test` for user and mailbox scope, provenance,
  deletion or revocation handling, attachment exclusion, prompt-injection
  containment, stale indexes, and retrieval suppression
- Explicit non-goals: no credential or full attachment indexing, no collaborator
  corpus, no authority promotion, no hidden durable memory mutation, and no graph requirement

### 15. Add agent drafting and revision history

- Sequence number: `15`
- Imperative title: Draft correspondence with durable revision history
- Execution lane: `architecture-impact`
- Task kind: backend and review-surface implementation
- Owning subsystem or role: Guardian drafting and Postgres correspondence state
- Prerequisites: Tasks 12 through 14
- Expected proof posture: `proven-test` for source provenance, persona voice
  boundaries, revisions, recipient and attachment review, concurrency, and
  user-authored corrections
- Explicit non-goals: no send, no implicit approval, no silent recipient or
  attachment changes, no collaborator impersonation, and no draft-as-memory claim

### 16. Enforce approval over immutable send snapshots

- Sequence number: `16`
- Imperative title: Gate consequential email actions with immutable approval
- Execution lane: `architecture-impact`
- Task kind: backend policy and audit implementation
- Owning subsystem or role: approval policy, command bus, and durable audit
- Prerequisites: Task 15; accepted approval and capability contract
- Expected proof posture: `proven-test` for exact recipients, headers, content,
  attachments, snapshot hash, approver identity, expiry, revocation, mutation
  invalidation, replay, and confused-deputy resistance
- Explicit non-goals: no prompt-based enforcement, no blanket approval, no
  autonomous send/delete, no post-approval mutation, and no live provider submission

### 17. Implement controlled idempotent sending

- Sequence number: `17`
- Imperative title: Submit approved messages exactly once
- Execution lane: `architecture-impact`
- Task kind: backend queue, worker, and provider implementation
- Owning subsystem or role: send worker, provider adapter, and command bus
- Prerequisites: Tasks 03, 08, and 16; isolated staging authorization
- Expected proof posture: `proven-test` before bounded `proven-live-provider` for
  durable idempotency keys, attempt ledger, duplicate requests, retries, timeout
  ambiguity, rate limits, approval validation, and provider error translation
- Explicit non-goals: no unapproved send, no deletion, no bulk campaign sending,
  no collaborator mailbox, no production traffic, and no success claim at enqueue

### 18. Reconcile Sent state and issue receipts

- Sequence number: `18`
- Imperative title: Reconcile provider outcomes into durable receipts
- Execution lane: `architecture-impact`
- Task kind: backend reconciliation and audit implementation
- Owning subsystem or role: provider sync, Postgres correspondence state, and events
- Prerequisites: Tasks 09, 10, and 17
- Expected proof posture: `proven-test` plus bounded staging proof for provider
  acceptance, Sent visibility, ambiguous submissions, delayed reconciliation,
  duplicate observations, terminal failure, and user-visible receipts
- Explicit non-goals: no delivery guarantee beyond provider evidence, no queue
  acceptance as completion, no silent success, no production promotion, and no
  ordinary audit payload containing message bodies or credentials

### 19. Prove adversarial and partial-failure behavior

- Sequence number: `19`
- Imperative title: Stress email boundaries under adversarial and partial failure
- Execution lane: `proof`
- Task kind: security, resilience, and recovery proof
- Owning subsystem or role: security review, provider integration, queues, and Guardian
- Prerequisites: Tasks 09 through 18 complete in the isolated test profile
- Expected proof posture: `proven-test` and controlled failure-injection evidence
  for malicious mail, poisoned attachments, prompt injection, account crossover,
  collaborator isolation, duplicate delivery, duplicate send, Redis loss,
  provider outage, token revocation, cursor rollback, backpressure, and restart recovery
- Explicit non-goals: no production mail, destructive provider actions,
  collaborator testing, secret capture, autonomous remediation, or release approval

### 20. Prove the complete staging loop on VaultNode

- Sequence number: `20`
- Imperative title: Prove the agent-native email loop in isolated staging
- Execution lane: `proof`
- Task kind: end-to-end live staging proof
- Owning subsystem or role: VaultNode operator, Guardian, provider adapter, and proof reviewer
- Prerequisites: Tasks 06 through 19; isolated operator-controlled mailbox and
  alias; exact-head deployment; explicit human approval for the test send
- Expected proof posture: exact-head `proven-live-runtime` evidence for ingest,
  normalization, triage, Guardian brief, action proposal, approval, execution,
  reconciliation, receipt, and secondary human review
- Explicit non-goals: no production mailbox, no collaborator mail, no MX cutover,
  no autonomous send/delete, no unsupported provider, and no release claim beyond
  the exercised staging surface and time window

### 21. Gate production cutover through human approval

- Sequence number: `21`
- Imperative title: Decide whether production correspondence may be activated
- Execution lane: `architecture-impact`
- Task kind: production-readiness decision and cutover plan
- Owning subsystem or role: human product owner, architecture reviewer, security
  reviewer, provider administrator, and VaultNode operator
- Prerequisites: Task 20 PASS; unresolved findings closed or explicitly accepted;
  rollback, monitoring, retention, support, and incident procedures reviewed
- Expected proof posture: signed human decision record with bounded production
  scope, go/no-go criteria, rollback authority, and post-cutover proof plan
- Explicit non-goals: this task is not cutover itself; no DNS, MX, alias, mailbox,
  credential, or production traffic change without a separately approved execution packet

## 9. Parallel work rules

No runtime implementation may begin merely because this index exists. The
shared contracts in Tasks 02 through 05 must be accepted first.

After those shared contracts are accepted:

- Task 06 provider-boundary proof and Task 07 schema implementation may run in
  parallel because neither depends on the other's mutable runtime output.
- After Task 10, Task 12 Guardian triage preparation and Task 13 review-surface
  design work may run in parallel only against accepted API and presentation
  contracts; integration of Task 13 still depends on Task 12.
- Task 14 retrieval and Task 15 drafting design or fixture work may run in
  parallel only after shared provenance and normalized-message contracts are
  accepted; drafting integration still depends on retrieval and human review.
- Security fixtures for Task 19 may be authored alongside Tasks 12 through 18,
  but final adversarial proof depends on their completed integrated surfaces.

Parallelism must not create competing token vocabularies, schemas, provider
leaks, approval meanings, or identity semantics. When a shared contract changes,
dependent work pauses and rebases on the accepted contract rather than silently
forking the architecture.

## 10. Human-required actions

These actions cannot be delegated to an agent merely through issue text:

1. Confirm the exact operator-controlled Google Workspace account and verify
   that no collaborator account is in scope.
2. Approve any Google Workspace tenant, alias, label/filter, OAuth, app-password,
   admin, DNS, or routing change before it occurs.
3. Enter or rotate provider secrets through the approved operator secret path;
   never place them in chat, prompts, logs, proof artifacts, or committed files.
4. Run or supervise canonical live proof on VaultNode and preserve exact-head,
   environment, time-window, and artifact provenance.
5. Review consequential draft snapshots and explicitly approve each staging send.
6. Obtain explicit informed consent before any collaborator mailbox or provider
   setting could enter a future test or production scope.
7. Make the production go/no-go decision and separately authorize any mailbox,
   alias, DNS, MX, credential, or production cutover Task Spec.

## 11. Proof and release gates

The campaign advances only when each Task Spec's stated proof surface passes.
Static contracts do not prove code; tests do not prove a live provider; a live
provider check does not prove Codexify integration; staging does not prove
production readiness.

Minimum production-gate evidence includes:

- accepted ADR and provider, schema, auth, approval, retention, and migration contracts;
- isolated operator-controlled Google Workspace proof;
- clean schema upgrade and downgrade proof;
- read-only sync, normalization, routing, triage, review, retrieval, drafting,
  approval, sending, reconciliation, and receipt evidence;
- duplicate-sync and duplicate-send prevention;
- malicious-content, credential-redaction, account-isolation, and collaborator-boundary proof;
- restart, outage, backpressure, retry, dead-letter, revocation, and rollback proof;
- exact-head end-to-end staging proof on VaultNode;
- explicit human production approval and a separately authorized cutover packet.

## 12. Documentation follow-through

This task adds only this campaign index and leaves
`docs/architecture/00-current-state.md` unchanged. Later Task Specs must govern:

- the new ADR;
- system overview and flow changes;
- data and storage contracts;
- module ownership changes;
- runtime and UI diagrams;
- provider operator documentation;
- current release-truth changes, only after accepted implementation and proof.

## 13. Campaign-wide non-goals

This index does not authorize or implement:

- runtime behavior, migrations, APIs, workers, queues, command-bus behavior,
  retrieval, frontend, or Tauri changes;
- mailbox, alias, label/filter, OAuth client, app-password, credential, DNS, or MX changes;
- production mailbox cutover or production correspondence;
- use, inspection, or modification of Zac Matariki Snushall's mailbox or any
  other collaborator infrastructure;
- a self-hosted mail server in the initial implementation;
- autonomous sending or deletion;
- an update to `docs/architecture/00-current-state.md`;
- any claim that Codexify Email is currently supported or live.

## 14. Source evidence

- GitHub Issue #599, including its hosted-provider comments
- GitHub Issue #600 and the identity correction naming Zac Matariki Snushall
- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/Ops/codexify-issue-template-contract.md`
- `docs/Collaborators/task-spec-protocol.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/security/auth-boundary-decision.md`
- Codexify Email project Source and handoff supplied with the Task Spec
