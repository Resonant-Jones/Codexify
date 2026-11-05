---
tags:
* architecture
* adr
* continuity
* governance
* provenance
* identity-boundary
  aliases:
* ADR-016
* Continuity Governance Surface Contract
---

# ADR-016: Continuity Governance Surface Contract

## Status

Accepted

Amended 2026-11-05: native-message durable custody accepted by explicit operator
approval of proposal `a680ff6ed4c43b46c275b668703d06bb8cec10ed`.
Architecture acceptance only; schema, writer/reader implementation and
PostgreSQL/live proof remain pending. Release remains HOLD.

## Date

2026-04-28

## Context

ADR-015 defines the continuity doctrine: Codexify may have a future continuity layer above thread-first chat, but that layer must stay user-governed, inspectable, reversible, and provenance-aware.

What ADR-015 does not yet define is the user-facing control plane for that continuity layer. Without a canonical governance contract, the system can drift into hidden heuristics, stale snapshot echo-chambers, imported-history overreach, persona/profile confusion, or identity contamination that is difficult to inspect or undo.

The gap is not theoretical:

- continuity doctrine exists
- identity and diary boundaries already exist
- export/restore provenance already matters
- personas already have a separate configuration/runtime role
- but there is no canonical contract for how continuity is configured, inspected, paused, reset, or excluded

This ADR closes that gap by defining the first explicit Continuity Governance Surface for Codexify.

## Problem Statement

If continuity behavior is left undefined, future implementation work can accidentally do one or more of the following:

- silently widen continuity scope beyond what the user intended
- bias the system toward stale or over-recalled snapshots
- contaminate continuity modeling with identity-like claims
- treat imported transcripts as if they were native lived continuity
- collapse persona configuration into ownership of continuity state
- make continuity bias impossible to inspect or reverse

Those failures matter because continuity is not just retrieval. It is a control-plane layer that can influence what the system prefers, surfaces, and reuses across time. If that layer is not explicitly governed, the runtime can become persuasive in ways the user never authorized.

## Decision

Codexify defines the **Continuity Governance Surface** as the canonical architecture layer that governs continuity behavior.

This surface is the user-governed control plane for:

- continuity scope
- continuity intensity
- continuity decay profile
- imported-history treatment
- continuity exclusions
- continuity mirror and inspection behavior
- continuity reset, rollback, disable, and pause behavior

The Continuity Governance Surface is not persona ownership. It is not a chat thread setting. It is not a deep-identity consent toggle. It is the control plane that determines whether continuity bias exists, how broad it is, where it may apply, how it decays, what it must exclude, and what the user can inspect or revoke.

## Canonical Concepts

| Concept | Canonical meaning |
|---|---|
| Continuity scope | The boundary within which continuity may bias context assembly. Scope answers where continuity can apply, such as thread-only, project-local, recent-thread working set, or cross-project personal continuity. Scope is narrower than "all available history" unless the user explicitly chooses that boundary. |
| Continuity intensity | The strength of continuity bias within the chosen scope. Intensity governs how strongly continuity may influence recall, framing, or prioritization. Intensity does not widen scope and does not imply deep identity modeling. |
| Continuity decay profile | The policy that determines how continuity bias cools with disuse, age, or lack of reinforcement. Decay changes activation bias, not canonical history truth by default. |
| Continuity exclusion | A rule that blocks specific content, threads, topics, or projects from continuity modeling even if they remain stored in chat history. Exclusions override convenience retrieval. |
| Continuity import mode | The treatment applied to imported history or imported transcripts. Import mode determines whether imported material is archive-only, recallable as archive, or eligible to seed continuity as a scaffold under explicit governance. |
| Continuity mirror | The inspectability surface for continuity state. It must show active and dormant continuity, provenance, exclusions, intensity, decay state, import treatment, and reset/freeze state in a user-legible way. |
| Continuity reset | An explicit action that clears active continuity bias or reinitializes continuity state according to the chosen reset mode. Reset must be user-legible and must not silently rewrite canonical history. |
| Continuity freeze / pause | A reversible temporary stop on new continuity updates, promotions, or refreshes. Freeze/pause preserves the existing continuity record and must not silently widen or auto-refresh continuity while paused. |
| User-authored continuity preferences | The explicit settings the user chooses for scope, intensity, decay, import treatment, exclusions, and reset behavior. These preferences are canonical user intent, not derived model output. |
| System-derived continuity state | The runtime-computed continuity state produced from user preferences, provenance, and current evidence. System-derived state may be inspected and used, but it must remain separable from the user-authored preference record. |

