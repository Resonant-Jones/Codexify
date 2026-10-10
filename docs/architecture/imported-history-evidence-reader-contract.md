# Imported-history evidence reader contract

Date: 2026-10-09. Architecture-impact lane; aligned with ADR-015, ADR-016's
October 9 inspection clarification, ADR-030, ADR-081 and ADR-084. No new ADR,
schema, public route, worker, scheduler, UI or release claim.

## Authority and trust boundary

`guardian/services/imported_history_evidence.py::ImportedHistoryEvidenceReader`
assembles existing excerpts for one explicitly requested human inspection.
PostgreSQL `projects`, `chat_threads`, and `chat_messages` remain authoritative.
The response is ephemeral evidence; it is neither instruction nor stored memory.
The trusted server caller supplies a `RequestUserScope` already resolved by account
authentication (for example `get_account_user_scope` in
`guardian/core/dependencies.py`). Guest principals, user-ID strings and imported
provider identifiers are not admitted credentials. This internal Python boundary
cannot authenticate a caller that fabricates a principal; exposing it publicly
would require a separately reviewed authenticated route.

`RecordReadAuthority` is a request-only receipt bound by object identity to that
same principal, the Project and exactly the selected threads. Each
`ThreadReadDecision` must explicitly resolve `record_read_allowed`,
`source_read_allowed` and `diary_read_allowed` to Python `True`. False, absent, ambiguous decisions and receipts bound to a
different principal instance fail closed. The caller must not cache or reuse this
receipt for another human request; this internal value is not a cryptographic
capability or a persisted consent record. The trusted caller must resolve any
applicable content-access, source-readback or independent diary-unlock restrictions
for this human request immediately before the read. A receipt can only narrow
ownership authority; it cannot grant another account's records. Never accept it
from request JSON or historical content. There is no implicit allow-all receipt,
policy cache, unlock implementation or future import-treatment resolver here.
No production caller is wired by this task.

The reader independently compares `projects.user_id`, each `chat_threads.user_id`,
Project membership, and every selected thread's `chat_messages.user_id` in **both**
single-user and multi-user modes. `classify_project_ownership` in
`guardian/core/project_ownership.py` rejects legacy-envelope authority conflicts;
a missing canonical owner cannot be replaced by an envelope owner. The existing
`require_thread_read_access` in `guardian/core/thread_access.py` is also applied
using snapshot metadata, but its single-user behavior is never the isolation proof.
All selected threads are authorized before any message content is fetched. A wrong
message owner anywhere in the selected corpus, including outside the page, rejects
the whole invocation. Errors contain no excerpts or other accounts' metadata.
Each later source-reference readback must repeat these checks with a new receipt.

ADR-016 distinguishes inspection from modeling. Diary flags, `exclude_from_identity`,
`modeling_excluded`, continuity exclusions, `Project.identity_depth` and the
identity-only `UserSettings` controls are not ordinary archive-read grants or
vetoes. In particular, `diary_requires_unlock` currently governs identity writes
(`guardian/routes/imprint.py` and `frontend/src/settings/IdentityMemorySettings.tsx`).
A separately applicable diary **read** restriction must still be resolved and
honored in the receipt. No modeling, continuity activation or inference permission
is inferred from a successful inspection.

## Explicit bounded inputs

`read` requires the trusted principal, positive canonical `project_id`, a tuple of
unique positive canonical `thread_ids`, a tuple of permitted
`ConversationOriginSystem.OPENAI` / `.ANTHROPIC`, explicit `InspectionLimits`, and
the receipt. Native origins, legacy source aliases, empty selections, duplicates,
boolean IDs and unresolved identity are rejected. `account_id` takes precedence
over the compatibility `user_id`; neither comes from import metadata.

| Input | Fixed upper bound |
| --- | ---: |
| Selected threads | 20 |
| Returned messages (`max_messages`) | 100 |
| Inspected candidate messages (`max_inspected_messages`) | 1,000 |
| Each UTF-8 excerpt (`max_excerpt_bytes`) | 8,192 bytes |
| Entire canonical JSON response (`max_response_bytes`) | 262,144 bytes |
| Explicit pagination `offset` | 100,000 records |

Each budget must be a positive integer within its ceiling. The byte budget covers
headers, provenance, coverage, JSON escaping and excerpts. If coverage metadata
alone cannot fit, the service raises an explicit request error. Excerpt clipping
preserves valid UTF-8. Candidate content is clipped in SQL before transfer; neither
full raw transcripts nor arbitrary extra metadata are returned. Provenance strings
are limited to 1,024 UTF-8 bytes and overlarge/malformed fields fail explicitly.

## Read mechanics and failures

Supply a factory for a **fresh, idle, transactional psycopg connection**, such as
`PgDB._connect` outside any `conversation_transaction`. The reader refuses borrowed,
already-active and autocommit connections without taking over their transactions.
It does not use the unimplemented generic `PgDB.cursor` or list helpers that turn
exceptions into empty results. One `REPEATABLE READ READ ONLY` transaction covers
Project authority, thread authority, counts and the bounded message query. A local
five-second statement timeout bounds each SQL statement. The connection is closed
after its read transaction; no source mutation or durable inspection record occurs.

`EvidenceRequestError` means invalid selection/budget;
`EvidenceAccessError` means missing, denied or conflicted authority;
`EvidenceMetadataError` means unsafe persisted metadata;
`EvidenceReadError` means a database failure or unsuitable connection. Database
exceptions are translated to content-free errors without SQL/DSN diagnostics.
None are serialized as invented protocol tokens. A successful empty authorized
thread has zero counts and an empty excerpt tuple; a failed metadata or database
read never becomes a successful empty corpus. No partial content is returned on
an authority, integrity or database error.

