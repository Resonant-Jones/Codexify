# UMS-05C7 Remaining Memory Vault Mutation Authority Revalidation Proof

Date: 2026-09-27

Status: **PASSED — REMAINING MUTATION AUTHORITY REVALIDATED**

```text
UMS05C7_REMAINING_MUTATION_AUTHORITY_REVALIDATED
```

## Correction notice — this receipt supersedes the 2026-09-25 C7 receipt

This revalidation was run against branch truth on 2026-09-27. It
**supersedes** `2026-09-25-ums05c7-remaining-mutation-authority-revalidation.md`
in two material respects:

1. **Ordinary review and lifecycle are no longer persistence-blocked.** The
   2026-09-25 C7 classified `approve`/`reject`/`dispute` and
   `retire`/`restore` as `REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE` because
   at that moment `memory_records` carried only `reviewed_at` / `activated_at`
   (2-way cardinality). UMS-05C8 (`8c2f4a6d9b10`) has since landed typed
   canonical authority, so those six actions are now
   `CURRENT_PERSISTENCE_SUFFICIENT`.
2. **Ordinary content correction is NOT sufficient on current persistence.**
   The 2026-09-25 C7 classified content correction as
   `IMPLEMENTABLE_ON_CURRENT_PERSISTENCE` on the reasoning that
   `memory_provenance` could carry prior/new values. That reasoning was wrong
   and is corrected here: `memory_provenance` has **no typed content
   column**, its only free-form carrier is `extensions`, and `extensions` is
   explicitly non-authority and explicitly forbidden by this task's Invariant 5
   from becoming a hidden content-version store. Prior ordinary-memory content
   is therefore **not durably recoverable** after an in-place correction.

The net effect on Campaign truth is a **change of authorized successor**, not
a re-opening of C7. Detail in "Campaign transition" below.

## Branch / lineage

- Branch: `feature/ums-continued`
- C6 anchor: `a05189d8c6e0f631f78c564e8beab2a9a04a383c` — ancestor of HEAD
  (exit 0)
- Starting HEAD: `c5bf1161cef80e44344a6db1a201b80efc900d2c`
  (`Persist ordinary memory governance state`, i.e. UMS-05C8)
- Index at start: empty
- Branch-local UMS commits between C6 and HEAD:

  ```text
  71a0ac1c8  Revalidate remaining Memory Vault mutation authority   (C7, prior)
  c5bf1161c  Persist ordinary memory governance state              (C8)
  ```

  Nine additional branch-local commits are unrelated WhooshD
  provider/model-path proof documents. No `main` merge, rebase, fetch, pull,
  reset, cherry-pick, or push occurred.

## C1–C6 baseline

| Slice | Capability | Status |
| --- | --- | --- |
| C1 | pin / unpin (record CAS + receipt spine) | CLOSED |
| C2 | pin mutation HTTP adapter | CLOSED |
| C3 | hold / release-hold | CLOSED |
| C4 | Project-scope mutation | CLOSED |
| C5 | stable Persona attribution mutation | CLOSED |
| C6 | direct user-authored canonical creation | CLOSED |
| C7 | remaining mutation authority revalidation (this receipt) | CLOSED |
| C8 | ordinary-memory review + lifecycle state persistence | CLOSED |

## Physical schema inventory (current branch truth)

### `memory_records` — authority-bearing fields