## Required Control Families

Future runtime and UI work that implements continuity must honor at least the following control families.

### Scope Controls

The minimum supported scope families are:

- thread only
- project-local
- recent-thread working set
- cross-project personal continuity

Scope controls define where continuity may bias context. They do not change canonical history ownership and they do not imply global recall across unrelated content.

### Decay Controls

Decay controls must define how continuity bias cools with disuse.

The contract distinguishes:

- rolloff, which reduces continuity bias or activation strength over time or disuse
- deletion, which removes history or records only when the user explicitly chooses a destructive action

The system may also support optional pinning or hold-close semantics for specific continuity anchors. Pinning may slow or suspend decay for the pinned anchor, but it must remain visible in the mirror and must not erase provenance.

### Import Controls

Imported history must be governed explicitly.

The minimum import modes are:

- archive only: imported material is preserved as history but cannot seed continuity bias
- recallable archive: imported material may be recalled intentionally, but it is not auto-promoted into continuity state
- continuity scaffold: imported material may seed continuity candidates under explicit governance, while remaining provenance-tagged as imported

Imported transcripts are not native lived continuity by default. Any continuity influence they carry must remain visibly imported and user-governed.

### Imported Archive Inspection Authority Clarification (2026-10-09)

**Decision A: existing account, Project, and thread-read authority is sufficient for a strictly human-initiated, zero-inference imported-archive inspection reader, provided each ownership boundary is independently enforced.** The continuity-governance settings model and evaluator are not prerequisites for that narrow operation. The three import modes above govern continuity influence, not the authenticated owner's right to inspect stored records. In particular, `archive only` permits owner inspection but prohibits continuity modeling.

Archive inspection means retrieving existing, explicitly selected imported message evidence for display to the requesting account user only. Bounded **evidence assembly for human display** is inspection only when its output remains an inert, ephemeral, user-visible set of excerpts and provenance, with no model/provider/tool consumer, semantic extraction, retained summary, hidden context assembly, or reuse by an inference pipeline. Calling the output a "preview" grants nothing further. Extracting traits, preferences, projects, open loops, or Chronicle prose crosses into interpretation and requires separately authorized continuity and, where applicable, identity governance before any model exposure.

The inspection-only reader must resolve the authenticated account server-side, require an explicit canonical Project and bounded thread/source selection, verify `projects.user_id` under ADR-081 and each thread's account owner and Project membership, and reauthorize source-reference readback. Missing ownership and legacy ownership conflicts fail closed. `guardian/core/project_ownership.py::classify_project_ownership` supplies conflict classification; `guardian/core/thread_access.py::require_thread_read_access` and `guardian/routes/chat.py::_scope_query_user_id` alone do **not** establish account isolation in single-user mode, so the reader must compare owners independently in every mode. Imported-provider IDs, historical instructions, operator credentials, and caller-supplied user IDs confer no account authority. Preserve imported/native message distinctions, original authorship, timestamp uncertainty, and accurate coverage/errors.

**Exclusion interpretation:** Diary flags (`ChatThread.is_diary`/`diary_mode`), `exclude_from_identity`, and `modeling_excluded` prohibit corresponding modeling, not ordinary inspection by the record owner. Explicit thread/Project exclusions from continuity and excluded sensitive topics likewise block modeling and activation, not human-visible archival inspection, unless independent diary-unlock, content-access, or record-read policy prohibits inspection. Existing access restrictions always apply. Missing continuity policy is **never** permission to interpret, model, or activate; ambiguous **record-read** authorization fails closed for inspection as well. Neither `UserSettings.memory_mode`/`allow_sensitive_modeling` nor `Project.identity_depth` is a substitute for continuity import-treatment authority. Exclusions must not leak record contents to unauthorized callers.

| Operation | Authority and user action | Exclusions and permitted result | Failure behavior |
|---|---|---|---|
| Owner archive inspection | Authenticated account; explicit Project, source and bounded thread selection; canonical owner/read checks | Existing record-read restrictions apply; only inert user-visible excerpts, including content excluded from modeling | Reject conflicted ownership or uncertain record-read rights; report partial coverage honestly |
| Bounded evidence assembly for human display only | Same authenticated, explicit, request-scoped inspection grant; no model delegation | Same read restrictions; no interpretation, persistence, hidden reuse, or continuity grant | Fail closed on ambiguous scope/access; omit or flag uncertain provenance |
| Summary, trait inference, or Migration Chronicle interpretation | Separately governed, explicit modeling permission; archive inspection alone is insufficient | Diary, sensitivity, identity, Project/thread modeling exclusions and import treatment apply | Block absent/ambiguous consent, governance, or exclusion resolution |
| Continuity-scaffold activation | Explicit governed `continuity scaffold` treatment and scoped activation | All continuity exclusions and provenance rules apply | Block without authoritative import treatment and exclusion resolver |
| Durable memory or preference promotion | ADR-084 / UMS account-user review and approval authority | UMS and identity/sensitivity guardrails; imported assertions remain candidates | Reject implicit/model-authored approval |
| Automatic or recurring continuity updates | Explicitly governed activation and separately authorized scheduling | Re-evaluate scope, exclusions, pause/freeze, import mode and decay | No automatic update until governing runtime policy exists |

