# Round-Trip-Stable Governed-Schema Equivalence Proof

**Date:** 2026-08-28

**Contract:** `governed-schema-equivalence/v1`

**Task main:** `66938525aa2fc54f8bc5f6185dfc9311452a5afa`

## Final classification

`ROUND-TRIP-STABLE GOVERNED-SCHEMA CONTRACT PASS — ADR-076 and governed-schema-equivalence/v1 define PostgreSQL round-trip canonicalization as the cross-restoration proof boundary; equivalent 9c66e490a42b schemas converge to one stable signature while real CHECK and non-CHECK schema changes remain detectable; the post-DLG implementation requalification is recorded below`

## Current-main and prerequisite identity

The implementation ran in the isolated worktree
`/private/tmp/codexify-governed-schema-equivalence-contract` on branch
`codex/define-governed-schema-equivalence-v1`.

At the start of the task, the source checkout was freshly fetched and clean at
`main...origin/main`, with both refs at `66938525aa2fc54f8bc5f6185dfc9311452a5afa`.
No governed-schema-equivalence seam had advanced on canonical main.  The
current-main drift was isolated and reconciled before implementation by:

- drift reconciliation proof: `8bec7714db9fc3de25216224eef5fc15fb85838b`
  (`Reconcile schema equivalence main drift`), with parent
  `66938525aa2fc54f8bc5f6185dfc9311452a5afa`;
- historical CHECK round-trip classification proof: commit
  `c4dc8e45262ab33a934d7daa0f2fd0ae110825fe`;
- blocked post-hoc adoption proof: commit
  `4dd158b8f0295a76accaf494daca9ab99fa38ff5`;
- qualifying-database migration provenance proof: commit
  `1d9bf6f6db1805ed3c3b2e9252e4c4d8976d4716`;
- accepted historical R2 convergence proof: commit
  `74098c156569fc7acf7e10308404b8a0dc99a150`;
- qualifying Google Drive migration proof: commit
  `3338536afa20bd99625b646ddfcd2ad22719163f`.

Those historical receipts and proofs were not edited.  Their interpretation is
extended only by this new evidence contract and ADR.

ADR collision checking found no existing ADR-076.  The selected ADR is
`docs/architecture/adr/076-round-trip-stable-governed-schema-equivalence.md`,
with status `Accepted` after authorized DLG preflight passed.  Exactly one new
ADR-index entry was added.

The initial candidate DLG run recorded the blocker
`content_hash_mismatch` for `docs/architecture/adr/adr-index.md`.  The
reconciliation task explicitly authorized repair of that one canonical node;
the historical blocker is retained here as sequence evidence, not as the final
result.

## Contract decision

ADR-076 establishes PostgreSQL-major-specific canonicalization as the
cross-restoration proof boundary.  The reusable implementation is
`scripts/governed_schema_equivalence.py` and exposes these library surfaces:

- `collect_governed_descriptors`;
- `normalize_descriptors`;
- `build_snapshot`, `snapshot_connection`, and `snapshot_from_dict`;
- `compare_snapshots` and `descriptor_diff`; and
- `canonicalize_database`.

The CLI exposes `inspect`, `snapshot`, `canonicalize`, and `compare`.

The exact governed relations are:

1. `github_watchdog_delivery_receipts`
2. `github_watchdog_review_attempts`
3. `github_watchdog_review_input_snapshots`
4. `github_watchdog_review_results`
5. `github_watchdog_review_dispatches`
6. `notion_connection_credentials`

The exact descriptor sections are `relations`, `columns`, `constraints`, and
`indexes`.  Relation descriptors contain `schema` and `name`.  Column
descriptors contain `schema`, `relation`, `ordinal`, `name`, `type`,
`not_null`, `default`, `identity`, `generated`, and `collation`.  Constraint
descriptors contain `schema`, `relation`, `name`, `type`, `deferrable`,
`initially_deferred`, `on_delete`, `on_update`, `definition`, `local_columns`,
`referenced_relation`, and `referenced_columns`.  Index descriptors contain
`schema`, `relation`, `name`, `unique`, `primary`, `definition`, and
`predicate`.

Collation identity is schema-qualified as `namespace.collation`, so equal
collation names in different namespaces cannot alias in the normalized
descriptor.

Catalog OIDs are used only for PostgreSQL catalog joins and are never emitted.
No timestamps, DSNs, database/container names, secrets, row data, or provider
credentials are serialized.  No custom CHECK normalizer exists.  PostgreSQL's
rendered constraint descriptor supplies CHECK meaning; internal parse-tree
text is diagnostic-only and does not enter the v1 digest.