```text
memory_id          VARCHAR(36)  PK
user_id            VARCHAR(255) FK users.id          -- account owns
project_id         INTEGER      FK (projects.id, projects.user_id)  -- Project scopes
semantic_species   VARCHAR(32)  CHECK in MemorySemanticSpecies
text_content       TEXT         nullable             -- current content authority
fact_key / fact_value / fact_confidence               -- Personal-Fact payload
reviewed_at        TIMESTAMPTZ  nullable             -- HISTORY ONLY (post-C8)
activated_at       TIMESTAMPTZ  nullable             -- HISTORY ONLY (post-C8)
pinned             BOOLEAN      NOT NULL default false
held               BOOLEAN      NOT NULL default false
review_state       VARCHAR(32)  NOT NULL              -- CANONICAL REVIEW AUTHORITY
    CHECK memory_records_review_state_check
      IN ('pending','approved','rejected','disputed')
lifecycle_state    VARCHAR(32)  NOT NULL              -- CANONICAL LIFECYCLE AUTHORITY
    CHECK memory_records_lifecycle_state_check
      IN ('active','dormant','retired')
extensions         JSONB        nullable             -- non-authority
created_at / updated_at   TIMESTAMPTZ NOT NULL        -- updated_at = record CAS
```

### `memory_provenance` — typed columns (no content carrier)

```text
provenance_id      VARCHAR(36)  PK
memory_id          VARCHAR(36)  FK (memory_id, user_id)
user_id            VARCHAR(255) FK users.id
source_system      VARCHAR(32)  CHECK
source_record_id   VARCHAR(255) nullable   -- opaque source identity
source_thread_id   INTEGER      nullable   -- FK chat_threads
source_message_id  BIGINT       nullable   -- FK chat_messages
source_import_job_id        VARCHAR(36) nullable
source_export_fingerprint  VARCHAR(128) nullable
source_subject_kind VARCHAR(32) nullable  -- CHECK; includes 'vault'
source_subject_id  VARCHAR(255) nullable
is_imported        BOOLEAN      NOT NULL
extensions         JSONB        nullable  -- explicitly NON-AUTHORITY
created_at         TIMESTAMPTZ  NOT NULL
```

Every typed column on `memory_provenance` is **source identity**, not content
state. There is **no typed prior-content column**.

### Revision families present in the schema

```text
personal_fact_revisions   -- PersonalFactRevision: actor, action,
                          --   field_changed, old_value TEXT, new_value TEXT,
                          --   reason, created_at
persona_profile_revisions -- PersonaProfileRevision (config lineage)
```

```text
ordinary-memory revision family: ABSENT
```

`Base.metadata.tables` contains no `memory_revisions` (or equivalent) table.
Memory tables present: `memory_entries` (legacy), `memory_records`,
`memory_persona_links`, `memory_provenance`.

### Personal Facts authority

```text
personal_facts.status     CHECK IN ('candidate','verified','disputed','archived')
personal_facts.is_active  BOOLEAN NOT NULL
personal_fact_evidence    (id, fact_id, source_message_id, excerpt, modality,
                           confidence, ...)
personal_fact_revisions   (id, fact_id, actor, action, field_changed,
                           old_value TEXT, new_value TEXT, reason, created_at)
```

Existing Personal Facts write routes in `guardian/routes/personal_facts.py`:
`approve_candidate`, `reject_candidate`, `dispute_personal_fact`,
`update_personal_fact` (7 write-method routes total).

`personal_fact_revisions.old_value` / `new_value` are **typed TEXT columns** —
this is the reference specimen for what a first-class revision family looks
like in this repository.

## Read projection (current)

`guardian/services/memory_vault_read.py` derives canonical posture **from the
typed columns**, not from timestamp nullability:

```python
review_posture = row.review_state if row.review_state in (
    'pending','approved','rejected','disputed') else 'pending'
lifecycle_posture = row.lifecycle_state if row.lifecycle_state in (
    'active','dormant','retired') else 'dormant'
```

The read projection normalizes canonical state; it does not create it. A
`rejected` row reads as `rejected`; a `retired` row reads as `retired`. This
satisfies Invariant 9.

## Required classification matrix