A human inspection grant lasts only for the specified read. It cannot be persisted as continuity consent, passed to a model, upgraded into a personal profile, or used to bypass later exclusions. The archive, not the transient inspection output, remains canonical. This decision **unblocks only a bounded inspection-only evidence-reader implementation**, subject to tests proving ownership, provenance, access restrictions, failures, and zero writes. It does **not** unblock model-derived Migration Chronicle previews or establish a live reader, continuity resolver, natural import-to-recall qualification, or release support.

### Request-Scoped Chronicle Interpretation Authorization Clarification (2026-10-10)

Standing Continuity Governance preferences remain durable, user-authored settings for future continuity behavior. Their complete Project-level import-treatment and exclusion resolver is not implemented by this clarification.

A separate one-time Chronicle interpretation request may select `recallable archive` explicitly for one authenticated invocation, one canonical Project, and a bounded selection of imported threads and origins. It also requires explicit interpretation consent in that same request, ordinary account and thread read authority, message-level imported provenance established by the existing evidence reader, and clear server-resolved thread modeling exclusions. This request-local selection is not a saved Project preference, does not alter future treatment, and cannot authorize a subsequent request. `archive only` remains ineligible for modeling. `continuity scaffold` remains unavailable to this operation and does not authorize activation or durable candidate creation.

The resulting internal decision is immutable and bound to the exact authenticated principal, account, Project, selected evidence scope, limits, purpose, treatment, and resolved exclusion decisions. It is neither serialized nor stored, cached, queued, or attached to a provider call. The preflight itself returns no historical text, performs no inference, and writes no state. It establishes request eligibility only; it is not proof that arbitrary message content is safe for model exposure. A future generator must obtain fresh authorization in the consuming request and independently enforce message-level sensitivity and source restrictions before model exposure. If required restrictions cannot be resolved there, generation must fail closed. This clarification makes no atomicity claim across later consumption and does not implement the full Continuity Governance Surface, activation, durable memory, or production qualification.

### Exclusion Controls

### Reviewed Chronicle Interpretation Authorization Clarification (2026-10-11)

An authenticated account owner may approve exact, previously inspected imported-message excerpts for one local Migration Chronicle interpretation request. Each selected message requires an explicit boolean `approve_for_local_chronicle: true`, and that approval is bound to the current account, canonical Project, bounded thread/origin selection, request purpose, `recallable_archive` treatment, current inspected excerpt, and recomputed SHA-256 digest. The approval is invocation-local content-use authorization; it is not a digest match, a non-sensitive classification, archive-wide modeling permission, continuity activation, identity inference, or standing import preference.

Authority is evaluated in this order: canonical account and Project authority; source-read restrictions; Project, thread, diary, and modeling exclusions; any applicable configured sensitive-topic or continuity exclusion; explicit one-time treatment and interpretation consent; explicit per-message approval; current provenance and digest integrity; then strict local inference and output controls. A lower-priority approval cannot override a denial. Explicit exclusions remain hard denials, and unknown, conflicting, or unavailable required restrictions fail closed. Where no separate applicable sensitive-topic restriction is configured, this narrowly scoped owner approval establishes content-use permission for the selected message only; it does not manufacture a safety finding.

The grant is immutable and request-local. It is not stored, cached, queued, serialized, logged with source text, transferred to another request, or reused for future access. The consuming request rereads canonical PostgreSQL evidence and rechecks all boundaries before the local-only, tool-free model call. The resulting Chronicle remains cited, ephemeral, zero-write, and non-activating. This amendment does not implement a classifier, a complete Continuity Governance Surface, frontend consent UI, persistence, or release qualification.

Continuity exclusions must include at least:

- diary exclusion
- sensitive-topic exclusion
- project-level exclusion from continuity modeling
- thread-level exclusion from continuity modeling

Exclusions must override convenience retrieval. If a source is excluded, continuity may not silently reintroduce it just because it is available.

