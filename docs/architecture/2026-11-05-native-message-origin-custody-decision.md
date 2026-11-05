# Native-message origin custody decision — 2026-11-05

Status: **ACCEPTED — operator decision 2026-11-05; ADR-016 amended.**
Implementation: **pending separate authorization; no runtime or schema change.**
Evidence baseline: `edea2690d4f3a60481e7628dc4c9fb27ab120030`, branch
`codex/stock-compose-migration-source`.
Proposal commit: `a680ff6ed4c43b46c275b668703d06bb8cec10ed` (local at acceptance).
Mainline integration baseline: `c28bc8f46e6896b9dec22d6cc7ba7696260c2b08`, freshly
fetched `origin/main`; this document was imported deliberately without its older
branch current-state changes.
Release: **HOLD**. Reader enforcement and live recall qualification remain open.

## Operator acceptance record

On **2026-11-05**, the operator explicitly supplied **“Operator decision:
APPROVED”** in the task “Accept the Native-Message Custody Amendment,” naming
proposal commit `a680ff6ed`. The operator accepted the nullable same-row witness,
its native-user/accepted-assistant discriminators, atomic trusted creation,
PostgreSQL constraints and immutability, independent reader verification,
legacy-NULL semantics, untrusted import/restore refusal, preservation of existing
accepted assistant witnesses and no retrospective backfill.

