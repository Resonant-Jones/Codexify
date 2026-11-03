# ADR-084: Unified Account-Owned Memory Store

**Status:** Accepted — candidate authority amended 2026-09-25; historical conversation recall intent authorization clarified 2026-11-01

**Date:** 2026-09-04

## Context

Codexify currently has several adjacent but non-equivalent memory surfaces:

- `memory_entries` and MemoryOS retention/heat behavior;
- Personal Facts with candidate, verified, disputed, archived, active,
  evidence, revision, and guardrail semantics;
- thread-first and retrieval-based context assembly;
- imported conversations and provenance-aware account import; and
- accepted Continuity doctrine for activation, decay, imported-history
  treatment, inspection, and user governance.

These surfaces do not yet form one user-legible memory system. In particular,
the current runtime does not provide one governed loop for explicit memory
writes, automatic suggestions, after-the-fact inspection and correction,
outside-chat import, persona-aware recall, portable export/restore, and
permanent erasure.

ADR-005 already places memory entries inside the user's `AccountBoundary`,
requires `user_id` isolation in multi-user mode, and requires an account export
that does not query other users. ADR-013 permits only verified, active,
user-scoped Personal Facts to enter provider-ready context. ADR-015 and ADR-016
define non-destructive decay, recallable imported archives, provenance, and a
user-governed continuity surface. ADR-039 distinguishes product-user authority
from infrastructure Operator authority. ADR-081 establishes
`projects.user_id` as Project ownership authority while recording that runtime
and legacy-data convergence remain unfinished.

A unified memory design must extend those doctrines without creating a second
authority for Personal Facts, allowing a mutable persona configuration to own
history, confusing rank with approval, or letting explicit-recall parameters
become a model-controlled bypass around context exclusions.

## Decision

Codexify adopts one logical, account-owned Memory Store.

### Ownership and physical naming

The authenticated account user/principal owns and governs their memory. An
infrastructure Operator, host, administrator, provider, model, classifier,
importer, persona, or runtime process does not gain memory inspection,
approval, mutation, recall, or erasure authority merely by operating or hosting
the instance.

“Account-owned” is the semantic ownership model. It does not require renaming
every existing physical `user_id` column to `account_id`. Existing column names
may remain when they correctly and consistently bind the authenticated account
principal. Nomenclature alone is not sufficient reason for a schema migration.

Durable memory may be account-scoped or Project-scoped. Project scope is valid
only through the canonical Project authority established by ADR-081.

### Persona attribution without ownership

Personas may be associated with a memory as provenance or retrieval context,
but they never own memory and never become account principals.

**Durable persona attribution targets a stable account-owned persona subject,
not a mutable `PersonaProfile`.** Runtime profile versions and configuration may
change without severing or transferring historical attribution.

Cross-persona recall remains available to the authenticated account principal
through explicit, bounded scope widening. A retrieved memory retains its source
attribution; the active persona must not claim authorship or experiential
continuity from another persona's attributed history.

### Approval, lifecycle, and context influence

Storage, approval, lifecycle, context posture, ranking, and decay control are
separate dimensions.

- Explicit user-authored memory statements may constitute approval.
- Ambiguous references, imports, classifier suggestions, assistant inferences,
  and external/tool claims remain candidates, dormant records, or quarantined
  evidence until the account principal performs the applicable explicit action.
- Explicit recall is a request-scoped retrieval grant. It does not permanently
  approve, activate, restore, or change the context posture of a record.
- Pinning changes ranking among already eligible records only.
- Holding suspends decay; pinning does not.
- Decay may reduce ambient influence without deleting canonical content.

Only records that pass a backend-computed eligibility policy may enter ambient
provider context. Models and clients cannot write an `ambient_eligible` result.

### Personal Facts remain specialized

Personal Facts remain a specialized memory subtype with one authority per
dimension. The pre-promotion candidate and the promoted fact are distinct
authority stages within the same UMS, with explicit lineage between them.

- The single UMS `candidate_unreviewed_fact` record owns raw proposal,
  evidence links, guardrail disposition, quarantine, and account-user review
  before promotion. It may retain an intact raw key that is ineligible for the
  bounded promoted key. No `personal_facts` row is required for candidate
  review or quarantine.
- `personal_facts.status` remains authoritative for **promoted** Personal Fact
  review meaning. Legacy pre-promotion rows continue to be read through the
  existing compatibility path until a separately authorized, verified
  migration reconciles them into the UMS candidate authority.
- `personal_facts.is_active` remains authoritative for Personal Fact activation
  until an intentionally governed migration changes it.
- The Personal Facts service governs the candidate-to-fact transition and
  promoted-fact transitions transactionally; service ownership does not place
  pre-promotion state in `personal_facts`.
