# UMS-02C Stable Persona-Subject Persistence Proof

Date: 2026-09-07

Status: **POSTGRESQL QUALIFIED — UMS-02 CLOSURE PROOF**

## Qualification identity

- Execution lane: architecture-impact persistence and authorization
- Starting HEAD: `00ff9f7025fb6c8bee02b753e9ddee904a7e7443`
- Starting Alembic head: `d4e8f1a2b6c9`
- Candidate Alembic head after the bounded implementation:
  `e5a9c2f7b4d1`
- Final Alembic head: `e5a9c2f7b4d1` (single head)
- Implementation-only fingerprint before qualification:
  `76d70cdbace4ed29f18b92d904df49d4690525beddeb866d1e123f4f9bb4c715`
- Implementation-only fingerprint after qualification:
  `76d70cdbace4ed29f18b92d904df49d4690525beddeb866d1e123f4f9bb4c715`
  (identical — no production code, ORM schema, or migration change)

## Implemented bounded surface

The implementation adds only the persistence substrate authorized by UMS-02C:

- `persona_subjects` has an opaque UUID string identifier, an account owner,
  optional descriptive profile-name snapshot, canonical `active | retired`
  lifecycle, timestamps, and the composite unique key needed to enforce
  account-consistent bindings.
- `persona_subject_bindings` records the source kind and identifier, both
  account columns, a composite foreign key to the owned subject, half-open
  validity timestamps, and the required active-binding partial unique index.
- The migration classifies every legacy `Persona` and `PersonaProfile` before
  it inserts any backfill rows. Persona ownership derives only from
  `personas.user_id`; profile ownership derives only from
  `persona_profile_bindings.owner_account_id`. Missing, malformed, duplicate,
  or missing-account evidence aborts the migration without a fallback owner or
  a partial source backfill.
- Every proven legacy source gets its own active subject and binding. IDs are
  deterministic UUIDv5 values keyed only by the source kind and canonical
  source identifier; no source names, prompts, Project fields, profile
  similarity, or lifecycle flags take part. A legacy inactive `Persona` still
  gets an active durable subject as required.
- `ensure_persona_subject` is server-owned and accepts only a session, the
  authenticated account, source kind, and source ID. It derives ownership and
  timestamps from the canonical source, rejects account mismatch and invalid
  binding history, and returns or creates exactly one current active subject.

No route, frontend, worker, memory link, exporter, restore path, Project
authority surface, PersonaProfile ownership rule, or lifecycle-transition API
was added. `Persona.is_active` remains separate from the canonical
Persona-subject lifecycle.

## Qualification environment

- Docker Desktop reachable from the executing harness (`docker info` returned
  `DOCKER_OK`).
- Disposable PostgreSQL 17.11 (Debian) container started on
  `127.0.0.1:55438`, used only for three isolated test databases
  (`codexify_ums02c_migration`, `codexify_ums02c_generic`,
  `codexify_ums02c_target`) and destroyed on exit.
- No live Codexify database, private-preview database, or any user-bearing
  database was contacted.

## Original qualification result (first attempt)

The first PostgreSQL qualification run produced:

```text
tests/migration/test_persona_subject_identity_migration.py .FFF          [ 40%]
tests/migration/test_persona_profile_manifest_binding_migration.py ....  [ 80%]
tests/migration/test_thread_persona_profile_revision_migration.py .F     [100%]
================== 4 failed, 6 passed, 15 warnings in 12.17s ===================
```

Two test-harness failure classes were observed. No UMS-02C migration
correctness defect was exposed; both failures were fixture / harness
defects in tests, not in production code.

### Harness defect class A — JSON fixture parameter typing

Three tests in `tests/migration/test_persona_subject_identity_migration.py`
inserted `PersonaProfile` revision fixtures via `jsonb_build_object(...)`.
The bound `:profile_id` parameter was used twice in the same statement:
as the column value for `profile_id` (`character varying`) and inside
`jsonb_build_object(...)` (no type hint). PostgreSQL could not infer a
type for the jsonb usage and reported:

```text
psycopg.errors.AmbiguousParameter: could not determine data type of parameter $1
LINE 8:                     'profileIdentity', $1,
```

After the first repair attempt placed `CAST(:profile_id AS TEXT)` only
inside `jsonb_build_object`, PostgreSQL then reported an "inconsistent
types deduced for parameter $1 (text versus character varying)" because
the same parameter carried two different inferred types at its two
positions.

### Harness defect class B — historical revision test against current-head schema verification