[ADR-016](./adr/016-continuity-governance-surface-contract.md#accepted-durable-custody-amendment-2026-11-05)
is the governing accepted authority. This decision records its rationale and
implementation boundary, rather than a second origin authority. Acceptance
changes the authorized architecture only. Migration, reader repair, deployment,
data rewrite and qualification still require separate authorization; no runtime,
fixture or database state is changed by this acceptance task.

## 1. Existing evidence: no ordinary-user witness is sufficient

| Candidate | Verified code boundary | Conclusion |
| --- | --- | --- |
| `NativeOriginAssertion` | [`core/db.py`](../../guardian/core/db.py), `NativeOriginAssertion`, `as_metadata`, `apply_native_origin_assertion` | The typed capability controls a current write, but serializes to plain JSON. Its Python identity is not persisted. |
| Ordinary native user insert | [`core/pgdb.py`](../../guardian/core/pgdb.py), `create_native_user_message` → `create_message`; [`core/db.py`](../../guardian/core/db.py), `_PostgresGuardianDB` equivalents | The insert stores the assertion with the message. Neither adapter stores a separately verifiable native-operation witness. |
| Canonical message row | [`db/models.py`](../../guardian/db/models.py), `ChatMessage` | IDs, account, thread, role, content, timestamps, kind, metadata and participant attribution exist; no ordinary-user creation-custody column exists. Ownership and placement remain independent facts. |
| Generic message audit | [`routes/chat.py`](../../guardian/routes/chat.py), `_persist_message_to_thread`; `AuditLog` and both `write_audit_log` implementations | Audit runs after insertion, including the unproven fallback. It records `create`, `chat_message`, a textual entity ID, account and time, not the trusted creation operation. There is no exact-message FK/unique binding or shared atomicity guarantee; the SQLAlchemy audit adapter suppresses failures. A matching audit row is insufficient. |
| Request/turn or message metadata | Recall grant resolver and completion metadata | A reference can bind a request to a stored message without proving how that message was created. Neither a grant nor assertion-shaped metadata supplies creation custody. |
| Accepted assistant lineage | `ChatCompletionAttempt`, `PgDB.create_assistant_message_for_completion_attempt`, `read_saved_widget_source_provenance` | ADR-016 accepts a narrow exact-assistant witness, described below. It does not prove the origin of the user message in the same turn. |

For the existing assistant witness, join
`chat_completion_attempts.completed_message_id = chat_messages.id` and require
the same `thread_id`, role `assistant`, non-null `accepted_at`, null
`terminal_event_type`, and coherent nonempty canonical `request_id`,
`backend_task_id` and `turn_id`. Validate account through the canonical message
and thread owners, and Project ownership separately. `request_id` is the attempt
PK, `backend_task_id` is unique, and `completed_message_id` references the exact
message; the attempt has no invented account column. The model permits failure
and cancellation terminal values, not a fabricated `COMPLETED` value.

Wrong-message, wrong-thread, failed/cancelled, provisional, contradictory or
unverified-restored attempt data cannot witness native origin. Multiple
incompatible bindings must not be resolved by choosing the convenient one.
`read_saved_widget_source_provenance` illustrates the read relationship; its
authorization checks alone are not a replacement for recall's independent checks.

The [provenance fixtures](./fixtures/history-message-provenance.v1.json) make
the gap explicit: P01 and N04 have identical assertion JSON and identical
non-ID message fields, but different custody and expected eligibility. The
pre-custody `create_chat_message_with_metadata` at `74fd8f489^` copied arbitrary
`extra_meta` into the ORM row. Present-day input guards do not retrospectively
prove custody for every already stored matching object. No production record
was inspected, and no claim is made that a particular live row is forged.

**Finding:** the inspected accepted records contain no sufficient durable
ordinary-user native-creation witness. A reader-only repair cannot infer one.

## 2. Accepted representation

The accepted representation is one new nullable column on the existing
canonical table, pending implementation:

```text
chat_messages.native_origin_custody TEXT NULL, default NULL

NULL                           no new creation witness
'native_user_v1'               Guardian canonical native-user creation
'native_assistant_attempt_v1'  Guardian accepted assistant-attempt creation
```

These are accepted versioned database discriminators, not runtime event,
status or conversation-origin tokens; their persistence is unimplemented. The
source system remains `codexify`.
No extra provenance table, operation ledger, UUID service, graph or signature is
needed. The existing message PK provides exact-row binding; the discriminator
identifies the permitted creation operation. The existing
`extra_meta.message_origin` remains descriptive assertion data and is written in
the same insert, but cannot establish reader authority without custody.

The field's name or string value is not proof by itself. Its evidentiary meaning
depends on **all** of these enforceable conditions:

1. A schema migration introduces it as nullable with no positive default,
   generated inference, data update or backfill. Every existing row is NULL,
   including rows with perfectly shaped native JSON.
2. Only the two enumerated Guardian native-creation operations can select a
   positive value. Their internal SQL/ORM insert path derives it from backend
   operation authority and the existing typed capability, never request JSON.
3. Generic writers, importers, copying and restore cannot supply it. All
   untrusted admission and persistence paths enforce that separation.
4. PostgreSQL constraints reject unsupported values and operation/role mismatch.
   A trigger rejects post-insert changes to custody, including NULL → positive,
   positive → NULL and positive → another value.
5. The writer/admission inventory and disposable-PostgreSQL negative proofs pass
   before a reader may rely on the field. A migration alone is not sufficient.

This closes the old free-form-JSON ambiguity by establishing a new, closed
persistence channel from its first write, not by declaring old JSON trusted.

## 3. Trust boundary and ownership

The nodes are the untrusted client/model/import/archive inputs, Guardian's
authenticated application and workers, and canonical PostgreSQL. Guardian owns
creation decisions; PostgreSQL persists and constrains them. The existing
trusted server SQL boundary is assumed, just as for accepted assistant attempts.
Custody proves the authorized native-creation operation inside that boundary;
it is not cryptographic attestation. Runtime retrieval requires no signatures
or hashing. No signing service, new credentials or key management is required.
Cross-installation proof-preserving restore remains separately governed and
unimplemented.

| Threat or input | Required boundary |
| --- | --- |
| Client, model, tool, provider or importer supplies the new field, including a metadata lookalike | Reject a requested authoritative field; never hydrate it from arbitrary dictionaries. A nested/lookalike value is never queried as the column. Existing handling of untrusted `message_origin` remains protected. |
| Generic insert has a native role, owner or thread | It inserts NULL. Those attributes cannot select the native operation. |
| Buggy metadata merge/replacement | It cannot set, clear or replace the separate column. Database immutability guards protect existing custody and its bound assertion. |
| Operator/table owner or compromised Guardian SQL writer | Outside this mechanism's forgery protection: that actor can also forge canonical attempts. No claim of protection from arbitrary trusted SQL execution is made. |

No new database login, standing user permission or second identity authority is
introduced by the accepted design. If a deployment gives untrusted actors arbitrary writes under the
trusted SQL identity, this design is insufficient there: do not mint or consume
custody until that trust boundary is enforceable. A caller-controlled session
setting such as `SET LOCAL trusted=true` is not an acceptable substitute.

## 4. Creation, mutation and failure rules

### Native user

`routes/chat.py::_create_native_user_message` already selects the native seam
only for the ordinary authenticated user role. Both
`PgDB.create_native_user_message` and
`_PostgresGuardianDB.create_native_user_message` must independently verify the
user role, preserve authenticated owner/thread authority and reject imported
source-lineage claims. They must insert content, protected assertion and
`native_user_v1` in one statement/transaction. The generic helper must not gain
a public JSON parameter that can select this discriminator.

The existing `NativeOriginAssertion` remains a backend capability, not a payload
to deserialize. Shared private persistence plumbing may accept it from these
operations, but a mapping or reconstructed caller assertion is not a capability.
Do not infer which operation occurred from the message role.

### Accepted assistant

`PgDB.create_assistant_message_for_completion_attempt` must lock and verify the
exact canonical attempt, including **non-null accepted_at**, coherent
request/task/turn/thread identity, no failure/cancellation, and no conflicting
source lineage. The present SELECT does not include `accepted_at`; extending
that check is a necessary dependency of this witness, not current proof.

The assistant insert, assertion, `native_assistant_attempt_v1`, and exact
`completed_message_id` binding must commit in the existing conversation
transaction. A failed binding rolls back the insert and witness. An existing
retry returns the original row and original custody without refreshing or
upgrading it. A present but unaccepted/mismatched/terminal attempt cannot mint
custody. The existing no-attempt/fallback write may remain unproven with NULL;
imported/conflicting content must never receive a positive discriminator.

### Database invariants and updates

The migration/model must define a supported-value CHECK and require role `user`
for `native_user_v1`, role `assistant` for `native_assistant_attempt_v1`.
Positive custody requires the paired version-1 `codexify` assertion written by
the native producer; malformed or contradictory assertions fail closed. The
producer validates its zoned timestamp; the timestamp is descriptive, not proof.
Positive-path PostgreSQL CHECKs must coalesce SQL unknown to false: absent JSON
members, JSON null, wrong types or a missing assertion must not pass because a
CHECK expression evaluated to NULL. Validate JSON numeric version 1 distinctly
from booleans or string `"1"`.

The update trigger must reject any custody change for every row. For a row with
custody it also rejects changing its canonical `id`, `thread_id`, `user_id`,
`role`, or reserved `message_origin` subobject. This prevents identity rebinding
and erasure of the bound assertion. Updating unrelated metadata, embedding
status or content under existing edit authority must not mint or refresh
custody. Origin proves record creation, not unchanged text or the truth of its
contents. Existing authorized message deletion removes the same-row witness;
this accepted design creates no new deletion permission or retention requirement.

Moving an existing thread between authorized Projects does not rewrite the
message witness; Project/read authority is resolved again on retrieval.
Per-message copying/reparenting is not authorized to transfer custody: a copy
is a new unproven row, and in-place identity rebinding of a witnessed row is
refused. Any future proof-preserving relocation needs its own accepted contract.

A failed native insert leaves neither row nor witness. A crash before transaction
commit leaves neither; a crash after commit leaves both. Metadata enrichment or
a retry can never upgrade a legacy NULL. There is no new user-message
deduplication scheme: distinct accepted creations remain distinct rows, and any
existing idempotency mechanism must preserve the original row rather than stamp
it again.

Install the nullable column, constraints and trigger together in the migration
transaction before deploying positive writers. Older writers continue to leave
NULL; no cutover timestamp makes those rows trusted. Do not activate recall on
an older reader merely because writers or the schema were upgraded. A downgrade
must refuse to drop custody while positive witnesses exist; deleting or rewriting
them to make downgrade succeed is not authorized. Test both schema creation
paths and this downgrade refusal on disposable PostgreSQL.

## 5. Reader verification and P01/N04 separation

The future `_select_message_excerpts` query must project the custody column and
only necessary provenance/witness fields from canonical storage. The contract's
older `_candidate_message_rows` reference is stale at this baseline; no such
function exists here. Use bounded queries without attempt-join row multiplication
or an unbounded scan. Do not expose raw metadata or provider IDs in receipts.

Verification order:

1. Keep authentication, canonical Project ownership, thread access, content/kind,
   temporal/query bounds and request-scoped model grant checks independent.
2. Reject incompatible native/import, source-account/message/thread and
   creation-linkage evidence. Complete imports are imported; partial/unproven
   claims are unknown; incompatible positive claims are conflicting.
3. A supported custody discriminator plus coherent assertion and immutable
   identity establishes the enumerated native creation. For a new assistant
   witness, independently persisted contradictory attempt lineage still fails
   closed. The marker attests that its exact successful binding was checked at
   creation; it does not require inventing a new success status.
4. With NULL custody, only ADR-016's existing exact trusted assistant witness
   can establish native origin. Plain assertion JSON, a user role or a nearby
   assistant witness cannot establish a user record's origin. Unsupported or
   malformed custody is not a reason to choose a more convenient witness.
5. Only independently eligible native rows receive excerpts and the
   `codexify` source label. Count observed imported/unknown/conflicting message
   exclusions separately from thread exclusions. Existing scan, result and byte
   bounds remain; a bounded receipt must not claim exhaustive coverage.

| Case | Independently verified runtime evidence | Required outcome |
| --- | --- | --- |
| P01, executed as a new canonical user creation after implementation | Actual native operation writes `native_user_v1` with this exact row; guards/constraints apply | Native, subject to all other permissions |
| N04, arbitrary claim through a generic/untrusted path | No native operation; column NULL even if descriptive JSON looks identical | Unknown; no model excerpt |
| Pre-migration P01-like or N04-like stored row | Column NULL; serialized appearance cannot identify its old write path | Unknown unless the accepted exact assistant witness independently applies |
| P08 assistant legacy witness | Exact canonical accepted successful assistant binding | May establish that assistant's origin only |
| N03 conflicting claims | Positive native witness and incompatible import evidence | Conflicting; no model excerpt |
| N11 foreign native record | Origin proof for another account | Account exclusion still wins |

P01/N04 fixture expectations must not be changed to make tests pass. Their
`trusted_evidence_source` descriptions must be realized by real trusted/generic
write operations in runtime tests, not interpreted as a caller-provided trust
flag. The immutable fixture JSON is not itself proof that either operation ran.

## 6. Import, export and restore admission

Generic/import writers must omit the column, never copy it from source objects,
and retain their existing provider-specific origin and lineage. New copies and
legacy rows remain NULL. An import/restore collision must not overwrite a native
row's content/identity while preserving its old custody, or be treated as a
successful custody transfer merely because canonical IDs match. Guard both
service admission and the low-level persistence helpers, with transaction-wide
rollback on a rejected claim/collision.

Exported witness values are claims carried as data, not portable capability
authority. Extend the existing `chat_messages` export projection to carry the
new column with an explicitly versioned archive contract; old formats must not
silently omit positive custody. At this baseline the newest export version is
`account-export.v8`; allocate the next version through the existing version
machinery when implementing, without adding a new export pipeline. Reject an
unsupported requested format for provenance-bearing rows rather than falsely
claiming a lossless export.

Generic uploaded restore must refuse non-null custody claims before any writes,
in every supported archive version, just as its current admission guard refuses
`extra_meta.message_origin`. A copied field, authenticated uploader, hash,
matching manifest or internally coherent ID map cannot authorize reinsertion.
The low-level `restore_account_export_chat_messages` must independently refuse
a non-null custody input and detect collisions with witnessed destination rows;
its explicit column allowlist must never turn source data into authority.
Unknown/imported archives without proof claims may remain NULL under existing
restore rules. Do not silently strip a purported proof and report successful
proof-preserving restoration.

No trusted custody-transfer procedure is selected here. P09 remains the
**future**, separately accepted proof-preserving restore case. Such a procedure
would have to establish original trusted export custody and rebind each exact
record and assistant relationship under canonical-ID remapping. It must preserve
the original creation meaning and assertion time, not mint native creation at
restore time. Current generic restore cannot do that and remains closed to
positive claims. No signing service or backfill is implied.

## 7. Explicit ADR impact

Classification: **explicit ADR-016 amendment accepted 2026-11-05.** Adding a
same-row witness avoids a parallel subsystem, but changes the representation and
reader positive-proof test. The following pre-amendment statements in
[ADR-016](./adr/016-continuity-governance-surface-contract.md#authoritative-chat-message-origin-clarification-2026-11-01)
are reconciled by the accepted amendment; the left column records their prior
wording, not a competing current rule:

| Pre-amendment statement | Accepted change (2026-11-05) |
| --- | --- |
| “Use the existing `ChatMessage.extra_meta` JSON object.” | Retain descriptive JSON, but add the nullable same-row `native_origin_custody` representation and its exclusive creation/admission/immutability rules. |
| “Association with this exact canonical message row supplies the message binding” | Retain exact-row binding, but state that JSON association alone does not establish custody; the controlled discriminator and immutable identity establish the native-operation binding. |
| “Thus existing storage can represent the rule.” | Record that existing JSON stores the assertion but cannot independently prove ordinary-user creation custody across legacy/untrusted serialization; a nullable schema extension is required. |
| Classification row: “Guarded creation assertion for this message, or the exact trusted assistant witness above; no contradictory import evidence” | Require the new verified custody discriminator paired with the assertion for the new creation path, or preserve the existing exact trusted historical assistant witness. NULL legacy user rows remain unknown. |
| Native restore: “Preserve the original assertion/witness and original assertion timestamp; do not stamp the restore as new native creation” | Preserve the target, explicitly distinguish exported claims from reinsertion authority, and require a separately accepted custody-transfer path before a non-null discriminator can be restored/remapped. Generic upload refusal remains mandatory. |

The ban on timestamp cutoffs, unverified trust flags, historical relabeling and
arbitrary matching JSON remains unchanged. The accepted field is usable only
after its writer/mutation/admission boundary is implemented and proven; calling
it a witness is insufficient. ADR-084 request-local grants, ADR-081 canonical
Project ownership and ADR-005 account isolation are unchanged. No other ADR is
created or silently superseded.

The canonical index resolves ADR-084 to
[`084-unified-account-owned-memory-store.md`](./adr/084-unified-account-owned-memory-store.md),
not the absent `084-account-owned-memory-and-explicit-recall.md` filename in
the task. Related governing sources are
[ADR-081](./adr/081-project-ownership-authority.md) and
[ADR-005](./adr/005-runtime-mode-and-account-boundary-invariants.md).

## 8. Next bounded implementation, requiring separate authorization

One next implementation slice should establish **durable custody and its guarded
read projection**, without enabling ordinary-chat advertisement or widening
recall. Its required files/dependencies are concrete:

| Surface | Required files and boundary |
| --- | --- |
| Governance prerequisite recorded | ADR-016, its index and this decision now record the operator's explicit 2026-11-05 acceptance. This does not authorize the implementation slice. |
| Canonical schema | `guardian/db/models.py`; one new Alembic revision in `guardian/db/migrations/versions/`, allocated from the then-current single head, adding the nullable column, CHECKs and immutability trigger/function. No row updates/backfill. Keep model-created and migrated schemas' enforceable invariants consistent. |
| Native producers/persistence | `guardian/core/db.py` and `guardian/core/pgdb.py`: existing native-user seams and accepted assistant-attempt seam, typed/private insertion plumbing, atomic SQL, role/source/acceptance checks and low-level restore/collision refusal. No generic writer defaults to native. |
| Untrusted entry points | `guardian/routes/chat.py`, `guardian/workers/chat_worker.py`: both user-message POST entry paths, the accepted assistant path and fallbacks; reject authoritative-field injection and preserve NULL on unproven paths. |
| Import and other direct ORM writers | Inspect `backend/rag/chatgpt_migration.py`, `guardian/core/hosted_room_messages.py`, `guardian/agents/store.py`, `guardian/core/core_loop_proof.py`, `guardian/core/chat_completion_service.py`, `guardian/workers/voice_worker.py`, `guardian/workers/chat_embedding_worker.py`. They receive no new native authority in this slice; omit/default NULL and preserve guards. Change one only if an actual dictionary hydration, replacement or custody collision dependency is found, recording that reason. |
| Reader | `guardian/core/account_history_recall.py`: `_select_message_excerpts`, classification before excerpt construction, exact assistant witness fallback, content-free message exclusion counts, preservation through response-budget trimming. No new retrieval pipeline. |
| Portability/admission | `guardian/core/pgdb.py` account-export bundle and legacy projections; `guardian/services/account_export.py` version handling; `guardian/services/account_restore.py` admission. Carry claims explicitly, reject untrusted positive restore and incompatible export versions, preserve account/ID-map rules. |
| Tests | Existing `tests/core/test_account_history_recall.py`, `tests/routes/test_account_history_recall.py`, `tests/core/test_message_origin_custody.py`, `tests/routes/test_message_origin_custody.py`, `tests/workers/test_native_assistant_origin.py`, `tests/services/test_account_restore_message_origin.py`; add a focused migration/trigger test under `tests/db/` and focused export compatibility coverage. |
| Documentation | `account-history-recall-contract.md`, `account-export-restore-contract.md`, `00-current-state.md`, and a dated implementation/proof receipt; update fixture persisted-evidence projections only if separately authorized, preserving all existing expected outcomes and trust distinctions. |

Required regressions and disposable PostgreSQL proof:

- Migrate a disposable pre-change database containing arbitrary P01/N04-shaped
  legacy JSON; both remain NULL without data changes. Reject invalid operation
  values, wrong roles, NULL-to-positive updates, removal/replacement of custody,
  identity rebinding and mutation of a witnessed assertion.
- Execute P01/P02 through real canonical native operations and N04 through
  generic/untrusted operations. Directly read back the discriminator and exact
  IDs. Test imported/mixed-origin, unknown, partial, unsupported and conflicting
  claims, including metadata/top-level/encoded archive injection and restored
  attempts that lack trusted custody. Do not manufacture proof by setting the
  custody column in a positive test fixture.
- Prove accepted-at checks, exact successful assistant binding, mismatched
  account/thread/message/request/task/turn, provisional/failure/cancellation,
  replay, concurrent duplicate delivery and transaction fault rollback. A
  returned legacy row is never upgraded by retry.
- Test ordinary metadata merges, full embedding-status replacement and
  legitimate edits preserve custody; generic import/restore collision and
  archive rejection leave every affected family unchanged. Test all supported
  archive versions and an unsupported older export target.
- Execute native/mixed recall against canonical PostgreSQL as well as SQLite
  test projections: only eligible rows reach excerpts/evidence blocks; exact
  observed content-free exclusion counts survive response trimming; account,
  Project, thread/kind, date/query, grant and Command Bus checks still fail
  closed. Keep fixed scan/result/byte limits and disclose bounded coverage.
- Use an explicitly supplied `TEST_DATABASE_URL` with authority to create and
  drop **only uniquely named disposable test databases**. Never substitute
  Preview or infer credentials. SQLite or mocked writers cannot prove
  PostgreSQL CHECK/trigger/JSONB/transaction behavior. No database authority is
  granted by this decision document.

Fresh PostgreSQL proof and an implementation receipt are prerequisites to
calling the custody boundary proven. Current-tip live recall qualification and
ordinary-chat activation remain separate gates; this slice does not repair the
known session-seam, advertisement-forwarding or 500-thread coverage findings.

## 9. Evidence limits and decision closeout

This decision inspected code, schemas, accepted contracts and synthetic fixture
expectations only. It executed no runtime tests, database reads/writes,
migrations, Docker operations or Preview changes. The prior baseline result of
122 passes and 36 PostgreSQL setup errors for missing `TEST_DATABASE_URL`
remains **unproven PostgreSQL coverage**, not an application regression or
successful custody proof.

Documentation validation is the only executable proof class for the acceptance
task: `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py`,
`git diff --check` and scoped `git status --short`. Results and commit identity
are reported in the task closeout. They cannot qualify the mechanism.

**Acceptance is recorded; implementation remains pending.** The accepted
ADR-016 amendment includes the same-row custody/admission rules, generic-restore
refusal and legacy-NULL semantics. A separate implementation task must provide
the migration, guarded writers and readers, and disposable PostgreSQL proof.
Do not begin that task automatically. Release remains HOLD.