### Inspection Controls

The continuity mirror must reveal enough information for a user to understand what continuity is doing.

At minimum, it must distinguish:

- active continuity versus dormant continuity
- explicit sources versus inferred sources
- imported provenance versus native provenance
- user preferences versus system-derived state
- excluded material versus eligible material

The mirror must be inspectable without pretending to be a memory authority. It is an explanation surface for continuity bias, not a claim that the system owns the user's past.

### Reset Controls

Reset controls must include at least:

- disable new continuity updates
- clear active continuity bias without deleting history
- perform a full continuity reset when the user explicitly chooses it

Reset actions must be explicit and user-legible. They must not silently alter canonical history or provenance.

## Authoritative Chat Message Origin Clarification (2026-11-01)

This accepted clarification governs **message-level source eligibility**, not
recall permission. ADR-084 still owns request-scoped recall authorization;
ADR-005, ADR-081, and existing thread/message read authority remain independent
requirements. It authorizes no runtime activation, migration, backfill, importer
rewrite, restore change, or historical relabeling. The rules below are a target
contract for subsequent implementation, **not a claim that writers or readers
already enforce them**.

### Origin, ownership, authorship, and placement are different facts

A message's account owner, authored role, containing thread, current Project,
and historical source system answer different questions. None substitutes for
another. A native user post may contain a quotation from elsewhere: the native
record is the new user-authored interaction, not proof that quoted content was
originally authored in Codexify. Conversely, copying, importing, moving, or
restoring an existing external conversation record is not native creation.
A native Project/thread, a trusted backend process performing an insert, or a
valid recall grant cannot launder such a record into native evidence.

### Accepted durable custody amendment (2026-11-05)

The operator explicitly supplied **“Operator decision: APPROVED”** for the
[November 5 custody decision](../2026-11-05-native-message-origin-custody-decision.md),
originally proposed in local commit
`a680ff6ed4c43b46c275b668703d06bb8cec10ed`. This amendment accepts that bounded
mechanism. It revises the JSON-only representation and positive-proof test in
the November 1 clarification; its ownership, exclusions and no-backfill rules
remain in force. Implementation requires separate authorization.

**Security boundary:** Guardian and canonical PostgreSQL are trusted. Custody
proves an authorized native-creation operation within that boundary. It is
**not cryptographic attestation**. Runtime historical retrieval requires no
message signatures or hashing, signing service, additional provenance store,
new credentials or key-management requirement. Privileged SQL compromise or
compromise of the trusted Guardian SQL writer is outside this mechanism's
forgery-protection claim. An untrusted actor with arbitrary writes under that
identity invalidates the assumed boundary; a field name or caller-controlled
trust flag cannot repair it. Cross-installation proof-preserving restoration
remains separately governed and unimplemented.

### One creation authority; same-row custody and descriptive metadata

**Positive native proof for the new creation path is a supported, creation-only
custody discriminator paired with its coherent origin assertion, assigned by
the trusted canonical backend atomically with the exact message insert.** The
authority is the canonical creation operation and its enforced persistence
channel, not either field's text. The existing exact trusted assistant witness
below remains an independent permitted proof for certain historical assistant
records. Neither proof grants recall permission.

Retain the existing `ChatMessage.extra_meta.message_origin` assertion as
protected descriptive metadata. Its shape is not a client authority field:

```json
{
  "message_origin": {
    "version": 1,
    "origin_system": "codexify",
    "asserted_at": "2026-11-01T22:00:00+00:00"
  }
}
```

`version` identifies this metadata shape; `origin_system` reuses the existing
conversation-origin value `codexify` **with message-level semantics**: original
native interaction creation, not current storage or the latest inserting
process. `asserted_at` is the backend's zoned creation-time assertion timestamp,
not a replacement for `event_at` or `created_at`. Association with this exact
canonical message row supplies the identity binding, but association of JSON
alone does not prove trusted creation custody. Do not embed a local
message/thread/Project ID in the assertion and later mistake it for authority.
These member names are the reserved metadata contract, not new values in the
canonical protocol-token registry. No provenance database, graph, or
cryptographic attestation infrastructure is introduced.

Accept one additional nullable column on the existing canonical row:

```text
chat_messages.native_origin_custody TEXT NULL, default NULL

NULL                           no new creation-custody witness
'native_user_v1'               canonical Guardian native-user creation
'native_assistant_attempt_v1'  canonical Guardian accepted-assistant creation
```

