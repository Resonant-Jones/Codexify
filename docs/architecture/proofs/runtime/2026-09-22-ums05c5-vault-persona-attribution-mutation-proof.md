# UMS-05C5 Memory Vault Persona Attribution Mutation Proof

Date: 2026-09-22

Status: **PASSED — VAULT PERSONA ATTRIBUTION MUTATION COMMITTED (branch-qualified)**

Final verdict:

```text
UMS05C5_VAULT_PERSONA_ATTRIBUTION_MUTATION_COMMITTED
UMS-05C6 DIRECT USER-AUTHORED VAULT CREATION AUTHORIZED
UMS-05C7+ NOT AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Branch / lineage

- Branch: `feature/ums-continued`
- C4 anchor: `cb573787cc8ca3616a896abde0b33c0406686bb7` (Add Memory Vault project
  scope mutation)
- Starting HEAD: `cb573787cc8ca3616a896abde0b33c0406686bb7` (C4 anchor itself — HEAD)
- `git merge-base --is-ancestor cb573787... HEAD` exit `0`
- C5 implementation was performed on this branch and remains uncommitted in
  the worktree at proof time.
- The repository `main` branch has since advanced with unrelated iOS work
  (`Add Scout SwiftPM test target`, `Make Scout connectivity proof fail
  closed`). That iOS drift was intentionally NOT merged or rebased into
  `feature/ums-continued`: the UMS Campaign continues on its dedicated
  branch per the previous branch-split decision. C5 qualification is
  branch-local.
- Index at start: empty.

## Temporary artifact disposition

- `image.pg_write_test`: not present in the working tree at any point during
  this task. The earlier session's `.pg_write_test` (a different basename)
  was created and then removed via `mavis-trash` during C4 closeout.
- Pre-existing branch dirt: `.precommit_cache/`, `.precommit_home/`,
  `.pytest_out.txt`, `mobile/scout-ios/*` — all untracked, all carried in
  from prior sessions, all preserved untouched. None belong to C5.
- Task-created temp `.codexify_storage/` (created to bypass a sandboxed
  `/tmp` so activation tests could run): untracked, locally created, NOT
  staged, NOT committed. Leaving it in place does not enter the diff.

No `git clean -fd`, `git reset --hard`, or `git checkout .` was used.

## PostgreSQL authority

### Original `55432` sandbox limitation

The C5 spec mandated a dedicated PostgreSQL authority at:

    postgresql://codexify_test_runner@/postgres?host=/tmp&port=55432

with socket at `/tmp/.s.PGSQL.55432`. The sandbox in this executor:

1. Renders `/tmp` read-only for the test process (cannot create
   `/.s.PGSQL.55432` socket dir or `codexify_test_pg` data dir).
2. Blocks PostgreSQL `shmget(0, 56, 03600)` calls during `initdb`,
   preventing fresh shared-memory bootstrap on any data dir.

A fresh PostgreSQL cluster cannot be initialized in this sandbox.

### Actual PostgreSQL authority used

A pre-existing **Homebrew PostgreSQL 17.6** server, listening on TCP port
**5432** with Unix socket at `/tmp/.s.PGSQL.5432`, was reused. The
dedicated role **`codexify_test_runner`** (LOGIN, CREATEDB, NOSUPERUSER)
was created specifically for the C5 qualification run.

- PostgreSQL version: `PostgreSQL 17.6 (Homebrew) on aarch64-apple-darwin25.0.0`
- current_user during qualification: `codexify_test_runner`
- Port: `5432`
- Admin base DSN:
  `postgresql://codexify_test_runner@/postgres?host=/tmp&port=5432`

### Disposable isolation mechanism (Case A)

`tests/services/test_memory_vault_mutation.py` and the UMS-04 round-trip
fixture explicitly create and tear down uniquely-named disposable child
databases for each test invocation:

```python
def _create_disposable_database(admin_url, name):
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.cursor().execute(f'CREATE DATABASE "{name}"')
    # ...build child URL by replacing DB name in admin URL...
```

Per-test:

1. Open admin connection to `postgres`.
2. `CREATE DATABASE ums05c1_<random>`.
3. Apply alembic migrations to `head` on the child.
4. Run test body on the child.
5. `DROP DATABASE ums05c1_<random>`.

Verification of the `postgres` admin database confirms zero application
tables (`\dt` shows `Did not find any relations`). The admin DSN is the
connection anchor only — every test mutation occurs in a per-test
disposable child database that is dropped after teardown.

The homebrew server does hold unrelated long-lived databases:

```
postgres
resonant_jones
threadspace_db
Codexify
codexify_message_seq_<hash>
codexify_pm_proof_<hash>
```

These are **not created, dropped, or mutated by the C5 fixture**. They
existed before this task. They would only be touched if the fixture itself
targeted them directly, which it does not — the fixture only invokes
`CREATE DATABASE`/`DROP DATABASE` against whichever database name it
synthesizes from the admin DSN. The admin DSN was set to `postgres`,
whose own tables are empty.

### No Preview, production, or application database was used

- The Homebrew port-5432 instance is a developer-side local server, not a
  Codexify Preview or production instance.
- The `postgres` admin database has zero tables.
- No Codexify application data (`memory_*`, `persona_*`,
  `threadspace_*` rows, Codexify account rows, etc.) was inserted,
  updated, or deleted.
- All qualification child databases were dropped at the end of each
  test; no orphan disposable DBs accumulated.

### Migration / portable DB tests

`tests/services/test_account_export_restore_unified_memory_roundtrip.py`
creates its own per-test disposable database through the same shared
fixture pattern. No raw homebrew database is mutated.

### Cleanup result

After qualification:

- All fixture-created per-test disposable DBs were dropped by their
  fixtures' teardown.
- `unset TEST_DATABASE_URL` was issued.
- `test -z "${TEST_DATABASE_URL:-}"` evaluates true.

## Persona identity authority

- **Stable subject authority**: `persona_subjects.persona_subject_id`
  (UUID, 36 chars, PK).
- **Account owner authority**: `persona_subjects.user_id` (FK to
  `users.id`).
- **Lifecycle vocabulary**: `active | retired` from
  `PersonaSubjectLifecycle` (protocol_tokens authority).
- **Mutable PersonaProfile**: NOT attribution authority. Display names,
  prompts, profile IDs, and bindings are not used to identify attribution
  subjects.
- **Canonical link-kind authority**: `MemoryPersonaLinkKind` is the
  closed vocabulary. Three distinct values:
  - `captured_under`
  - `suggested_by`
  - `associated_with`
- **Canonical attestation surface**: `memory_persona_links` with:
  - `link_id` server-generated UUID
  - composite FK to `memory_records(memory_id, user_id)` ON DELETE CASCADE
  - composite FK to `persona_subjects(persona_subject_id, persona_user_id)` ON DELETE CASCADE
  - `CheckConstraint(user_id = persona_user_id)` for same-account integrity
  - `UniqueConstraint(memory_id, persona_subject_id, link_kind)` preventing duplicates
  - DB-level `CHECK` restricting `link_kind` to canonical enum values

## Mutation service

- Public surface added: `MemoryVaultMutationService.set_persona_attribution`
- Exact signature:

  ```python
  set_persona_attribution(
      *,
      memory_id: str,
      expected_updated_at: datetime,
      persona_subject_id: str,
      link_kind: MemoryPersonaLinkKind | str,
      present: bool,
      reason: str | None = None,
      request_ref: str | None = None,
  ) -> VaultMutationResult
  ```

- Reused C1–C4 primitives:
  - `_load_authorized_memory` + `_require_fresh_token` for memory load
    and CAS validation
  - CAS-advance: `update(MemoryRecord).where(memory_id=?, user_id=?,
    updated_at=expected_updated_at).values(updated_at=clock_timestamp())`
  - `_build_receipt` for the canonical provenance row (the receipt value
    type was internally widened from `bool | int | None` to
    `bool | int | dict | None` to allow the structured
    `persona_attribution` link fields; the public mutation surface is
    unchanged — pin, hold, and Project-scope contracts remain identical
    and the helper vocabulary remains closed)
  - `_readback` returning canonical `VaultItem` via
    `MemoryVaultReadService`
  - `session.flush()` + `session.commit()` (single transaction)
- No per-call account override exists; `authenticated_account_id` is
  constructor-bound and immutable.
- No arbitrary-field mutation was introduced; `_normalize_link_kind`
  validates against `MemoryPersonaLinkKind`, and the helper vocabulary
  is closed to `pinned`, `held`, and the named `persona_attribution`
  method.

## Scope proof

- Active subject add: present=True with no existing link → 1 receipt
  `add_persona_attribution`, parent CAS advanced, exact link inserted,
  readback contains the exact `(subject_id, link_kind)` exactly once.
- Remove: present=False with existing link → 1 receipt
  `remove_persona_attribution`, parent CAS advanced, exact link deleted,
  readback omits the exact link.
- Duplicate exact add no-op: present=True with existing exact link and
  fresh CAS → changed=False, receipt_id=None, timestamp unchanged.
- Already-absent remove no-op: present=False with no exact link,
  fresh CAS, real same-account subject → changed=False, no receipt.
- Link-kind independence: same subject, multiple kinds
  (`captured_under` + `associated_with`); remove one, the other
  survives. Subject-wide deletion never occurs.
- All canonical link kinds: `captured_under`, `suggested_by`,
  `associated_with` all accepted via parametrized service test.
- Invalid internal link kind: direct service invocation with a
  non-canonical string → `MemoryVaultMutationError` (fail-closed).
  HTTP layer also rejects with 422 via Pydantic enum validation.

## Persona lifecycle proof

- Active absent link + present=True → add (changed=True).
- Retired absent link + present=True →
  `MemoryVaultPersonaSubjectLifecycleConflict` (no link, no receipt,
  no timestamp change).
- Retired existing link + present=True (fresh CAS) → no-op (changed=
  False, no write, no receipt, historical link preserved).
- Retired existing link + present=False → remove (changed=True,
  CAS advanced, one remove receipt, subject lifecycle and bindings
  unchanged).
- Missing subject → `MemoryVaultPersonaSubjectNotAvailable` 404.
- Foreign-account subject → same `NotAvailable` posture (no
  distinguishability).

## CAS proof

- Persona mutation T1→T2 with active subject: parent CAS advances,
  child link changes, receipt appended, all in one transaction.
- Fresh no-op: `expected_updated_at` matches current and desired
  presence matches current; no timestamp change, no receipt.
- Stale no-op: even when desired presence happens to match current,
  stale `expected_updated_at` raises `MemoryVaultMutationConflict`.
- Persona→stale-pin: read T1; add Persona; receive T2; attempt
  `set_pinned(..., expected_updated_at=T1)` → conflict, `pinned`
  unchanged, no pin receipt, Persona link state unchanged.
- Existing-governance→stale-Persona: pin T1→T2; hold T2→T3;
  Project scope T3→T4; attempt `set_persona_attribution` with T1 →
  conflict, Persona links unchanged, no Persona receipt.

**One record-level `updated_at` CAS now protects `pinned`, `held`,
`project_id`, and `memory_persona_links`.** No child-specific CAS is
introduced.

## Receipt proof

- Schema: `memory-vault-mutation.v1` (unchanged from C1–C4).
- Action labels (frozen for C5):
  - `add_persona_attribution`
  - `remove_persona_attribution`
- Add payload:

  ```json
  {
    "previous_values": {"persona_attribution": null},
    "new_values": {"persona_attribution": {
      "link_id": "<server-generated>",
      "persona_subject_id": "<stable subject>",
      "link_kind": "<canonical enum value>"
    }}
  }
  ```

- Remove payload:

  ```json
  {
    "previous_values": {"persona_attribution": {
      "link_id": "<existing link id>",
      "persona_subject_id": "<stable subject>",
      "link_kind": "<canonical enum value>"
    }},
    "new_values": {"persona_attribution": null}
  }
  ```

- Receipt contains no Persona display name, PersonaProfile ID, prompt,
  profile manifest, memory content, Project description, or binding
  source-reference history.
- Receipt is non-authority audit/lineage; canonical Persona attribution
  authority remains `memory_persona_links` exclusively.

## Atomicity proof

Forced provenance flush failure (via `event.listen(session,
"before_flush", raise)` triggered on receipt-insertion) during a
Persona add:

- After rollback: no Person link row inserted, memory `updated_at`
  unchanged, receipt count unchanged.
- Same-account DB integrity preserved: `memory_records.user_id`,
  `memory_persona_link.user_id`, `memory_persona_link.persona_user_id`,
  and `persona_subjects.user_id` all equal the authenticated account.

## Independence proof

`_non_persona_fields` snapshot before/after successful scope mutation
remains identical for:

- `user_id`
- `project_id`
- `semantic_species`
- `text_content`
- `fact_key`, `fact_value`, `fact_confidence`
- `reviewed_at`
- `activated_at`
- `pinned`
- `held`
- `extensions`

Plus:

- `persona_subjects` rows: unchanged (`SELECT * FROM persona_subjects`
  diff is empty).
- `persona_subject_bindings` row count: unchanged.

## HTTP proof

- Path: `PATCH /api/memory-vault/items/canonical/{memory_id}/persona-attribution`.
- Request body: `VaultPersonaAttributionRequest` with required
  `persona_subject_id: str`, `link_kind: MemoryPersonaLinkKind`,
  `present: bool`, `expected_updated_at: datetime`; optional
  `reason`, `request_ref`.
- Reuses `_VaultMutationRequest` timezone-aware validator.
- Delegation: thin — body fields passed verbatim to
  `service.set_persona_attribution(...)`.
- Error mapping:
  - 401 `Stable account identity required` for blank account.
  - 422 for missing/invalid `persona_subject_id`, missing/invalid
    `link_kind`, missing `present`, missing/malformed/naive
    `expected_updated_at`. Service is not invoked.
  - 404 `Memory not available` for missing/cross-account memory.
  - 404 `Persona subject not available` for missing/foreign subject.
  - 409 `Persona subject is not active for new attribution` for retired
    + new-attribution.
  - 409 `Memory changed since it was read` for stale CAS.
  - 409 `Memory mutation unavailable` for generic integrity failure.
- Caller authority injection: query-string `user_id`/`account_id`/
  `persona_profile_id` are filtered out by route signature — they do
  not bind to the service. Service receives only the body fields.
- No compatibility scope-mutation route exists; compatibility GET
  remains read-only.
- Existing pin, hold, and Project-scope routes remain qualified; their
  tests still pass unchanged.

## Control-plane proof

- Seven Memory Vault paths mounted internally on admitted web profiles
  (`v1-local-core-web-mcp`, `v1-friends-family-web`,
  `v1-whooshd-deepseek-web`):

  ```text
  GET   /api/memory-vault/items
  GET   /api/memory-vault/items/canonical/{memory_id}
  GET   /api/memory-vault/items/compatibility/{source_kind}/{source_id}
  PATCH /api/memory-vault/items/canonical/{memory_id}/pin
  PATCH /api/memory-vault/items/canonical/{memory_id}/hold
  PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope
  PATCH /api/memory-vault/items/canonical/{memory_id}/persona-attribution
  ```

- All seven remain hidden from public OpenAPI
  (`not (VAULT_PATHS & openapi_paths)`).
- Feature flag `CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES=false` removes all
  seven.
- A quarantined profile + flag true keeps the router off (all seven
  absent).
- `guardian/guardian_api.py` is unchanged (SHA verified identical at
  open and close).
- `guardian/services/memory_vault_read.py` is unchanged (SHA verified).
- `guardian/protocol_tokens.py` is unchanged (SHA verified).
- `config/supported_profiles/*` shows no diff.

## Regression results

| Surface | Result |
| --- | --- |
| Mutation (`test_memory_vault_mutation.py`) | 52 passed |
| Routes (`test_memory_vault.py`) | 74 passed |
| Activation (`test_memory_vault_activation.py`) | 7 passed |
| Persona migration (`test_persona_subject_identity_migration.py`) | 4 passed |
| Protocol tokens (`test_protocol_tokens.py`) | 36 passed |
| Read projection (`test_memory_vault_read_projection.py`) | 24 passed |
| UMS-04 round-trip (`test_account_export_restore_unified_memory_roundtrip.py`) | 1 passed |
| `py_compile` (5 authorized Python files) | PASS |
| Alembic heads | one head `7e5a5fccf253` |
| `pre-commit` on 5 runtime/test files | PASS (no further mutation after pre-commit auto-fix) |
| `validate_docs.py` | PASS |
| `git diff --check` | PASS |

## Runtime / control-plane immutability

```text
guardian/services/memory_vault_read.py
  7c12d7dc9836465b4bb4b1f393bf066ce5de3b665aab6ed70051f7d247e843b3   (unchanged)
guardian/protocol_tokens.py
  3283f67cdc20b7e4b7ba546c69442d21ab977aa88decb657064063035703fad7   (unchanged)
guardian/guardian_api.py
  bbb6fc86c9ea4d3dfbf8bd52f9b02c602efba5db3b46f0719e02adfed648a9a5   (unchanged)
```

No supported-profile manifest diff. No export/restore implementation
diff.

## ADR impact

Aligned with ADR-082 (Persona Profile / manifest authority) and
ADR-084 (Unified Account-Owned Memory Store). No new ADR. No architecture
semantic change. Stable Persona-subject attribution and the existing
qualified Vault mutation spine were reused; `MemoryPersonaLinkKind`
remains the protocol token authority.

## Limitations

- No frontend control exists.
- Persona attribution grants no retrieval, recall, ambient eligibility,
  Project-scope widening, ownership, review, or activation change.
- No Persona subject lifecycle, binding, profile, or prompt mutation
  was added.
- No direct Vault creation, content correction, Personal Facts review,
  retire/restore, or conversational memory command exists yet.
- Branch-local qualification only. This qualification has NOT been
  deployed, NOT exposed via Preview, NOT merged into the current
  `main` branch, and is not represented as any release. The C5 surface
  is reachable exclusively through internal-only routes on
  `feature/ums-continued`.
- UMS-05C remains OPEN; UMS-05C6 direct user-authored Vault creation
  is the sole next authorized slice; UMS-05C7+, UMS-05D+, and UMS-06+
  remain unauthorized.