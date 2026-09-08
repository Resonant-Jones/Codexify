# Persona private-preview migration rehearsal

Date: 2026-09-06
Result: **PASS — clone migration compatibility and data preservation proven.**

The live private-preview database was not upgraded. Live upgrade requires a
separate authorization and fresh external checkpoint. Persona deployment and
authenticated browser save/readback remain pending; no release claim advances.

## Source and migration graph

- Source: clean `feature/persona-studio` at
  `f247a046141271f034c935f9baf924aa99aa1f25`.
- Live reconciliation root: `/Volumes/Dev_SSD/Codexify-main`, resolved from
  the installed stack LaunchAgent. Secure env existence/readability was checked
  without reading or copying its contents.
- Source database discovered through Docker Compose project/service labels:
  `codexify_private_preview` / `db`.
- Live source container:
  `01d246fa2e1a31859c3e34f84138220ec10566966313932e51644e9bfa755936`.
- Canonical configuration: `backend/alembic.ini`, script directory
  `guardian/db/migrations`.
- Alembic graph resolution found exactly one head, with this ordered path:
  `b2c8d0e3f5a7 → c3d9e1f4a6b8 → d4e0f2a5b7c9`.
  The source is an ancestor; the path has no missing parent or unresolved
  parallel head. Both migration implementations were inspected; neither
  manually stamps or edits the migration ledger.

`c3d9e1f4a6b8` adds `persona_profiles.current_revision`, immutable
`persona_profile_revisions`, and server-owned `persona_profile_bindings`.
It constructs revision 1 from existing five-field profiles and binds legacy
profiles only where exactly one account exists. `d4e0f2a5b7c9` adds
`chat_threads.active_profile_revision` and pins only valid, account-owned,
non-overridden selections. Both add constraints. Neither requires changing
any original column value.

## Snapshot and isolation

One custom-format `pg_dump --no-owner --no-acl` captured the live database
without stopping application traffic. The dump provides the snapshot boundary;
the control clone, not a later live read, supplies the preservation baseline.

- Dump size: **3,333,556 bytes**.
- Dump SHA-256:
  `1224063733dce395e5b208fa3d9861247c589e172ba053bf012e57460de83326`.
- External artifact directory:
  `/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/codexify-persona-migration-rehearsal.08qzdrlb`.
- Directory mode `0700`; dump, manifests, logs, receipt, and retained rehearsal
  driver mode `0600`, verified after execution. No row contents or credentials
  were printed or committed.

The same dump restored with `pg_restore --exit-on-error --no-owner --no-acl`
into two PostgreSQL 15 containers, each with a separate proof-only volume.
Both restores exited successfully with empty stderr and initially reported
exactly `b2c8d0e3f5a7`.

| Role | Container ID |
| --- | --- |
| control | `5fc9376085597a4faca3b589f3c58cf0215242c685ac704eda9be6b88cf5780a` |
| candidate | `5558734bc4a09153aeeb0fd3c7cc7fd326b88111b19f36847023c1ee4924b809` |

They were created on the proof-only `--internal` network
`persona-rehearsal-08qzdrlb`, with inert proof credentials, no published host
ports, and no live application network or source-volume attachment. Their
volumes were `persona-rehearsal-08qzdrlb-control-data` and
`persona-rehearsal-08qzdrlb-candidate-data`.

## Migrator and preservation result

Built from the clean source with:

```bash
docker build -f backend/Dockerfile --target runtime \
  -t codexify-persona-migration-proof:f247a046 .
```

Proof image identity:
`sha256:e0d92e9c5ec7917c78a8fe3b8b5eb27313ef244afd466614c3a823e2c1690df7`.

The image ran with `--entrypoint python` and
`/app/backend/scripts/docker/run_migrator.py`. Every supplied database DSN
targeted the candidate on the isolated network. No live env file, source
volume, or live connection was supplied. The canonical runner, including its
normal seed-defaults step, exited **0** and reported `Done`. No workaround,
bootstrap, manual repair, or stamp was used. Final candidate revision:
**`d4e0f2a5b7c9`**.

For every public base table except `alembic_version`, the control manifest
records columns in ordinal order, row count, and SHA-256 of all rows projected
through those original columns. PostgreSQL `row_to_json` preserves the ordered
projection; UTF-8 byte sorting plus newline framing gives deterministic order
while retaining duplicate rows. The identical projection is used after
migration, excluding newly added columns from the comparison.

- **111 pre-existing tables; 5,595 rows** compared.
- Candidate before upgrade matched the control manifest exactly.
- After upgrade: **zero row-count differences; zero original-column digest
  differences; zero missing original tables/columns**.
- Aggregate original-column manifest SHA-256:
  `ac6329e9555557f279fcdcb1d04540c0e05cc2ba95883c4d6b95fc9c016a62b8`.
- Exact schema additions: `persona_profile_bindings`,
  `persona_profile_revisions`, `persona_profiles.current_revision`, and
  `chat_threads.active_profile_revision`; no unexpected tables/columns added.
- PostgreSQL restore validated existing constraints and Alembic created the
  target constraints normally. Target public unvalidated-constraint count: **0**.
- Snapshot contained three legacy profiles and six accounts. The inspected
  migration's single-account ownership assignment must not be generalized into
  automatic ownership recovery for this multi-account snapshot. This rehearsal
  proves preservation and schema compatibility, not profile visibility for a
  particular account or browser behavior.

## Live preservation and disposal

The source revision remained exactly **`b2c8d0e3f5a7`** after rehearsal.
The source container ID was unchanged. `/health` and `/health/chat` were healthy
before and after. Both stack and tunnel LaunchAgents remained loaded; neither
was suspended or reconfigured. This task launched no live migration container
and made no live DDL/data write. Ordinary application traffic and existing
reconciliation were not stopped.

Both exact proof containers, both proof volumes, and the proof network were
removed; subsequent inspections confirmed all five resources absent. The
external dump and proof artifacts remain retained. The proof image remains
available under its separate tag; no live image tag was replaced.

## Validation, limitations, and next prerequisite

`python3 scripts/validate_docs.py` and `git diff --check` passed. Only this
receipt and the authorized current-state document changed. ADR-082 authored
manifest/server binding separation, account authority, immutable revisions,
and non-executing broad settings remain unchanged. No migrations, scripts,
Compose files, runtime code, or supported profiles were edited.

Warnings: initial Docker build metadata access required sandbox escalation;
the authorized build then succeeded. Pi catalog listed DeepSeek V4 Pro, chosen
for bounded read-only migration review, but exact-pair preflight rejected it
as unavailable. No inference or delegation occurred; no Pi repair was attempted.
No restore or migration failure occurred. Detailed logs remain restricted.

Next prerequisite: explicitly authorize the live
`b2c8d0e3f5a7 → d4e0f2a5b7c9` upgrade with a fresh external checkpoint and
post-migration preservation/readback checks. This clone proof is not that
authorization and does not qualify deployed Persona lineage or browser saves.