These versioned discriminators identify backend creation operations, not new
conversation origins, task statuses or event tokens. The exact message PK and
immutable row binding associate custody with this message. The column is usable
as evidence only through the following enforced boundary, never because its
value resembles a trusted claim:

- Introduce the nullable column, CHECKs and immutability trigger atomically.
  There is no positive default or historical data update. Every legacy row
  remains NULL, including a row whose JSON matches the native assertion.
- Only `PgDB.create_native_user_message`, its `_PostgresGuardianDB` equivalent,
  and `PgDB.create_assistant_message_for_completion_attempt` may mint the
  respective discriminator. Native-user creation verifies the authenticated
  canonical owner/thread and user role. The accepted-assistant operation verifies
  the exact locked canonical request/task/turn/thread identity, non-null
  `accepted_at`, no failure/cancellation and successful exact-message binding.
  Imported or conflicting source claims cannot mint custody.
- Content, protected assertion and custody must be inserted together. Assistant
  attempt binding commits in that same transaction. Insert/binding failure
  rolls everything back. Retries return the original row and assertion without
  refreshing or upgrading custody. Unproven fallback writers leave NULL.
- PostgreSQL CHECKs reject unsupported discriminators, operation/role mismatch
  and incoherent paired assertion data. Positive-path checks must coalesce SQL
  unknown to false; missing JSON keys, wrong types and JSON null cannot pass
  through CHECK's nullable result semantics.
- PostgreSQL immutability protections reject every post-insert custody change,
  including NULL-to-positive promotion and clearing. For witnessed rows they
  also protect `id`, `thread_id`, `user_id`, `role` and the reserved assertion
  from rebinding/replacement. Unrelated metadata and authorized content edits
  follow existing rules without minting proof. Existing authorized deletion
  deletes the same row/witness; no new deletion authority is created.
- Generic writers, importers, copy paths and restore admission must refuse
  untrusted custody claims; they cannot hydrate the column from arbitrary
  dictionaries. Native thread placement, request references, account ownership,
  roles, timestamps and metadata flags cannot select the trusted operation.
  Copy/import/restore collision must not replace a witnessed record while
  retaining its old proof. No retrospective origin backfill is permitted.

The field and these constraints are **accepted architecture, unimplemented**.
Existing guarded native user and accepted-assistant writes produce protected
JSON, but serialize away the in-memory capability identity. Generic audit and
request records do not resolve ordinary-user creation custody. A nullable schema
extension is necessary; JSON storage alone does not establish that proof.
The migration, closed writer/admission channel, reader verification and
disposable PostgreSQL proof all remain prerequisites. Ordinary runtime retrieval
does not need signatures or hashing to verify this trusted persistence boundary.

A later implementation must enforce these additional custody requirements:

- Reject model/client attempts to supply, replace, remove, or merge the reserved
  subobject, including ordinary message metadata, tools, persona instructions,
  attachments, imported raw metadata, and restore payloads without trusted
  provenance custody. A client-authenticated content submission is not a
  client-authoritative origin assertion.
- The backend alone selects native creation versus import/copy/restore. Calling
  a generic insert helper does not by itself select native origin. In
  particular, the importer uses that helper too; **do not native-stamp every
  call to `create_message` by default**.
- Write the assertion in the native insert transaction, not in a later
  best-effort metadata update. Retries must preserve the original assertion and
  message identity; failed writes must not leave apparently proven records.
- Make the source-origin assertion immutable for that record. Protect it from
  generic JSON replacement/merge, message edit, copy, import, restore collision,
  and maintenance paths. Unrelated mutable metadata may still change.
- A row bearing this string before the protected writer boundary is established,
  an arbitrary metadata claim, or an unsupported version is **not** native
  proof. No timestamp cutoff, `trusted: true` flag, empty metadata, or reader
  default may manufacture writer authority.

If a canonical writer or mutation path cannot uphold those guards, its records
remain unproven for native recall until that path is repaired. This is the
remaining implementation prerequisite, not a reason to introduce another store.

### Writer coverage and existing historical lineage