| Mutation | Domain | Required authority | Current physical authority | Persistence sufficient? | Specialized delegation? | Revision/receipt requirement | UMS-04 impact | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| content correction | ordinary episodic | content + durable prior-version history | `memory_records.text_content` (current only); no prior-version family | **NO** | no | first-class prior-content revision required; receipt alone insufficient | new export family/field required | **NEW_CANONICAL_PERSISTENCE_REQUIRED** |
| content correction | Personal Fact | Personal Facts revision authority | `personal_fact_revisions.old_value/new_value` | yes | yes | already provided by `personal_fact_revisions` | already covered | **CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION** |
| approve | ordinary memory | review authority | `memory_records.review_state` (4-token CHECK, NOT NULL) | yes | no | receipt only | v4 carries `review_state` | **CURRENT_PERSISTENCE_SUFFICIENT** |
| approve | Personal Fact | Personal Facts verification authority | `personal_facts.status='verified'` | yes | yes | receipt via PF service | already covered | **CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION** |
| reject | ordinary memory | review authority | `memory_records.review_state` | yes | no | receipt only | v4 carries `review_state` | **CURRENT_PERSISTENCE_SUFFICIENT** |
| reject | Personal Fact | Personal Facts authority | `personal_facts.status='archived'` | yes | yes | receipt via PF service | already covered | **CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION** |
| dispute | ordinary memory | review authority | `memory_records.review_state` | yes | no | receipt only | v4 carries `review_state` | **CURRENT_PERSISTENCE_SUFFICIENT** |
| dispute | Personal Fact | Personal Facts authority | `personal_facts.status='disputed'` | yes | yes | receipt via PF service | already covered | **CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION** |
| retire | ordinary memory | lifecycle authority | `memory_records.lifecycle_state` (3-token CHECK, NOT NULL) | yes | no | receipt only | v4 carries `lifecycle_state` | **CURRENT_PERSISTENCE_SUFFICIENT** |
| retire | Personal Fact | Personal Facts status/activation authority | `personal_facts.status='archived'` + `is_active=false` | yes | yes | receipt via PF service | already covered | **CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION** |
| restore | ordinary memory | lifecycle authority | `memory_records.lifecycle_state` | yes | no | receipt only | v4 carries `lifecycle_state` | **CURRENT_PERSISTENCE_SUFFICIENT** |
| restore | Personal Fact | Personal Facts status/activation authority | `personal_facts.status` + `is_active` | yes | yes | receipt via PF service | already covered | **CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION** |

## Persistence-sufficiency test applied

For the six ordinary-memory review/lifecycle actions, every one of the ten
sufficiency conditions holds:

1. authority-bearing state exists — `review_state` / `lifecycle_state`;
2. it is in canonical persistence, not receipt metadata;
3. it distinguishes every contractually required state (4 review / 3 lifecycle);
4. it survives restart (persisted TIMESTAMPTZ-free VARCHAR, NOT NULL);
5. account/Project/Persona invariants remain enforceable (FK + CHECK
   unchanged);
6. read projection derives correct posture without inventing authority;
7. a receipt can be appended without becoming authoritative;
8. `account-export.v4` exports and restores both fields;
9. restore preserves semantics (C8 restore validates the token vocabulary and
   fails closed on invalid explicit values);
10. no new migration / column / export family / schema version is required.

For ordinary-memory content correction, conditions 1, 2, 3, 5, 6, 8 and 9
**fail**: prior-content authority does not exist in canonical persistence, and
cannot be truthfully created inside `extensions`.

## Content-correction analysis

Required semantics: update canonical episodic text, preserve the prior
authoritative text, preserve the new authoritative text, identify actor and
mutation source, preserve reason / request reference, CAS-protect the update,
return canonical readback, and export/restore the complete correction history.

Findings:

- `memory_records.text_content` is the **current** content authority. A
  correction is an in-place UPDATE of that column.
- `updated_at` is a valid CAS token (reused from C1–C6) and is advanced
  database-authored.
- `memory_provenance` is one-to-many and append-only, so a receipt per
  correction is possible. But every **typed** provenance column is source
  identity. The prior text has no typed home.