The snapshot envelope binds `governed-schema-equivalence/v1`, PostgreSQL major
15, the separately verified source Alembic revision `9c66e490a42b`, and the
normalized descriptors.  Its SHA-256 is over UTF-8 JSON with sorted keys,
compact separators, one terminal newline, and no digest field.  Comparison
requires contract version, major, revision, digest, and exact normalized
descriptor equality.  Digest equality alone is insufficient.

## Historical disposable PostgreSQL proof

This section is the original live receipt and remains bound to the
implementation state recorded by its historical validation counts and digest.
The current implementation bytes are requalified in the appendix below.

The live proof used only the disposable container
`codexify-gse-proof-20260828`, loopback access, and PostgreSQL image
`postgres:15` (image digest
`sha256:3b0d656f5fff31c7d8a64f500a703dcf3f35e98ce78f602831a73059a5e6a012`).
The server reported PostgreSQL `15.18` / `server_version_num=150018`.  The
database directory and socket directory were tmpfs mounts; no Docker-managed
volume, shared source mount, or proof network was created.  All proof database
names used the disposable `codexify_gse_` prefix except the disposable source
fixture.

The fresh source was migrated first to predecessor
`6e9f0a1b2c3` with:

```text
python -m alembic -c backend/alembic.ini upgrade 6e9f0a1b2c3
```

The exact recovered synthetic predecessor fixture was applied only inside the
disposable source.  Its SQL SHA-256 was
`4b0ea2bd462bffee0a033216c95f538f2792bbf2a025f141669ddb76b24996db`.
It contained no DDL and did not write `alembic_version`.  The source then
advanced to final revision `9c66e490a42b` with the same repository Alembic
command shape.  The source ended with exactly one Alembic revision row:
`{9c66e490a42b}`.

For each canonicalization, the tool performed read-only source/target catalog
checks, exactly one controlled dump class:

```text
pg_dump --schema-only --no-owner --no-privileges --dbname=<source>
```

and exactly one transactional restore class:

```text
psql --no-psqlrc --set=ON_ERROR_STOP=1 --single-transaction --dbname=<target>
```

The target name was explicitly supplied, checked against `current_database()`,
and required the disposable prefix.  No `--clean`, `--create`, Alembic command,
version stamp, manual DDL, source write, or live qualifying-database access was
used by the canonicalization tool.

## Historical R2 reproduction

The historical raw comparator was reproduced without dropping fields.  The
fresh disposable source produced the exact historical raw R2 digest:

`1bc62c1b7308c4989ce41332faa14809a889af747c809d94454cd659d8ff4e28`

The first raw schema-only restore produced the exact blocked/restored digest:

`abcc9ce04c6e03217af2f806ba8b79a3be9e90945d7688c53612cac42b76ad44`

The raw digests therefore remained unequal.  The exact twelve CHECK-only
descriptor identities were:

1. `ck_github_watchdog_review_attempts_escalation_mode`
2. `ck_github_watchdog_review_attempts_policy_reason_code`
3. `ck_github_watchdog_review_attempts_policy_resolution_state`
4. `ck_github_watchdog_review_attempts_state`
5. `ck_github_watchdog_review_dispatches_state`
6. `ck_github_watchdog_review_dispatches_terminal_error_code`
7. `ck_github_watchdog_review_dispatches_terminal_shape`
8. `ck_github_watchdog_review_input_snapshots_block_error_code`
9. `ck_github_watchdog_review_input_snapshots_state`
10. `ck_github_watchdog_review_results_state`
11. `ck_github_watchdog_review_results_terminal_error_code`
12. `ck_notion_connection_credentials_validation_status`

Columns, indexes, foreign keys, primary keys, unique constraints, and the
remaining governed surface matched in the raw reproduction.  Four additional
parse-tree differences were retained as diagnostic-only evidence:

- `ck_github_watchdog_review_attempts_model_selection_source`;
- `ck_github_watchdog_review_attempts_operation`;
- `ck_github_watchdog_review_input_snapshots_terminal_shape`; and
- `ck_github_watchdog_review_results_terminal_shape`.

## v1 canonicalization result

The six governed relations yielded 112 columns, 36 constraints, and 18
indexes.  The first canonicalization of the fresh final source into disposable
target 1 produced:

`ROUNDTRIP_STABLE_TARGET_DIGEST=3602352f35eea4aaec2da7728ae0a6c9d68ad6ec59572b5863beae56a3f0423f`

The second canonicalization of target 1 into independently disposable target 2
carried forward the previously verified revision `9c66e490a42b` because a
schema-only dump does not preserve Alembic table data.  It produced the same
digest:

`3602352f35eea4aaec2da7728ae0a6c9d68ad6ec59572b5863beae56a3f0423f`

The first/second digest equality and exact descriptor equality both passed.
The v1 fresh/restored comparison therefore passed even though the historical
raw fresh/restored digests remained unequal and the exact twelve raw CHECK
differences remained present in that historical evidence.

## Mutation detection

The baseline source was canonicalized into a disposable target and reproduced
the stable digest
`3602352f35eea4aaec2da7728ae0a6c9d68ad6ec59572b5863beae56a3f0423f`.

For the CHECK negative case, exactly one governed CHECK constraint,
`ck_github_watchdog_review_attempts_state`, was recreated with one new accepted
literal (`semantic_mutation`).  Canonicalization produced digest
`17c2bb050c8b776db7c11a876d4f9657f6f3b3def23126385c9196a7029b5996`.
Comparison failed closed with both a governed digest mismatch and descriptor
mismatch; the bounded diff identified that CHECK constraint and the added
`semantic_mutation` literal.

For the non-CHECK negative case, exactly one governed index,
`gse_semantic_index_mutation`, was added on
`github_watchdog_review_attempts(head_sha)`.  Canonicalization produced digest
`a146d8ca52aa354c4f3911e858fb6f60ec615df23b6d544c90d07a3659590ffd`.
Comparison failed closed with both a governed digest mismatch and descriptor
mismatch; the bounded diff identified the added index.

## Failure and safety behavior

Focused unit coverage proves PostgreSQL-major mismatch raises
`POSTGRES_MAJOR_MISMATCH`, wrong Alembic identity raises
`ALEMBIC_REVISION_MISMATCH`, missing governed relations fail closed, disposable
target identity is enforced, command failures are typed, and tampered snapshot
envelopes are rejected.  A schema-only source is accepted only with an
explicitly carried, previously verified expected revision; an observed wrong
revision always fails.

The current implementation also keeps source metadata and catalog reads inside
an exported repeatable-read, read-only PostgreSQL snapshot for `pg_dump`,
rejects user-owned objects in the disposable target before dumping (including
user-defined collations), and qualifies column collations by namespace.

The source remained non-mutated: the raw source digest was reproduced again
after canonicalization, the source still had exactly one `9c66e490a42b` row,
and the fixture sentinel count remained one.  The unit fake-connection tests
also verify catalog reads are SELECT-only.  No live Google qualifying database,
OAuth flow, Google API, Connection action, Command Bus invocation, migration
adoption, or release promotion occurred.

## Validation

- New focused contract tests: `15 passed`.
- Migration owner/D6 regression suite: `20 passed`.
- Alembic revision uniqueness test: `1 passed`.
- Black check for the new tool and tests: passed.
- CLI smoke: `inspect` reported major 15 and revision `9c66e490a42b`; `snapshot`
  reported the stable digest; `compare` returned `equivalent: true` for the
  independently canonicalized targets.
- `scripts/validate_docs.py`: passed.
- `make docs PYTHON=python3`: passed.  Its diagram-freshness subcheck emitted
  the known Git-LFS permission warning while reading the worktree diff, then
  passed without source-drift findings.
- Initial candidate DLG validator: blocked with
  `content_hash_mismatch` for `docs/architecture/adr/adr-index.md`; its exact
  message was `Canonical source bytes do not match node content_hash.`
- Authorized DLG preflight: passed with zero errors, 10/10 source hashes, and
  13/13 target resolutions.  It also emitted six existing
  `broken_local_markdown_link` warnings for `docs/architecture/README.md`;
  those warnings were not changed in this task.
- Preflight DLG Phase 3 test: `38 passed`.
- Final source/DLG commit lineage, post-commit DLG validation, and final
  tracked-scope checks are recorded in the current implementation
  requalification below.

## Review requalification after post-DLG implementation changes

The comparator implementation and its focused tests changed after
`DLG_COMMIT`, so the historical unchanged-bytes statement and historical
stable digest are not used as current-head proof.  Implementation commit
`924d6a4dd8c94364e5c33885f8f745e693d90198` contains the review hardening and
is requalified here.