| Creation path | Required origin behavior; current evidence boundary |
| --- | --- |
| Ordinary user message, including structured/multimodal content | The current authenticated canonical insert stamps protected JSON. The accepted same-row `native_user_v1` custody insert remains unimplemented; later metadata enrichment is not creation proof. Preserve role and owner semantics. |
| Native assistant response | Use the same guarded creation authority, never model-supplied origin. Only the accepted attempt operation may mint the new assistant discriminator in this slice; role `assistant` alone proves nothing. |
| Accepted worker assistant completion | The current `PgDB.create_assistant_message_for_completion_attempt` stamps JSON inside its binding transaction. Atomic `native_assistant_attempt_v1` custody and its accepted-at/immutability checks remain unimplemented. Preserve retry/deduplication and terminal semantics. |
| Voice user/assistant | `workers/voice_worker.py` writes the transcript through `create_message` without metadata and calls the completion **service** directly. The service uses `create_chat_message_with_metadata`; this does not inherit the queue worker's exact attempt-binding guarantee. Both need the same guarded creation rule. |
| Hosted Room human messages | `core/hosted_room_messages.py::create_human_room_message` directly inserts `ChatMessage` with participant attribution and an empty-metadata value. Preserve participant/authored-role semantics, and guard this direct insert too; account owner and human author are distinct. |
| Agent coding results and proof helpers | `agents/store.py::_store_source_thread_result` constructs `ChatMessage(kind="coding_result")`; `core/core_loop_proof.py` creates a user row and a synthetic assistant proof-status row without origin metadata. Origin cannot be inferred from assistant role or provider output. |
| Internal tool/evidence/proof messages | Native creation may be established, but origin does not make internal evidence recallable. Preserve kind exclusions; synthetic proof/status rows require an explicit content-eligibility decision, not automatic inclusion because an existing kind happens to default to `chat`. In-memory tool-result prompt dictionaries are not themselves canonical message inserts. |
| Separate message domains | `messaging/service.py` writes `DirectMessage`, not `ChatMessage`; `chat/chat.py` writes a separate SQLite `messages` table with no active caller found in this inspection. Neither establishes origin for canonical history. |
| External import, copy/move, or restore | Preserve original evidence. A native writer processing an existing record must not mint fresh native authority for it. |

The queued worker uses the atomic assistant/attempt helper when available;
fallback adapters insert first and enrich later. Current canonical route/worker
enrichment subtracts the reserved origin member from incoming metadata before
the JSONB merge. That write-side protection does not establish reader-verifiable
ordinary-user custody. Mutation/fallback paths, import/restore admission and raw
ORM inserts must be included in the new column's guard inventory. Existing
payload/request correlation metadata is not itself creation proof.

For **certain existing assistant records only**, persisted server-owned accepted
completion lineage can independently prove native generation: the same-account,
same-thread canonical attempt must identify **this exact** `completed_message_id`
and coherent request/turn/backend-task identity with persisted acceptance and
successful assistant binding. In the **existing** attempt representation this
means a non-null `accepted_at`, the exact `completed_message_id`, and no
failure/cancellation `terminal_event_type` (null); success is not a fabricated
`terminal_event_type="COMPLETED"` value. The account is checked via canonical
thread/message ownership, not an invented account column on the attempt.
A provisional row, provider response, unrelated attempt, or an ID
copied into message metadata is insufficient. The existing saved-widget
provenance path in `guardian/core/db.py::read_saved_widget_source_provenance` and
its eligibility validation demonstrate that narrower witness. This is not a
universal message-origin reader and does not prove an associated user message's
origin. Imported, restored-unverified, or contradictory lineage still fails
closed. No retrospective native claim is made for ordinary unmarked user rows.

### Classification, conflicts, and legacy uncertainty

The following four labels are **documentation-only fixture vocabulary**, not new
canonical runtime tokens or a second authority system:

| Classification | Required evidence | Ordinary native historical recall |
| --- | --- | --- |
| `native` | Supported same-row custody from the guarded native operation paired with a coherent assertion, or the exact trusted historical assistant witness above; no contradictory import evidence | Eligible for source screening only; all other permissions/exclusions still apply |
| `imported` | Existing positive provider import evidence and coherent canonical import lineage | Excluded; native placement and recall permission do not change origin |
| `unknown` | No adequate positive proof; incomplete import/native claim; unsupported/malformed metadata; unverified restore custody | Excluded, without guessing |
| `conflicting` | Incompatible native/import claims, or contradictory account/source-message/source-thread/creation linkage | Excluded, without selecting a convenient winner |

Preserve the importer's current `extra_meta.origin` values (`chatgpt_import` and
`claude_import`), matching `canonical_filter_profile`, zoned `imported_at`,
`source_message_id`, `source_thread_id`, `source_created_at`, raw-provider role
and payload, and existing import/thread lineage and timestamp uncertainty.
`era` and `embedding_status` are auxiliary fields, not independent proof.
Do not replace this provider-specific evidence with a boolean. Positive import
evidence wins over **placement**, not over a contradictory positive native
claim: the latter combination is a conflict and cannot be exposed as native.
Partial import indicators also prevent a native classification until the
contradiction/uncertainty is resolved under a separately authorized process.

