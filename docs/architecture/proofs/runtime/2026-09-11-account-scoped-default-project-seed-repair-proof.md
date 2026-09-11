# Account-scoped default Project seed repair proof

Date: 2026-09-11. Execution lane: architecture-impact / `EXECUTE`.

Result: PASS.

Reason: `account_scoped_default_project_seed_repaired_and_rehearsal_qualified`.

## Scope and authority

This task repaired the mandatory post-Alembic seed phase without changing the
migrator ordering, Project schema, migration history, application startup, or
release truth. The prior fresh restored-copy traversal reached Alembic head and
then failed because `backend/scripts/seed_defaults.py` resolved one global
Project by name and attempted `INSERT INTO projects (name, description)`. At
the current schema that obsolete path raised PostgreSQL `NotNullViolation` on
`projects.user_id`.

ADR-005 supplies the account boundary, ADR-076 defines account-scoped built-in
Project roles, ADR-081 makes `projects.user_id` sole Project ownership
authority, and ADR-085 forbids recreating the retired shared legacy Project.
The repair implements those accepted decisions; it does not redefine Project
authority, so no new ADR is required.

Authorized repository paths were limited to the seed script, its focused new
test module, and this proof. `backend/scripts/docker/run_migrator.py`, all
migrations, Project helpers/models, Compose, configuration, ADRs,
`docs/architecture/00-current-state.md`, frontend code, and existing proofs
were not edited.

## Repository and operational boundary

- Host: `VaultNode.local`
- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Branch: local `main`
- Start HEAD: `fe6c2b1e7761230245d894f9ce04d7172ef6c864`
- Fetched `origin/main`: `cb551de1866715ef421026203ffe2a87cec8aaca`
- Initial topology: local `main` ahead 13, behind 4
- Initial staged binary-patch SHA-256:
  `4e96d8c7155e327f03f15d311ddfbf03c32dc2d86129e184b4f7a6bb29b7560e`

The two pre-existing staged Dev Log deletions for 2026-09-10 and 2026-09-11
were treated as unrelated user state. They were not modified, restored,
unstaged, or included in this task.

Provider authority, live Private Preview mutation/Alembic authority, and
application-startup authority were all `NONE`. Provider-backed invocations,
live migration attempts, task-agent startup attempts, and Chroma mutations were
zero.

## Repaired seed contract

The dependency-light seeder now performs this deterministic transaction:

1. Enumerate `users.id` in fixed bytewise order, excluding the historical
   compatibility identity `local`; an empty account set commits no Project.
2. Lock each canonical account in that same order.
3. Resolve an existing built-in only by
   `(projects.user_id, projects.system_role='general')`. Retain its Project ID,
   owner, name, and description exactly.
4. If no structural General exists, inspect only that account's unroled exact
   aliases `General` and `Loose Threads`. Promote a sole match in place by
   setting the canonical presentation name and role. This preserves the same
   Project ID, description, owner, and every reference; it performs no Project
   reassignment or deletion.
5. If multiple same-account structural Generals or legacy candidates exist,
   fail closed with the existing `account_general_project_duplicate`
   vocabulary and roll back the entire seed transaction.
6. Otherwise insert exactly one row with canonical `user_id`,
   `system_role='general'`, name `General`, and the canonical default
   description. No insert path omits ownership or role.

The historical compatibility deduper now refuses modern schemas containing
`projects.user_id`; it cannot select a global keep Project, create an ownerless
Project, or move a modern Project reference. No cross-account alias
reassignment is authorized or possible in the repaired path.

## Focused validation

All ownership-sensitive tests used disposable PostgreSQL 15 databases:

- `tests/test_seed_defaults_account_scope.py`: 10 passed. This covers zero
  users, one account, multiple accounts, `local` exclusion, same-name account
  isolation, repeat idempotence, in-place account-scoped alias promotion,
  reference stability, every creation/promotion owner path, existing role
  uniqueness, and ambiguous-state rollback.
- Existing default-Project, account-Project, lifecycle, ownership, and lifecycle
  route regressions: 31 passed.
- Existing account-scoped Project-name migration regressions: 2 passed.
- Ruff checks and Python compilation for the changed Python files: PASS.
- Focused and repository-wide diff whitespace checks: PASS.
- `python3 scripts/validate_docs.py`: PASS.
- `.venv/bin/python scripts/validate_docs.py`: PASS.

These tests prove the bounded seed contract; they are not live-runtime or
release-readiness proof.

## Fresh retained-dump rehearsal

The immutable source was
`/Volumes/Dev_SSD/Codexify-preservation/persona-retirement-20260911T145217Z/private-preview-post-persona-retirement.dump`:

- SHA-256: `0401d5334b34a3b281e1a999732cce6a1ad9ddd12de5c18657d5b1528b2d805d`
- Size: 3,338,690 bytes
- Restore: `pg_restore --exit-on-error --no-owner --no-acl`, PASS

It was restored into the new container
`codexify-seed-rehearsal-20260911t185447z` and new volume
`codexify_seed_rehearsal_20260911t185447z`. The database had `--network none`,
no published ports, separate storage, and no remote data path. Bounded command
logs are retained mode 0600 under
`/Volumes/Dev_SSD/Codexify-preservation/account-scoped-seed-repair-20260911T185447Z`.

The restored precondition was exact:

- Alembic revision: `d4e0f2a5b7c9`
- Users / Projects / threads / messages: 6 / 6 / 72 / 805
- Project `1`: absent
- Persona Profiles / revisions / bindings: 0 / 0 / 0
- Repaired Project-1 thread count: 8
- Affected message count: 20
- Repaired-thread full-row SHA-256:
  `be4ab5affdb49361d2109587493a3ad64804860a50cca731b2e9badcc4ec5c03`
- Affected-message full-row SHA-256:
  `d201acd44888dfd48905ce6a9b477eee764332bac39bda4ef745198121d8c0bd`

The exact repaired mapping was thread `1 -> 8`; threads `3, 4, 5, 71, 72 ->
6`; thread `69 -> 8`; and thread `70 -> 7`. Each thread owner equaled its
replacement Project owner.

## Exact-source migrator qualification

The runtime target in `backend/Dockerfile` was built from the task working tree
with no source bind mount and tagged
`codexify-backend-runtime:account-scoped-seed-repair-20260911`.

- Image ID: `sha256:a45b2fe1959f87574780512eece31274369a34315bc99e97c959befbce71ed12`
- Alembic head count: 1
- Alembic head: `7e5a5fccf253`

No application service was started. Both rehearsal runs used the image's exact
canonical migrator entrypoint, which executed `alembic upgrade heads` and only
then `seed_defaults.py`.

## First complete migrator result

The first full migrator exited 0. Alembic advanced from `d4e0f2a5b7c9` to
exactly `7e5a5fccf253`; the seed phase then exited 0 with five canonical
non-`local` accounts, three existing structural Generals retained, zero alias
promotions, and two owned Generals created. The prior `NotNullViolation` did
not recur.

Post-seed Project state, expressed only through Project IDs and counts:

- Projects: 8 total; Project `1`: absent
- Canonical non-`local` accounts: 5; structural General rows: 5
- Existing structural General IDs retained: 6, 7, 8
- Newly created structural General IDs: 9, 10
- General IDs 6, 7, and 8 retained their historical repair presentation names
  as required by the existing-General no-op rule
- General IDs 9 and 10 use the canonical presentation name `General`
- Non-General Projects: 3
- Ownerless Projects: 0
- `local` structural Generals: 0
- General rows with a missing account: 0
- Canonical accounts missing a General: 0
- Accounts with more than one General: 0
- Cross-account thread/Project owner mismatches: 0

The head traversal performed one expected pre-seed ownership reconciliation:
legacy-local Project ID 3 moved to the single canonical owner proven by its
threads under migration `d4e8f1a2b6c9`. Pre-existing Project IDs 2, 4, 6, 7,
and 8 retained their owner digests; IDs 9 and 10 were new account-owned seed
rows. The seeder contains no owner-update statement and no reference-update or
Project-delete statement. Unexpected pre-existing Project owner mutations: 0;
cross-account Project reassignments: 0.

## Repair-boundary integrity

After the first migrator and after the second migrator:

- Threads / messages: 72 / 805
- The exact eight repaired thread mappings above: unchanged
- Repaired-thread SHA-256: unchanged at
  `be4ab5affdb49361d2109587493a3ad64804860a50cca731b2e9badcc4ec5c03`
- The exact 20 affected messages: unchanged
- Affected-message SHA-256: unchanged at
  `d201acd44888dfd48905ce6a9b477eee764332bac39bda4ef745198121d8c0bd`
- Persona Profiles / revisions / bindings: 0 / 0 / 0
- Persona Subjects / bindings attributable to retired profiles: 0 / 0
- Current Project foreign-key constraints checked: 17
- Project foreign-key orphans: 0

This proves the Project-1 and Persona-retirement boundaries survived the full
canonical migrator. It does not broaden the original retirement authority.

## Full migrator idempotence

The exact same image ran the complete migrator a second time against the
already-migrated rehearsal database and exited 0. Alembic remained exactly at
`7e5a5fccf253`. The second seed reported five existing Generals, zero
promotions, and zero creations.

The complete ordered Project-row snapshot was identical before and after the
second run: 8 rows with SHA-256
`7062bc0c16549d0983d792359d371ec8ccd998fdee1753a0fc30b44fd416a230`.
Therefore second-run Project inserts, deletes, reassignments, and owner changes
were each zero. `SEED_DEFAULTS_ACCOUNT_SCOPED_IDEMPOTENCE=PASS` for this exact
repaired rehearsal state only.

## Live safety and next boundary

Read-only checks immediately before and after the isolated rehearsal showed the
live Private Preview PostgreSQL database still at `d4e0f2a5b7c9`, with 6
Projects, Project `1` absent, 72 threads, 805 messages, and zero Persona
Profiles/revisions/bindings. Backend, frontend, origin, and worker containers
remained stopped or merely `Created`; the Private Preview launch agent remained
absent. The task started no application or live migrator. PostgreSQL remained
available, while Private Preview application writers remained quiesced.

Activity counters:

- Live migration attempts: 0
- Provider-backed invocations: 0
- Task-agent startup attempts: 0
- Chroma mutations: 0
- Pushes / merges: 0 / 0

This restored-copy evidence qualifies the repaired complete migrator but does
not authorize or prove live migration recovery, service startup, or a release
claim. The next recommended task is **Resume live canonical Alembic with
account-scoped seed repair**, architecture-impact lane, with a separate live
integrity and idempotence proof. Work stops at that boundary here.