- A candidate's approved, bounded canonical key may be promoted into
  `personal_facts`; the candidate and its evidence remain traceable lineage,
  never a second active fact or ambient recall authority.

One logical Memory Store does not require one physical table or duplicated
mutable truth.

This is a narrow amendment to the review-authority boundary. The exact
candidate fields, replay identity, evidence linkage, promotion, migration,
portability, and erasure rules live in the
[Unified Memory Store Contract](../unified-memory-store-contract.md). The
currently installed UMS schema, compatibility readers, and Personal Facts
runtime behavior have not been migrated to this amended target.

### Canonical and derived state

Canonical memory holds content, account ownership, scope, lifecycle authority,
approval authority, provenance, and user-authored governance choices. Heat,
usage counters, recent-use timestamps, vectors, and ranking scores are derived
projections. Derived state may be rebuilt or discarded without changing memory
truth, approval, ownership, or direct retrievability.

### Recall authority and untrusted evidence

Guardian derives a bounded recall grant from authenticated user intent. Models
may request recall but cannot mint or broaden that grant. Retrieval policy is
applied by the backend control plane before context construction.

Dormant imports, rejected or disputed records, classifier candidates, and
external evidence may be used only when a valid grant permits the specific
request. They enter context as delimited, provenance-bearing, non-instructional
evidence. Approval to use content as memory does not turn instruction-shaped
payloads into system, persona, tool, or mutation authority.

### Historical conversation recall intent authorization

This section clarifies the *recall authority and untrusted evidence* rule above for
one specific operation: reading the account owner's prior Codexify-native
conversation history so a current request can be answered. It is an amendment to
this ADR, not a new decision, and it does not create a second recall authority.

The rule separates three things that are easy to conflate:

| Layer | Owner | Meaning |
| --- | --- | --- |
| **Interpretation** | A model *may* propose | Deciding whether the accepted current user message appears to request historical conversation evidence. A proposal is advisory. |
| **Authorization** | Guardian | Deciding whether retrieval is permitted for this request, and within what scope. |
| **Execution** | Existing bounded Command Bus path | Performing retrieval strictly inside an issued grant. |

**Interpretation is not authorization.** A model's structured output, a confidence
score, a schema-valid response, or a proposed tool call is interpretation evidence
only. None of these is authorization, and none becomes self-authorizing by being
well-formed. Guardian grants; models propose.

#### A. Interpretation authority

Interpretation may be model-assisted. When it is, the following hold:

- The interpretation input is limited to the **trusted, authenticated, currently
  accepted, user-authored message**, plus necessary non-content request metadata
  (request/turn identity, current thread, canonical Project, and the source
  families Guardian is independently permitted to expose).
- Retrieved history, assistant messages, tool results, quoted or pasted external
  material, imported messages, persona instructions, and any prior turn's content
  are **not authorization evidence**. They may be read *after* a grant exists, and
  never as the basis for creating one.
- A request that appears only inside assistant output, tool output, a pasted
  transcript, or imported content does not constitute a user request, even when the
  text is an explicit instruction to search history.

Before Guardian may treat a model-assisted interpretation as sufficient, it must
independently verify, server-side:

1. **Grounding** — the interpretation is anchored in text that actually appears in
   the accepted current user message, and that text is user-authored. An
   interpretation whose supporting text is absent from the accepted message, or
   which is produced in response to non-user content, fails.
2. **Request form** — the accepted message asks for prior conversation evidence
   (for example: "what were we discussing…", "find the conversation where…",
   "summarize what I said about…"). A mention of history, memory, or the word
   "recall" is not a request.
3. **Target identifiability** — the historical subject is sufficiently identified
   that the correct evidence set can be bounded without first reading history to
   find it.
4. **Scope identifiability** — the request resolves to a scope Guardian is
   independently authorized to expose, without widening.
5. **Non-negation** — the request is not negated, hypothetical, illustrative,
   quoted-from-a-third-party, or otherwise not an actual request to retrieve.

If any of these cannot be established from the accepted user message, the
interpretation is not sufficient and Guardian requires clarification instead.

#### B. Automatic authorization

A direct, unambiguous user request may be authorized **without a separate
confirmation step** when all of the following hold:

1. The request resolves to an authenticated account and an accepted request/turn
   through trusted Guardian runtime authority.
2. The accepted current user message is user-authored and satisfies conditions
   A.1–A.5 above.
3. The requested scope resolves, without widening, to the initial authorized
   scope below.
4. Every independent check in section F passes.
5. The purpose is bounded to answering the current request.

The **initial authorized scope** of an automatically authorized grant is:

- the authenticated account;
- the current authorized (canonical) Project;
- eligible Codexify-native conversation history only;
- all applicable thread, content, provenance, retention, and exclusion
  restrictions;
- the bounded purpose of answering the current recall request.