- `extensions` is JSONB, explicitly documented as non-authority, and
  Invariant 5 of this task forbids it from becoming a content-version store.
  A `previous_values = {"text_content": "..."}` payload inside `extensions`
  would be an audit note, not authority-bearing revision state — and
  Invariant 6 of this task states plainly that a receipt saying content
  changed is not equivalent to a durable prior content revision.
- Consequently, after an in-place correction the prior canonical text is
  **not reconstructable** from canonical authority.
- Contrast: `personal_fact_revisions` stores `old_value` / `new_value` as
  typed TEXT in a first-class family. Ordinary memory has no equivalent.

**Conclusion:** ordinary-memory content correction is
`NEW_CANONICAL_PERSISTENCE_REQUIRED`.

```text
UMS-04 PORTABILITY OBLIGATION: REQUIRED BEFORE MUTATION IMPLEMENTATION
```

Minimum required concept (identified, not designed or built):

- a first-class ordinary-memory content-revision family owning prior and new
  authoritative text, actor, action, reason, and a stable ordering identity;
- it must be exported by `account-export.v4` (or require a revisited
  schema-version decision) and rehydrated by the restore executor;
- mandatory proofs once built: export → restore → re-export semantic
  equality, second-restore idempotency, and per-revision ordering stability.

## Review analysis

The normative review vocabulary is `pending | approved | rejected | disputed`.

- Before C8 these collapsed into a 2-way `reviewed_at IS NULL / NOT NULL`
  test, which conflated `pending` with `rejected` and with `disputed`.
- C8 (`8c2f4a6d9b10`) added `memory_records.review_state` VARCHAR(32) NOT NULL
  with `CHECK review_state IN ('pending','approved','rejected','disputed')`,
  and the `MemoryReviewState` protocol enum with exactly those four values.
- The C8 backfill mapped `reviewed_at IS NULL → pending`,
  `NOT NULL → approved` and deliberately **synthesized no** `rejected` or
  `disputed` rows.
- A future approved → disputed → re-approved cycle is expressible by writing
  `review_state` alone; `reviewed_at` remains history and is not overloaded.
- `account-export.v4` carries `review_state`; restore validates it against the
  canonical vocabulary and fails closed on an invalid explicit value.

**Conclusion:** ordinary-memory `approve`, `reject`, and `dispute` are each
`CURRENT_PERSISTENCE_SUFFICIENT`. They are not authorized to be implemented in
this task.

## Lifecycle analysis

The normative ordinary lifecycle vocabulary is `active | dormant | retired`.
`archived` is **not** an ordinary-memory lifecycle token.

- Before C8 `activated_at IS NULL / NOT NULL` conflated
  `dormant` with `retired` and with never-activated.
- C8 added `memory_records.lifecycle_state` VARCHAR(32) NOT NULL with
  `CHECK lifecycle_state IN ('active','dormant','retired')`, and the
  `MemoryLifecycleState` protocol enum with exactly those three values.
- Retirement is distinct from `held`, from `pinned`, from review state, and
  from ambient-retrieval exclusion. It is its own canonical token.
- Restore-from-retirement is a `lifecycle_state` write from `retired` to a
  prior state; it does not manufacture a new record, and because
  `lifecycle_state` is a discrete token it does **not** erase activation
  history the way clearing `activated_at` would.
- `account-export.v4` carries `lifecycle_state`; restore validates it and
  fails closed on an invalid explicit value.

**Conclusion:** ordinary-memory `retire` and `restore` are each
`CURRENT_PERSISTENCE_SUFFICIENT`. They are not authorized to be implemented in
this task.

## Personal Facts delegation analysis

Personal Facts already own a complete, separate, single writable authority:

- review: `status ∈ {candidate, verified, disputed, archived}`;
- lifecycle: `is_active` plus `status='archived'`;
- revision: `personal_fact_revisions.old_value` / `new_value`;
- evidence: `personal_fact_evidence`;
- write routes: `approve_candidate`, `reject_candidate`,
  `dispute_personal_fact`, `update_personal_fact`.