## Imported provenance and temporal truth

Thread origin alone never classifies a message. The reader admits a message only
when its own `extra_meta` establishes the matching persisted importer `origin`,
`canonical_filter_profile` and a parseable zoned `imported_at`.
`backend/rag/chatgpt_migration.py::_write_canonical_messages` writes these fields.
The compatibility markers `chatgpt_import` / `claude_import` and profile strings
are existing stored metadata, not new canonical origin values. A native addition
or legacy row without sufficient positive import evidence is omitted and counted
as `unproven_import_records`; this count does not pretend to distinguish native
from incomplete legacy imports. No source-ID join or cross-Project search occurs.
Contradictory account/source-thread provenance fails explicitly.

Every `ImportedExcerpt` contains canonical Project, thread and message IDs, the
canonical imported origin, nullable stored source IDs, canonical role and inert
text. Colliding provider IDs remain distinct under canonical account/Project/thread
scope. Missing IDs remain `None`. The existing Anthropic importer may synthesize
`source_message_id`; `source_message_id_verified_original` is true only when the
stored reference matches a raw original `id`, `uuid` or `message_id`. The reader
does not manufacture any reference or promote an importer ID to verified identity.
Original role and content type are extracted from raw fields when present;
`importer_role` and `importer_content_type` preserve separate normalized evidence.
For example, Claude normalization's `text` does not establish an original source
content type. No raw content blocks, media payloads, names or arbitrary metadata
are exposed.

The response keeps the following times distinct:

- `source_time` and `source_time_field`: parseable time actually present in a raw
  source field (`raw_message.create_time` for OpenAI; the existing importer field
  precedence for Anthropic). An `updated_at` basis remains explicitly an update
  field, not a claim of creation time. Existing export epoch seconds, milliseconds
  and numeric strings are normalized without importing the writer. Unzoned, invalid
  and missing values are unknown.
- `normalized_source_time`: the importer's persisted normalized timestamp, which
  can use conversation/import fallback. `normalized_time_matches_source` verifies
  equality with a raw source instant; `fallback_or_uncertain_time` remains true
  otherwise. The original raw timestamp and a disagreeing normalized value are
  both retained honestly. The reader does not reconstruct a lost fallback basis.
- `imported_at`: message import time, independently required for import evidence.
- `canonical_event_at` / `canonical_created_at`: stored canonical record clocks;
  neither proves an original source instant.
- `read_at`: UTC time of this ephemeral assembly, not freshness of the source.

Historical instructions, custom instructions, tool-looking text and system roles
remain inert excerpts. No instruction parsing, adoption, forwarding or execution
occurs.

## Coverage and pagination

Ordering is ascending canonical `(thread_id, message_id)`; input thread order is
normalized. SQL inspects at most the explicit candidate-window bound. Per-thread
counts include native and unproven messages, with optional persisted import-summary
kept/filtered counts. Missing summaries remain unknown; summaries never prove a
complete source archive or complete account import.

`EvidenceCoverage` reports total stored messages, inspected and returned counts,
unproven import records, omissions caused by the message/response budgets, truncated
excerpts, offset, next offset, window completeness and pagination ceiling.
For an inspected window, returned + unproven + message-limit omissions + byte-budget
omissions equals inspected. Byte-budget reduction drops trailing whole excerpts;
coverage counts and order remain deterministic. The final encoding is
`ImportedHistoryEvidence.to_json()` (UTF-8, sorted keys, compact separators).
Serialization with additional transport framing needs its own budget.

`next_offset` advances by **inspected** records. It does not promise recovery of
eligible messages omitted inside that page by the return or byte budget: reread
that same window with larger permitted budgets or a smaller inspection window.
Excerpts truncated for length need a separately authorized bounded source readback.
`selected_window_complete` is conservative: true only from offset zero with no
remaining rows, uncertain provenance, omission or excerpt truncation. Source archive
completeness is always explicitly unverified. When the offset ceiling prevents a
further page, `pagination_limit_reached` is true and no unusable next offset is
advertised. Pagination across separate invocations can change if canonical records
change; only each individual invocation has one consistent snapshot.

## Proof and downstream boundary

`tests/services/test_imported_history_evidence.py` provisions a random disposable
PostgreSQL database from **explicit** `TEST_DATABASE_URL`, migrates the canonical
schema, and exercises account/Project ownership, missing/conflicted owners,
OpenAI/Anthropic records, colliding IDs, mixed native additions, uncertain provenance
and times, diary/source/record restrictions, modeling exclusions, incomplete histories,
failed database/metadata reads, deterministic bounds and empty histories. It compares
all public canonical table rows before/after reads, verifies server-enforced read-only
transactions, and uses dependency spies and runtime call guards for forbidden paths.
No disposable database means failed proof, not a skipped successful qualification.

No models, providers, summaries, Personal Facts, Memory Vault writes, approvals,
continuity activation, queues, embeddings, events, connectors, source mutation or
persisted results belong to this reader. No production human-display path is mounted.
Migration Chronicle synthesis, Daily Chronicle, account-wide/cross-Project synthesis,
external briefing, continuity governance, natural import-to-recall qualification,
deployment and release support remain deferred and unproven. Current-state HOLD
and release claims are unchanged.