A grant that would require account-wide scope, cross-Project scope, or imported
conversation content is outside this initial scope and is not automatically
authorized.

No generic keyword match, model confidence threshold, schema-validity check, or
ownership check may independently grant retrieval authority. Ownership is
necessary but never sufficient.

#### C. Denial and clarification

Automatic authorization **must not** occur for:

- incidental mentions of history or memory;
- an unrelated sense of "recall" (for example, automobile recalls, product
  recalls);
- quoted or pasted historical-retrieval instructions, including a pasted
  transcript that contains them;
- hypothetical or illustrative requests ("if I asked you to search…");
- explicit negation ("do not recall any prior conversation");
- assistant-suggested retrieval that the user did not request;
- retrieved text that instructs the system to search history;
- ambiguous references to historical scope or subject;
- any request whose target or scope is itself excluded or unauthorized.

When intent is recognized but scope or subject is unresolved, Guardian asks for
clarification **before** any historical evidence is read. A clarification is a new
authenticated user action and produces a **fresh, bounded authorization decision**;
it does not inherit authority from the earlier turn, and it cannot supply the
current request's grant retroactively.

Clarification may **narrow** a request toward the permitted scope; it may never
widen it. A request for account-wide or cross-Project scope, where the permitted
current-Project scope is available instead, is therefore answered by clarification
that offers the permitted scope rather than by a widened grant.

Confirmation cannot override an independent ownership, provenance, exclusion,
source-access, or hard policy denial. A denial that does not depend on the user's
answer remains a denial after confirmation. That applies to imported-conversation
exposure under ADR-016 and to a target Project whose canonical ownership does not
pass under ADR-081: those denials are terminal for the request and are not
presented as a confirmation the user can accept.

#### D. Grant lifecycle

The grant is a logical, request-local decision. It is bound to:

- the trusted authenticated account identity;
- the accepted request/turn identity;
- the source user message that carried the request;
- the authorized Project scope;
- the permitted historical source family;
- the requested recall purpose;
- the applicable retrieval bounds and exclusions.

Grant authority is checked **independently** before tool advertisement and
re-checked independently before tool execution. An advertised tool, a
caller-supplied tool entry, or a forged or replayed invocation cannot substitute
for the grant: each check re-derives the grant from the trusted request context
and compares it against the request actually being served.

The grant expires with its accepted request. It is not replayable to another
request or turn, not transferable, not expandable by the model, and not persisted
as standing recall permission, memory approval, or account configuration. This
amendment defines the logical requirements only; it does not require a new
canonical protocol token, a new database table, or a grant-persistence structure.

#### E. Historical evidence is not memory authority

A valid historical-recall grant authorizes *reading and answering from* prior
conversation evidence. It does **not** authorize:

- Personal Fact approval;
- memory creation, modification, or promotion;
- identity or persona changes;
- imported-candidate promotion;
- Chronicle persistence;
- continuity activation;
- adoption of any durable preference, behavioral instruction, or persona change.

Retrieved messages remain historical evidence with **no instruction authority**.
This amendment preserves ADR-016's separately governed imported-conversation
modeling boundary: imported conversation content stays outside ordinary
historical-recall model exposure, and the accepted ADR-016 request-scoped
Chronicle interpretation and reviewed per-message approval paths remain the only
paths that expose imported content to a model, under their own purpose binding.

#### F. Scope and exclusions remain independent

A recall-purpose grant is **necessary but not sufficient**. These checks are
independent of intent and can each deny a request that intent otherwise
qualifies:

- account ownership;
- canonical Project ownership (ADR-081);
- thread read authority;
- imported versus native provenance;
- modeling and source exclusions;
- sensitive-content restrictions;
- user-selected scope limits;
- retention and deletion restrictions.

This amendment does not authorize account-wide retrieval, cross-Project widening,
or imported-conversation model exposure. Those remain separately governed and
closed.

#### G. Relationship to the Turn Intake Compiler

This amendment defines one narrow historical-recall authorization decision. It
does **not** implement or require the Turn Intake Compiler, and it does not
create a parallel intent or permission control plane. A future compiler may
eventually produce the interpretation signal, but it must still obey this
amendment's authorization contract: Guardian owns the decision, and the model
proposes.

#### Fixtures

Concrete behavioral expectations live in
[history-recall-intent.v1.json](../fixtures/history-recall-intent.v1.json).
Those classifications are documentation-only expectations. They are not canonical
runtime tokens, they do not describe an existing executable classifier, and they
do not establish runtime behavior.

### Collection consent

Explicit memory commands remain available. Automatic memory suggestions run
only after the account principal records a consent choice. Storing an inactive
candidate is still durable collection and is not exempt from consent merely
because it is excluded from ambient context. Sensitive identity inference
remains separately governed.