A future Vault action against a `verified_personal_fact` or
`candidate_unreviewed_fact` row must delegate to that authority in the same
transaction that appends the Vault receipt. It must not write
`review_state` / `lifecycle_state` as a competing second truth — those columns
are ordinary-memory governance axes and using them to drive Personal Facts
would create exactly the dual-writable-truth this task forbids (Invariant 4).

**Conclusion:** all six Personal Facts mutations are
`CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION`.

## UMS-04 portability analysis

`account-export.v4` currently exports and restores the canonical families
`memory_records`, `memory_persona_links`, `memory_provenance`,
`persona_subjects`, `persona_subject_bindings`, plus Projects and legacy
persona-profile state. The `memory_records` field set after C8 is:

```text
memory_id, user_id, project_id, semantic_species, text_content,
fact_key, fact_value, fact_confidence, reviewed_at, activated_at,
pinned, held, review_state, lifecycle_state, extensions,
created_at, updated_at
```

Per-mutation export/restore survival:

| Mutation | Survives current export → restore → export? |
| --- | --- |
| ordinary approve / reject / dispute | YES — `review_state` is an exported, restored, identity-compared field |
| ordinary retire / restore | YES — `lifecycle_state` likewise |
| Personal Facts (all six) | YES — Personal Facts are already inside the v4 canonical families |
| ordinary content correction | **NO** — no prior-content authority exists to export |

`PORTABILITY GAP = YES` for ordinary content correction only. That mutation
stays unauthorized until a revision family and its portability land atomically
with it.

## Reusable mutation spine (C1–C6 primitives that survive)

The following remain reusable for whichever mutation is authorized next:

- authenticated account authority, constructor-bound, no per-call override;
- record-level `memory_records.updated_at` CAS with database-authored
  advancement;
- single-PostgreSQL-transaction topology with rollback on receipt failure;
- append-only `memory_provenance` receipt under
  `memory-vault-mutation.v1`;
- canonical `MemoryVaultReadService` readback;
- internal-only route control plane with OpenAPI hiding, feature-flag
  disable, and quarantine precedence.

These are reusable **transaction infrastructure**. They do not substitute for
the missing content-revision persistence.

## ADR impact

- **Aligned with ADR-084.** C7 changes no accepted semantics.
- **No contract contradiction found.** ADR-084, the Unified Memory Store
  contract, the Memory Vault contract, and the Account Export + Restore
  contract agree on the four-value review vocabulary, the three-value
  lifecycle vocabulary, and the requirement that content correction be
  revisioned.
- **ADR-081 Project ownership and ADR-082 Persona authority boundaries
  preserved.** C7 authorizes no action that alters them.
- No ADR changed. No contract edited.
- The new-persistence requirement identified here is a persistence gap in
  implementing **already-frozen** ADR-084 semantics, so it does **not** require
  a new ADR.

## Invariants check

- Account ownership — preserved; every future mutation stays
  authenticated-account scoped, cross-account stays indistinguishable from
  not-found.
- Project scoping — preserved; correction/review/lifecycle must not alter
  Project authority.
- Persona attribution — preserved; transitions do not transfer ownership.
- Personal Facts single authority — preserved; delegation only, no second
  writable truth.
- Provenance non-authority — preserved; `extensions` is not authorized as a
  review, lifecycle, or content-version store.
- Revision integrity — **this is the finding**: ordinary-memory correction
  currently lacks durable prior-content authority.
- Review/lifecycle separation — preserved; both are discrete canonical
  tokens, and retirement is not hold / unpin / rejection / deactivation /
  projection exclusion.
- Portability before implementation — enforced; the blocked mutation stays
  unauthorized.
- No authority in derived projection — preserved; read normalizes, never
  creates.

## Contradictions

None. No `BLOCKED_BY_CONTRACT_CONTRADICTION` classification was issued.