`tests/migration/test_thread_persona_profile_revision_migration.py::test_real_chat_adapters_atomically_write_and_clear_pins`
intentionally upgrades a disposable database only to the historical
`PIN_REVISION = d4e0f2a5b7c9` (one revision before UMS-02C's
`e5a9c2f7b4d1`) and then constructs `GuardianDB(database_url)`.
Production `_PostgresGuardianDB.__init__` runs
`verify_schema_consistency(self.engine)` on first use, which raises:

```text
RuntimeError: Expected database tables missing:
['persona_subject_bindings', 'persona_subjects'].
Apply latest Alembic migrations.
```

The test's intent is to prove Persona pin adapter behavior at the
historical schema. The current-head production schema verification is
correct runtime posture; it is not the correct gate for a test that
deliberately operates against an older schema.

## Test-harness repairs (the only two changes between the two qualification runs)

### Repair 1 — narrow `CAST(:profile_id AS TEXT)` in the JSONB fixture helper

File: `tests/migration/test_persona_subject_identity_migration.py`,
helper `_insert_profile_revision`.

Change: added a single explicit PostgreSQL `TEXT` cast at the
column-value position (first use of `:profile_id`):

```sql
INSERT INTO persona_profile_revisions (
    profile_id, revision, api_version, manifest_json, created_at
) VALUES (
    CAST(:profile_id AS TEXT), :revision, 'codexify.persona/v1',
    jsonb_build_object(
        ...
        'profileIdentity', :profile_id,
        ...
    ),
    :created_at
)
```

Both positions of the bound `:profile_id` now resolve to `text`. The
stored JSON value remains the exact source profile ID string; no fixture
ID was hardcoded; no parameter binding was replaced with unsafe
formatting; no migration implementation was changed. The same pattern
already existed in `tests/migration/test_thread_persona_profile_revision_migration.py`
(`CAST(:identity AS text)` for `to_jsonb(CAST(:identity AS text))`).

Narrow verification: `tests/migration/test_persona_subject_identity_migration.py`
ran as **4 passed, 0 failed, 0 errors, 0 skipped**.

### Repair 2 — historical-revision `GuardianDB` construction without current-head schema verification

File: `tests/migration/test_thread_persona_profile_revision_migration.py`.

Added a test-only helper `_historical_guardian_db(db_url)` that builds
a `GuardianDB` facade via `GuardianDB.__new__(GuardianDB)` plus a
`_PostgresGuardianDB.__new__(_PostgresGuardianDB)` instance whose
`engine`, `SessionLocal`, `db_url`, and compatibility flags are wired
to the same parameters that production `__init__` would use. Production
`__init__` is skipped, so `verify_schema_consistency` is not called.
Adapter methods (`set_thread_active_profile_id`, `get_chat_thread`,
`update_thread`) continue to execute against the real database at the
historical revision using the same SQLAlchemy ORM session the production
adapter uses.

This mirrors the existing repository test pattern from
`tests/core/test_project_lifecycle.py` and
`tests/core/test_chat_message_provenance_persistence.py`, which already
use `_PostgresGuardianDB.__new__` to bypass `__init__` for fixture
construction. The helper is test-only and is colocated with the
historical-revision migration test that needs it.

Production `GuardianDB`, `_PostgresGuardianDB`, and
`verify_schema_consistency` are unchanged. The current-head
`EXPECTED_TABLES` set is unchanged. No runtime flag was added to bypass
verification. `PgDB(database_url)` continues to construct directly
because `PgDB.__init__` does not perform schema verification.

Narrow verification: `tests/migration/test_thread_persona_profile_revision_migration.py`
ran as **2 passed, 0 failed, 0 errors, 0 skipped**.

## Full qualification results (after harness repair)

| Step | Command | Result |
| --- | --- | --- |
| Pre-flight | `git rev-parse HEAD` | `00ff9f7025fb6c8bee02b753e9ddee904a7e7443` |
| Pre-flight | Alembic static heads | `e5a9c2f7b4d1` (single head) |
| Pre-flight | Implementation fingerprint before | `76d70cdbace4ed29f18b92d904df49d4690525beddeb866d1e123f4f9bb4c715` |
| Pre-flight | Git index empty | yes |
| 1 | `tests/migration/test_persona_subject_identity_migration.py` | 4 passed |
| 1 | `tests/migration/test_persona_profile_manifest_binding_migration.py` | 4 passed |
| 1 | `tests/migration/test_thread_persona_profile_revision_migration.py` | 2 passed |
| 1 combined | combined migration group | **10 passed, 0 failed, 0 errors, 0 skipped** |
| 2 | `tests/test_migrations.py` (generic parity) | **1 passed, 0 skipped** |
| 3 | fresh target `upgrade head` | reached `e5a9c2f7b4d1 (head)` |
| 4 | repeat `upgrade head` | no-op success; `current` = `e5a9c2f7b4d1 (head)` |
| 5 | `\d persona_subjects` (psql) | full constraints visible |
| 5 | `\d persona_subject_bindings` (psql) | full constraints visible |
| 6 | resolver + legacy Persona regression | **17 passed** |
| 7 | adjacent export regression | **27 passed** |
| 8 | final `alembic heads` | `e5a9c2f7b4d1 (head)` |
| 8 | final `alembic history` | one linear lineage ending at `e5a9c2f7b4d1` |
| 8 | implementation fingerprint after | `76d70cdbace4ed29f18b92d904df49d4690525beddeb866d1e123f4f9bb4c715` (identical) |
| 9 | disposable container teardown | `codexify-ums02c-postgres` removed |