Missing import markers are never positive native evidence. An unmarked legacy
row, even one whose author or owner recalls creating it, remains `unknown` unless
an existing durable, exact-message trusted witness independently proves origin.
The same applies to a legacy user row with native-shaped assertion JSON but
NULL custody. P01 and N04 must be separated by actual trusted creation evidence,
not different expected outcomes or a caller-supplied trust description. A new
canonical native insert receives the controlled column; a generic claim does
not. Existing rows are not upgraded to reconstruct that distinction.
Keep it intact; no deletion, relabeling, automatic backfill, or inference from
message text is authorized. Human record-inspection rights are separate from
model exposure. The imported inspection reader's existing `unproven_import_records`
means precisely that it cannot distinguish native additions from incomplete
legacy imports; it must not be reinterpreted as a native count.

### Restore and portability

Origin is the historical source, not the latest insertion process. The account
export/restore contract remains authoritative for portability and semantic
equivalence; an origin-bearing archive must preserve its proof, not gain new
native status during restore.

| Restored input | Required disposition |
| --- | --- |
| Proven native record with preserved trusted origin custody | Preserve original creation meaning, assertion/witness and assertion time only through a separately governed proof-preserving restore path; never stamp restore as native creation. That cross-installation path remains unimplemented. |
| Proven imported record, including placement in a native Project/thread | Preserve imported provider identity and lineage; keep it excluded from ordinary native recall |
| Legacy record lacking proof | Preserve unknown origin, raw metadata, role, and temporal uncertainty; no default native assertion |
| Contradictory provenance | Fail closed for native exposure; report conflict without leaking content. A proof-preserving restore may reject contradictory proof-bearing input under its existing fail-closed validation boundary; it must never silently repair it |
| Canonical IDs remapped | Remap canonical relationships under the restore contract, retain provider source IDs and origin semantics, and revalidate exact-message witness linkage rather than trusting a coincidentally equal old ID |

Archive hashes, successful owner authentication, and a valid manifest establish
integrity/account authority, **not by themselves the historical truth of a
self-authored native claim**. Arbitrary uploaded `message_origin` JSON or restored
attempt rows cannot recreate trusted creation authority. A later proof-bearing
restore must establish preserved custody from an already trusted canonical export
and validate exact-record lineage. If it cannot do so, it must refuse admission
of the purported trusted assertion rather than silently promoting or stripping
it. Ordinary legacy restore can preserve records as unknown without inventing
proof. Current generic upload admission refuses the reserved JSON assertion;
admission for the new custody column remains unimplemented. The accepted rule
is to refuse non-null untrusted custody claims before any writes, including at
low-level restore helpers and in every supported archive version. Exported
custody values are data, not portable authority. Archive ID remapping, hashes
and owner authentication cannot authorize reinsertion, nor may a canonical-ID
collision transfer an old row's custody. No generic trusted-custody restore is
accepted as implemented. This amendment executes no format or restore change
and introduces no signing service, credentials or key-management dependency.

### Per-message recall and coverage consequences

Future ordinary historical recall must establish origin **for each candidate
message**, before any excerpt or source attribution becomes model-visible.
A mixed-origin native thread may contribute only independently proven native
conversation messages that also pass account, Project, thread, content, kind,
and ADR-084 request-grant checks. Only then may a result say `codexify`.

Using existing bounded coverage-receipt conventions, report content-free counts
of imported, unknown, and conflicting candidate-message exclusions, separately
from thread exclusions. Do not expose excluded text, raw import metadata,
provider source identifiers, or historical instructions through receipts/errors.
Do not imply complete coverage when provenance exclusions, scan budgets, or
other omissions exist. This does not repair the separate 500-thread truncation
finding. Native origin grants no recall permission, memory approval, identity
change, Chronicle generation, or instruction authority.

The [message provenance fixtures](../fixtures/history-message-provenance.v1.json)
separate stored evidence, the trusted evidence source, classification, and
conditional recall eligibility. They are documentation-only expectations, not
runtime tests or evidence that origin stamping/filtering has shipped. Historical
recall finding #3 remains open until the guarded writers, restore/mutation
boundaries, per-message reader, labels, and coverage tests implement this rule.

## Boundary Doctrine

The Continuity Governance Surface obeys the following boundary rules:

- continuity governance belongs to user/runtime continuity control, not persona ownership
- Persona Studio may eventually expose compatible controls, but persona profiles must not become the canonical owner of user continuity state
- continuity settings are not equivalent to deep identity consent
- diary/chat storage is not the same thing as continuity bias
- imported transcripts may be continuity scaffolds only under explicit governance rules
- continuity must remain inspectable, reversible, and provenance-aware
- continuity governance must not silently widen into identity modeling
- continuity governance must not claim uninterrupted native memory where provenance does not support it

Persona configuration can borrow continuity semantics later, but it does not own the continuity control plane.

## Non-Negotiable Invariants

The following invariants are mandatory for any future implementation:

- personas do not own or silently widen user continuity state
- continuity configuration must not silently enable deep identity modeling
- continuity exclusions must override convenience retrieval
- imported and native lineage must remain distinguishable
- rolloff with disuse changes retrieval or activation bias, not canonical history truth by default
- reset and disable actions must be explicit and user-legible
- continuity governance must not claim uninterrupted native memory where provenance does not support it
- export/restore must preserve continuity-governance settings and provenance semantics if later implemented
- continuity-governance state must remain separable from provider-state, request-state, and thread-history truth surfaces

## Relationship to Existing Architecture

This ADR is aligned with, and constrained by, the following contracts:

- ADR-015 for continuity doctrine, working-set decay, provenance, and imported-history scaffolding
- the IDDB policy for chat-history versus identity separation, opt-in deep identity, and diary exclusion
- the account export/restore contract for provenance, lineage, and restore semantics
- the Persona Studio separation-of-concerns doctrine so profile config and user continuity governance do not collapse into one layer

Current runtime truth remains thread-first. This ADR does not claim a live Continuity Engine or a live continuity-governance UI.

## Implementation Boundaries

This ADR does not implement:

- runtime retrieval changes
- persistence or schema changes
- new UI panels or settings pages
- persona profile schema changes
- import pipeline changes
- export/restore payload changes
- automatic deep identity expansion
- new prompt behavior

This contract is architectural. It defines the future seam, not a shipped feature.

## Initial Architecture Shape

The likely future seams are:

| Seam | Responsibility |
|---|---|
| Continuity-governance settings model | Store user-authored continuity preferences, including scope, intensity, decay, exclusions, import mode, and reset state. |
| Continuity policy evaluator | Resolve user preferences, provenance, and current runtime evidence into the continuity state used by context assembly or continuity orchestration. |
| Continuity mirror inspection surface | Present active, dormant, excluded, imported, and inferred continuity state in a user-legible read-only form. |
| Continuity reset / disable actions | Provide explicit user operations that pause, clear, or fully reset continuity state without silently rewriting canonical history. |
| Continuity-aware import framing | Apply explicit import modes so imported transcripts are archive-only, recallable, or eligible to seed continuity scaffolds under governance. |
| Export/restore compatibility seam | Preserve continuity-governance preferences and provenance semantics if and when export/restore grows support for continuity state. |

These seams are intentionally high level. They describe the future control plane without prescribing tables, routes, or ranking algorithms.

## Documentation Routing

This ADR is the follow-on contract after ADR-015 and should be discoverable from the architecture front door.

- `00-current-state.md` remains the short-horizon truth layer for present runtime reality.
- `adr-index.md` should list this ADR immediately after ADR-015.
- `README.md` should point readers from the continuity doctrine to this governance contract when they need the user-facing control plane, not just the doctrine.

## Consequences

### Positive

- Continuity can be user-governed instead of heuristic-only.
- Inspectability becomes part of the contract rather than an afterthought.
- Imported histories can participate without being mislabeled as native continuity.
- Reset and exclusion semantics can be reasoned about before any UI or backend work lands.
- Persona/profile boundaries stay separate from continuity ownership.

### Negative

- Future implementation must keep more state surfaces distinct: continuity, diary/history, identity, persona config, request state, and provider state.
- The continuity mirror must be designed carefully so it explains bias without pretending to be memory ownership.
- Any later backend or UI implementation will need to honor this contract before it can claim continuity behavior is supported.

## Links

- [[ADR Index]]
- [[015-Continuity-Engine-Working-Set-and-Decay-Contract|ADR-015 Continuity Engine Working Set and Decay Contract]]
- [[account-export-restore-contract|Account Export + Restore Contract]]
- [[persona-studio|Persona Studio Architecture]]
- [[system-overview|System Overview]]
- [[data-and-storage|Data and Storage]]
- [[tech-debt-and-risks|Tech Debt and Risks]]
- [[00-current-state]]

## Notes

This ADR defines the canonical user-governed control plane for continuity behavior. It deliberately keeps continuity, diary history, persona configuration, and identity modeling separate, and it does not describe any continuity-governance implementation as already shipped.