The fresh current-head runtime probe used only the tmpfs-backed disposable
container `codexify-gse-requal-20260828`, PostgreSQL image
`postgres:15@sha256:3b0d656f5fff31c7d8a64f500a703dcf3f35e98ce78f602831a73059a5e6a012`,
and loopback port `55438`.  The source reported PostgreSQL `15.18`,
`server_version_num=150018`, exactly one Alembic revision row
`9c66e490a42b`, and all six governed relations.  The source was migrated only
inside this disposable container; no shared or qualifying database was used.

The current `canonicalize_database` implementation exported a repeatable-read
read-only source snapshot and ran the schema-only dump with that snapshot.  A
first source-to-target run and a second independently disposable target run
both produced:

`2fe066b5f541fd9d13f941dda5d7a6ae0ffd429a7c47508253fa2bc3249baa1a`

The current snapshot comparison returned `equivalent: true`, an empty reason
list, and zero descriptor differences.  A separate target containing only a
user-defined `public.gse_custom_collation` was rejected with
`DISPOSABLE_TARGET_REQUIRED` before either dump or restore command ran.  The
disposable container was removed after the probe.

Current repository requalification also passed:

- `tests/migration/test_governed_schema_equivalence.py`: `29 passed`.
- DLG Phase 3, Alembic uniqueness, D6 compatibility, and governed-schema
  contract tests: passed together.
- `scripts/knowledge_graph/validate_and_generate_dlg.py validate` at
  repository revision `924d6a4dd8c94364e5c33885f8f745e693d90198`: passed with
  zero errors, 10/10 source-hash matches, and 13/13 target resolutions; the
  six existing README broken-link warnings remain unchanged.
- `scripts/validate_docs.py` and `make docs PYTHON=/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`:
  passed.
- Source-to-DLG ancestry, the exact six-file publication boundary, migration
  source immutability, and PR-scoped `git diff --check`: passed.

## Disposition

The cross-restoration schema-proof defect and the reviewed hardening findings
are repaired at the contract level.  The GitHub PR still requires its own
required-check and review gates; this receipt does not waive either gate.
Google Drive adoption remains a separate task and must not begin OAuth until
database adoption passes.

## Canonical publication qualification

- `SOURCE_COMMIT`: `abbdf5b03eec31b78edb43e62c713c892cc296fc`.
- `DLG_COMMIT`: `3f72792a1118722a7883154d52cf5b3a9e4628e3`.
- `SOURCE_COMMIT` is the exact direct parent of `DLG_COMMIT`.
- Candidate base: `66938525aa2fc54f8bc5f6185dfc9311452a5afa`.
- `PUBLICATION_MAIN`: `5b5df6fe36c68d1dee28b2546778d9a891800c46`.
- Main drift classification: unrelated movement only; the observed post-candidate
  main movement touched no governed-schema-equivalence, DLG, migration, ADR, or
  Architecture Contracts seam.
- The exact six-file publication boundary is:
  `docs/architecture/adr/076-round-trip-stable-governed-schema-equivalence.md`,
  `docs/architecture/adr/adr-index.md`,
  `docs/architecture/proofs/2026-08-28-round-trip-stable-governed-schema-equivalence-proof.md`,
  `docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json`,
  `scripts/governed_schema_equivalence.py`, and
  `tests/migration/test_governed_schema_equivalence.py`.
- Historical stable `governed-schema-equivalence/v1` digest:
  `3602352f35eea4aaec2da7728ae0a6c9d68ad6ec59572b5863beae56a3f0423f`.
- Final ADR-index source hash:
  `9844ad3ad91310ea4b65311f576eae78a616f4b8d48b13420e7daf60501d88e3`.
- The ADR-index DLG node `freshness.verified_commit` is
  `abbdf5b03eec31b78edb43e62c713c892cc296fc`.
- The comparator implementation and tests were changed after `DLG_COMMIT` by
  the review hardening commit above.  The ADR-076 source, ADR index source,
  and ADR-index DLG node remain the governed source-to-DLG chain; the current
  implementation is qualified by the requalification section above.
- Publication must preserve `SOURCE_COMMIT` → `DLG_COMMIT` ancestry through a
  history-preserving merge commit on canonical `main`.
- Squash and rebase publication are prohibited.
- No release-support or current-state change is included.
- Google Drive remains `Qualification Pending`; no live database, OAuth, Google
  API, Connection, Command Bus, or migration-adoption action is included.