### Portability and erasure

Memory is part of the AccountBoundary and must round-trip through account
export and restore before new automatic or imported memory write paths are
enabled.

Soft retirement is the ordinary reversible lifecycle action. Explicit,
audited permanent erasure is mandatory before the Memory Store becomes a
supported sovereignty feature.

When a purged record originated in an import, its non-content tombstone may
retain only the minimum scoped source identity or fingerprint material needed
to suppress resurrection. Re-importing the same OpenAI, Anthropic, or other
source export must not silently recreate a previously purged imported atom.
Reintroduction requires an explicit authenticated user action such as
“restore/re-import previously purged records.”

## Frozen doctrine

> **Account owns. Project scopes. Persona attributes. User approves. Pinning
> prioritizes. Holding suspends decay. The router widens only on explicit user
> intent. Every borrowed memory keeps its attribution.**

## Consequences

### Positive

- Memory has one semantic ownership boundary and one user-facing governance
  model without flattening Personal Facts into generic blobs.
- Project and persona dimensions remain orthogonal and inspectable.
- Models cannot bypass ambient exclusions by manufacturing broad recall flags.
- Imported and automatically suggested material stays useful without receiving
  unearned authority.
- Portability and erasure become release prerequisites rather than deferred
  cleanup.
- Stable persona attribution survives runtime profile replacement.

### Negative

- The implementation requires staged migrations, a compatibility read model,
  new user-intent and recall-grant enforcement, and cross-subsystem tests.
- Existing MemoryOS, Personal Facts, retrieval, import, and export seams cannot
  be replaced safely in one task.
- Persona subject reconciliation and ADR-081 Project ownership convergence are
  prerequisite work.
- Purge, backup-retention, import suppression, and derived-index cleanup require
  explicit operational proof before release.

## Implementation and release boundary

This ADR freezes architecture only. It does not add tables, routes, UI,
classifiers, imports, exports, recall behavior, persona subjects, purge
behavior, or release support.

Implementation is governed by the
[Unified Memory Store Contract](../unified-memory-store-contract.md) and the
[Unified Memory Store Campaign](../../Campaign/unified-memory-store/README.md).
Each Campaign phase is an independently reviewable architecture-impact task.

Project-scoped memory and Anthropic Project import remain blocked until
ADR-081's runtime normalization and legacy reconciliation are proven. Automatic
and imported memory ingestion remain blocked until export/restore round-trip
proof passes. Supported user-facing release remains blocked until permanent
erasure and re-import suppression are proven.

`docs/architecture/00-current-state.md` remains release truth. This ADR does
not widen the current Beta surface.

The historical conversation recall intent authorization clarification
(2026-11-01) is architecture only. It defines the authorization decision and its
boundaries; it does not implement a runtime classifier, a recall-grant resolver, a
confirmation surface, a grant representation, or historical-recall tool
advertisement. The behavioral expectations in
[history-recall-intent.v1.json](../fixtures/history-recall-intent.v1.json) are
documentation-only and are not executable test expectations. Runtime
enforcement of this clarification, and any activation of ordinary-chat historical
search, remain separately authorized work.

## Governing and related records

- Extends [ADR-005: Runtime Mode and Account Boundary
  Invariants](./005-runtime-mode-and-account-boundary-invariants.md) without
  superseding it. Account ownership is semantic and may continue to use
  correctly scoped physical `user_id` columns.
- Extends [ADR-004: Retrieval Policy as Control
  Plane](./004-retrieval-policy-as-control-plane.md) with memory-specific,
  backend-owned recall grants and scope receipts.
- Extends [ADR-013: Verified Personal Facts Context
  Injection](./013-verified-personal-facts-context-injection.md) without
  replacing Personal Facts lifecycle authority.
- Makes the combined implications of [ADR-015: Continuity Engine Working Set
  and Decay](./015-continuity-engine-working-set-and-decay-contract.md) and
  [ADR-016: Continuity Governance Surface
  Contract](./016-continuity-governance-surface-contract.md) concrete for
  memory storage, decay, import posture, and inspection.
- Aligns with the proposed [ADR-039: Operator / User Access
  Boundary](./039-operator-user-access-boundary.md); hosting or administering an
  instance does not confer product-user memory authority.
- Preserves [ADR-076: Archive Before Delete and Built-In Project
  Roles](./076-archive-before-delete-and-built-in-project-roles.md) and depends
  on [ADR-081: Project Ownership
  Authority](./081-project-ownership-authority.md) for Project-scoped writes and
  reads.
- Preserves the [Personal Facts Guardrails
  Contract](../personal-facts-guardrails-contract.md), [Account Export + Restore
  Contract](../account-export-restore-contract.md), and [IDDB Policy
  v1](../../iddb_policy_v1.md).