### Actual PostgreSQL constraint inventory

`persona_subjects`:

```text
persona_subject_id    varchar(36)   NOT NULL  PK
user_id               varchar(255)  NOT NULL  FK -> users(id) ON DELETE CASCADE
display_name_snapshot varchar(255)  NULL
lifecycle             varchar(16)   NOT NULL  DEFAULT 'active'
                                       CHECK (lifecycle IN ('active','retired'))
created_at            timestamptz    NOT NULL  DEFAULT now()
updated_at            timestamptz    NOT NULL  DEFAULT now()
UNIQUE (persona_subject_id, user_id)
```

`persona_subject_bindings`:

```text
binding_id         varchar(36)   NOT NULL  PK
persona_subject_id varchar(36)   NOT NULL  FK -> persona_subjects(persona_subject_id, user_id) ON DELETE CASCADE
subject_user_id    varchar(255)  NOT NULL  FK -> users(id) ON DELETE CASCADE
source_account_id  varchar(255)  NOT NULL  FK -> users(id) ON DELETE CASCADE
                   CHECK (source_account_id = subject_user_id)
ref_kind           varchar(32)   NOT NULL  CHECK (ref_kind IN ('persona','persona_profile'))
ref_id             varchar(128)  NOT NULL
valid_from         timestamptz    NOT NULL
valid_until        timestamptz    NULL
                   CHECK (valid_until IS NULL OR valid_until > valid_from)
created_at         timestamptz    NOT NULL  DEFAULT now()
PARTIAL UNIQUE (ref_kind, ref_id) WHERE valid_until IS NULL
```

Every constraint the test suite asserts as required is present in the
live PostgreSQL schema.

## ADR impact

Aligned with existing ADRs. No ADR change.

- ADR-081 Project ownership authority: unchanged.
- ADR-082 Persona Profile manifest and binding authority: unchanged.
- ADR-084 Unified Account-Owned Memory Store: unchanged.

The repairs altered only two test files. The repairs do not reinterpret
account authority, Persona/Profile equivalence, Persona-subject
lifecycle, migration behavior, schema-verification production policy, or
memory ownership.

## Invariant check

- Repair only test-harness behavior: confirmed.
- UMS-02C migration code unchanged: confirmed (fingerprint identical).
- ORM schema unchanged: confirmed (fingerprint identical).
- `GuardianDB` current-head schema consistency checks unchanged:
  confirmed (`verify_schema_consistency` source unchanged).
- No runtime flag added to bypass verification: confirmed.
- No historical revision reinterpreted as current-head: confirmed.
- No PostgreSQL errors suppressed: confirmed (no `try/except` around
  `verify_schema_consistency`, no swallowed exceptions).
- `Persona.is_active` remains selection state, not subject lifecycle:
  confirmed.
- Pi fixture remains untouched and unstaged: confirmed
  (`tests/pi/fixtures/fake_pi_package/package.json` still in tree but
  not staged).

## Non-impact and release boundary

- ADR-081, ADR-082, and ADR-084 are unchanged.
- The normative Unified Memory Store Contract records the qualification
  outcome in §4.5; the contract itself is unchanged in its semantic
  doctrine. UMS-02C persistence is now PostgreSQL-qualified internal
  persistence. No unified memory storage, persona-aware recall,
  export/restore coverage for Persona subjects, or Beta/release widening
  is claimed.
- The known unrelated Pi fixture remains untouched and unstaged:
  `tests/pi/fixtures/fake_pi_package/package.json`.

## Validation

`scripts/validate_docs.py` ran after the proof-doc and Campaign README
updates; no doc-side errors reported. See the final closeout commit for
the exact validation transcript.

## Decision

```text
UMS-02A STABLE PERSONA SUBJECT CONTRACT: PASSED
UMS-02B PERSONA SUBJECT LIFECYCLE TOKENS: CLOSED
UMS-02C PERSONA SUBJECT PERSISTENCE: PASSED
UMS-02: CLOSED
UMS-03: AUTHORIZED TO START
RUNTIME/RELEASE IMPACT: INTERNAL PERSISTENCE ONLY
```