## Sole successor

```text
NEXT_PREREQUISITE =
  UMS-05C8 ORDINARY MEMORY CONTENT REVISION PERSISTENCE + UMS-04 PORTABILITY
```

Dependency-order reasoning:

- Ordinary review and lifecycle mutations are now persistence-sufficient, so
  they no longer gate on anything and are not the smallest outstanding
  prerequisite.
- Ordinary content correction is the only remaining category that is
  persistence-blocked, and it is blocked on exactly one missing concept: a
  first-class ordinary-memory content-revision family, plus its UMS-04
  export/restore coverage.
- Per the successor rule, when any remaining mutation requires new canonical
  persistence, the next slice is the persistence/portability prerequisite —
  **not** the mutation implementation.

```text
REMAINING MUTATION IMPLEMENTATION: BLOCKED ON PERSISTENCE + UMS-04 PORTABILITY FOLLOW-THROUGH
```

The six ordinary-memory review/lifecycle mutations are classified
`CURRENT_PERSISTENCE_SUFFICIENT` but remain **NOT AUTHORIZED** for
implementation in this task. They may be authorized individually by a later
Campaign decision, after this prerequisite lands.

## Campaign transition

Required terminal shape:

```text
UMS-05:  OPEN
UMS-05A: CLOSED
UMS-05B: CLOSED
UMS-05C: OPEN
UMS-05C1: CLOSED
UMS-05C2: CLOSED
UMS-05C3: CLOSED
UMS-05C4: CLOSED
UMS-05C5: CLOSED
UMS-05C6 DIRECT USER-AUTHORED VAULT CREATION: CLOSED
UMS-05C7 REMAINING MUTATION AUTHORITY REVALIDATION: CLOSED
UMS-05C8 ORDINARY MEMORY REVIEW AND LIFECYCLE STATE PERSISTENCE: CLOSED
UMS-05C9 ORDINARY MEMORY CONTENT REVISION PERSISTENCE + UMS-04 PORTABILITY: AUTHORIZED
UMS-05C10 REVIEW / LIFECYCLE MUTATION WRITERS: NOT AUTHORIZED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+: NOT AUTHORIZED
UMS-06+: NOT AUTHORIZED
```

**This renames the previously authorized UMS-05C9.** The prior Campaign line
read `UMS-05C9 ORDINARY MEMORY CONTENT CORRECTION: AUTHORIZED`, which assumed
correction was implementable today. This revalidation withdraws that
authorization and replaces it with the persistence/portability prerequisite
that correction actually needs. Ordinary content-correction *implementation*
moves behind that prerequisite.

## Validation results

```text
alembic heads                          → exactly one head: 8c2f4a6d9b10
tests/services/test_memory_vault_creation.py        → passed
tests/services/test_memory_vault_mutation.py        → passed
tests/services/test_memory_vault_read_projection.py→ passed
tests/routes/test_memory_vault.py                   → passed
tests/routes/test_memory_vault_activation.py        → passed
tests/services/test_account_restore_unified_memory.py → 48 passed
python scripts/validate_docs.py                     → PASS
git diff --check                                    → PASS
```

Test-environment notes (no code impact): the dedicated `/tmp/.s.PGSQL.55432`
authority is unavailable in this sandbox, so proof used the pre-existing
Homebrew PostgreSQL 17.6 server on `127.0.0.1:5432` with the dedicated
`codexify_test_runner` role (LOGIN, CREATEDB, NOSUPERUSER) and the
qualified disposable-child-database pattern. The `gitleaks` pre-commit hook
cannot bootstrap its Go toolchain in this sandbox, so it is skipped narrowly
and must run at branch integration.

## No release impact

C7 added no runtime capability, no route, no migration, no token, and no
frontend. Nothing in this receipt may be read as supported-path, Beta, or
Private Preview qualification. The work is branch-local on
`feature/ums-continued` and is not merged into the current `main`.
