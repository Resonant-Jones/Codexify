# Private Preview schema advance and read-state requalification

Date: 2026-11-06

Serving revision: `dece0182163970b7d5de1b849306b52ac56030b7` (published `origin/main`, the merge
commit that landed PR #1007). Serving source root:
`/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106`, a clean detached
worktree of that revision, named by the Private Preview `serving-source` pin.

Live database before: revision `3a91d7c4e8b2`, 138 tables.
Live database after: revision `a7d4c9e2f1b3`, 140 tables, every pre-existing row preserved.

Release posture remains `HOLD`. This receipt records one live surface — the Private Preview
database and the recipient-local read-state behaviour deployed on it. It does not qualify the
product.

## What this receipt establishes

The live Private Preview database was advanced from `3a91d7c4e8b2` to the repository's single
migration head `a7d4c9e2f1b3`, the serving revision was moved onto the merged mainline, and the
twenty recipient-local read-state checks recorded by the 2026-10-29 receipts were **re-run against
the running service** at that revision. All twenty passed.

Three things had to be true before the migration could be applied at all, and each is proven below
rather than assumed: the backend image had to carry the reviewed migration source, a verified
recovery path had to exist, and the migrator's own coherence gate had to be satisfied by the
source the Preview actually serves.

## The seven revisions that were applied

The live database sat at `3a91d7c4e8b2` with a sibling branch unapplied. The migrator applied
seven revisions, in the order Alembic resolved them:

| # | Revision | Kind | What it carries |
| --- | --- | --- | --- |
| 1 | `b7e2c4a1d903` | schema | Campaign Continuation Authority provenance discriminator (two columns, bounded backfill, two check constraints) |
| 2 | `e42c7d0b9135` | schema | Durable coding-worker ownership on accepted runs (two nullable columns, paired-ownership check) |
| 3 | `d86f2a4b1c90` | schema | Claim-scoped heartbeat on accepted coding runs (one nullable column, ownership check) |
| 4 | `c8e42a91d307` | graph only | Merge of the guardian coding-claim and main heads |
| 5 | `a3115f64dda8` | graph only | Merge of the guardian coding-claim and campaign-continuation heads |
| 6 | `d91e4fa6702b` | schema | Observe-only, account-owned inference attempt metering (`inference_usage_events`) |
| 7 | `a7d4c9e2f1b3` | schema | `music_projects` table |

Both merge revisions are graph-only. Every schema-carrying revision is additive: new columns with
nullable or defaulted values, new tables, and check constraints. No revision rewrites, drops, or
truncates an existing row, and the one bounded backfill
(`b7e2c4a1d903`) touches only the two columns it adds. The five schema-carrying revisions and the
two graph-only mergepoints are exactly the set the release truth named as unapplied.

Observed schema objects after the migration:

```text
campaign_continuation_authorities.approval_provenance     NOT NULL
campaign_continuation_authorities.revocation_provenance   NULL
agent_runs.coding_worker_instance_id
agent_runs.coding_worker_claim_id
agent_runs.coding_worker_last_heartbeat_at
inference_usage_events                                      (table)
music_projects                                              (table)
```

## Data preservation

Row counts were captured directly from PostgreSQL before the migration and again after it, over
every table the read-state contract depends on plus the account and audit tables.

| Table | Before | After | |
| --- | --- | --- | --- |
| `users` | 13 | 13 | preserved |
| `chat_threads` | 5144 | 5144 | preserved |
| `chat_messages` | 113547 | 113547 | preserved |
| `audit_log` | 401 | 401 | preserved |
| `direct_messages` | 14 | 14 | preserved |
| `direct_message_conversations` | 5 | 5 | preserved |
| `direct_message_consents` | 1 | 1 | preserved |
| `direct_message_relationships` | 8 | 8 | preserved |
| `direct_message_relationship_participants` | 16 | 16 | preserved |
| `campaign_continuation_authorities` | 0 | 0 | preserved |
| `agent_runs` | 0 | 0 | preserved |
| `projects` | 15 | 15 | preserved |
| Tables (public schema) | 138 | 140 | +2 (`inference_usage_events`, `music_projects`) |

No row was lost, and no pre-existing row changed. The backend served the same thread and message
counts after the migration (`threads=5144`, `messages=113547` in `/health/chat`).

## The recovery path was proven, not just taken

A `pg_dump` of the live database was taken **before** the migration and was verified by actually
restoring it:

```text
dump      : pre-migration-3a91d7c4e8b2-20261106T064535.dump
size      : 140461603 bytes
sha256    : 6c2136fd6c09b6559f5de9e9f73b305c6c6f9f21b0ac26707ba81dbd86035825
archive   : pg_restore --list -> 1216 entries
```

The archive was restored into a disposable database and compared against the live database it was
dumped from, on schema revision, table count, and the same per-table row counts:

```text
alembic_version                                   3a91d7c4e8b2     3a91d7c4e8b2     OK
table_count                                       138              138              OK
rows.users / chat_threads / chat_messages         13 / 5144 / 113547   identical    OK
rows.direct_messages / conversations / ...        14 / 5 / ...         identical    OK
RESTORE_EQUIVALENCE: EQUIVALENT
```

The scratch database was dropped afterwards. The dump file is the rollback path; the restore proves
that path works rather than asserting that it should.

## The image had to be rebuilt, and its provenance was proven

The `migrator` service deliberately mounts **no** `guardian/` volume: the migration source Alembic
executes from is the one baked into the image, because the macOS virtiofs stat bug makes
`os.path.exists()` unreliable on bind-mounted files carrying the `com.apple.provenance` xattr. The
image in use carried 128 revisions and headed at `3a91d7c4e8b2` — the old head. The application
tier would have served a schema its own code did not describe.

Both images were rebuilt from the reviewed serving checkout:

```text
codexify-backend-runtime:latest        sha256:8ff03e035d57166f51cd1d151a5e486576fc874bf33a844c55f82a06e8827d01
codexify-worker-coding-runtime:latest  sha256:0d0475a4d0d996802e2c98cf2c9871d7175ea11649fa4bcb90141aeb948d7e45
```

The rebuilt runtime image was proved to carry the reviewed migration source, not merely a
same-headed one: a SHA-256 manifest of every migration revision file plus `env.py`,
`run_migrator.py`, and `alembic.ini` was computed **inside the image** and compared against the
same manifest computed from the serving checkout on the host.

```text
host files  : 138
missing in image : 0
mismatched       : 0
PROVENANCE: IDENTICAL
```

The image's own Alembic head was read from inside the image and matches the checkout's single
head:

```text
$ docker run --rm --entrypoint sh codexify-backend-runtime:latest \
    -c "ls /app/guardian/db/migrations/versions | wc -l; \
        python -m alembic -c /app/backend/alembic.ini heads"
135
a7d4c9e2f1b3 (head)
```

## The migrator's coherence gate refused first, and the refusal was correct

The first migration attempt **failed closed**, and it was right to. The migrator compares the
image's baked migration source against a read-only comparison mount at `/source-migrations`, and
refuses to migrate when they describe different revisions. That mount is declared in the base
`docker-compose.yml` as `./guardian/db/migrations`, relative to the Compose **project directory** —
which is the operator's *development* checkout, not the pinned serving source the backend and
workers actually mount.

```text
[Migrator] Alembic heads: ['a7d4c9e2f1b3']
[Migrator] Comparing the migration source against /source-migrations
[Migrator] ERROR: the migration source does not describe this checkout
          (effective_revisions=135, source_revisions=128, missing_from_source=[...])
[Migrator] ...
```

The gate was comparing the image against a revision the Preview does not serve. The serving overlay
— the operator-local third Compose file whose stated purpose is *"Only executable source/config
mounts are replaced"* — replaced the executable source mounts for the backend and the workers but
not the migrator's comparison mount. The fix points that mount at the pinned serving source, so
the gate compares the image against the source that is really served:

```yaml
  migrator:
    volumes:
      - ${CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT:?}/backend:/app/backend
      - type: bind
        source: ${CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT:?}/guardian/db/migrations
        target: /source-migrations
        read_only: true
        bind:
          create_host_path: false
```

This keeps the gate strict; it does not weaken it. The re-run passed it:

```text
[Migrator] Effective migration source: /app/guardian/db/migrations
[Migrator] Alembic heads: ['a7d4c9e2f1b3']
[Migrator] Migration source is coherent (135 revisions)
[docker] run: /usr/local/bin/python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
[Migrator] Verified alembic_version == a7d4c9e2f1b3
[Migrator] Running seed defaults
[Migrator] Done
```

**This change lives in an operator-local file the repository does not track.**
`docker-compose.private-preview-serving.yml` is not on `origin/main`; it is an operator artifact
copied into each serving worktree. The change is therefore not carried by this receipt's commit,
and the next operator who rebuilds a serving worktree must re-apply it. It is recorded here so it
is not lost.

## The serving revision moved, and the pin was repointed

The previous serving worktree (`private-preview-serving-20261029`) could not be advanced in place:
the host sandbox denies replacing existing files in that tree, so `git checkout` moved `HEAD` and
the index while leaving the working tree at the old revision.

```text
$ git checkout HEAD -- guardian/core/config.py
error: unable to unlink old 'guardian/core/config.py': Operation not permitted
```

Creating new files in that tree worked; replacing them did not. Rather than fight the constraint
on a directory whose contents were already inconsistent with its own `HEAD`, the serving source was
moved to a fresh worktree at the same revision and the pin was repointed — the step the approved
deployment sequence already names.

```text
$ git worktree add --no-checkout --detach \
    /Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106 dece01821
$ git sparse-checkout set --no-cone '/*' '!/.claude/'
$ git checkout -f dece01821
HEAD is now at dece01821 Merge pull request #1007 from Resonant-Jones/feat/auto-20261105-c8c1dc20
```

The new worktree is clean (`git status --porcelain --untracked-files=no` is empty), carries all 135
revision files, and every spot-checked file's blob matches `HEAD` exactly. The old worktree was
restored to `c8e72ef86` with a clean tracked status, so it remains a valid fallback.

```text
$ cat ~/Library/Application Support/Codexify/private-preview/serving-source
/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106
```

The backend serves the pinned source, proven by comparing file digests **inside the running
container** against the serving checkout on the host:

```text
guardian/db/models.py                      OK   39a5ebe46751
guardian/core/config.py                    OK   b9e6f9b75a0a
guardian/agents/coding_agent_contracts.py  OK   16fa0d129054
guardian/workers/document_embed_worker.py  OK   09a48460f7c3
guardian/utils/embed_paths.py               OK   03198c9c452c
```

## The twenty read-state checks, re-run against the running service

Two synthetic accounts on the reserved `example.invalid` domain, provisioned through the documented
`private_preview_provision` path with usernames claimed through `PUT /api/profile/social-identity`,
driven over `http://127.0.0.1:8081`. The password was generated into a mode-600 file outside the
repository and was never printed.

**20 of 20 checks passed.**

| Check | Result |
| --- | --- |
| A discovers B's profile by username | PASS |
| A sends a contact request to B | PASS |
| B receives the request | PASS |
| B accepts the request | PASS |
| A holds a relationship with B | PASS |
| A opens a conversation with B | PASS |
| A sends 3 messages to B | PASS |
| **B sees `unread_count = 3` before reading** | PASS |
| **A sees `unread_count = 0` for their own sent messages (account isolation)** | PASS |
| **B advances its read cursor explicitly** | PASS |
| **B's `unread_count` drops to 0 after reading** | PASS |
| **Repeated read is idempotent (cursor never moves backward)** | PASS |
| **Read state persists across a fresh request (reload)** | PASS |
| **A new message makes B unread again (=1)** | PASS |
| **Watermark advances only to the message actually seen (1 remains)** | PASS |
| **4 concurrent reads all succeed and converge (`unread_count = 0`)** | PASS |
| **B's read cursor is not observable by A (no sender-visible receipt)** | PASS |
| Consent HTTP surface is quarantined by the preview profile (expected) | PASS |
| Consent columns are live with fail-closed defaults | PASS |
| An out-of-domain consent state is rejected by the constraint | PASS |

The sender's view of the conversation carried exactly these keys, with no read state among them:

```text
conversation_id, created_at, kind, latest_activity_at, latest_message,
origin, participants, peer, placement, relationship_id, unread_count
```

The last two checks are storage-layer checks, because the Preview profile quarantines the consent
HTTP surface — the endpoint answers `404` by design, so the constraint is the only place the
contract is observable. The columns carry fail-closed defaults, and an out-of-domain value is
rejected by the declared constraint:

```text
automatic_memory_suggestions  character varying  'unset'::character varying
ERROR:  new row for relation "user_settings" violates check constraint
       "user_settings_automatic_memory_suggestions_check"
```

The constraint probe ran inside a transaction that was rolled back, and the probe row was verified
absent afterwards.

## Cleanup

The two synthetic accounts were removed with the reusable account-scoped operator script, which
refuses to widen its own scope and asserts inside the same transaction that no row outside the
named scope changed:

```text
$ bash scripts/ops/private_preview_account_scoped_reset.sh \
      --username readstate-a --username readstate-b --confirm
RESULT: scoped reset committed. Rows outside the named scope were asserted unchanged.
```

| Table | Before cleanup | After cleanup |
| --- | --- | --- |
| `direct_message_read_cursors` | 3 | 2 |
| `message_requests` | 9 | 8 |
| `direct_messages` | 19 | 14 |
| `direct_message_conversations` | 7 | 5 |
| `direct_message_relationships` | 9 | 8 |
| `direct_message_relationship_participants` | 18 | 16 |
| `direct_message_consents` | 2 | 1 |
| `user_profiles` | 10 | 8 |
| `users` | 15 | 13 |

Every count returned to its pre-proof value, and the surviving counts match the pre-migration
baseline exactly.

`CODEXIFY_PREVIEW_APPROVED_EMAILS` was restored from a pre-change copy; the restored
`.env.private-preview` is byte-identical to that copy (sha256
`0f1879ddfa2d9b26014bf4cba1f5294bbef9080573c1bc851c33ad94865ae89d`), the allowlist is back to its
14 entries with no proof account present, and the backend was recreated on the restored allowlist.
Both proof accounts now return `401` from `/api/auth/login`.

## What the deployed Preview looks like now

```text
[Backend] Verifying required tables + alembic_version
[Backend] OK: alembic_version=a7d4c9e2f1b3

GET http://127.0.0.1:8081/health       -> 200  {"status":"ok", ..., "release_hold":true}
GET http://127.0.0.1:8081/health/chat  -> 200  {"ok":true, "queue":{"depth":0,"status":"progressing"},
                                                "threads":5144, "messages":113547}
```

The live database head now equals the repository's single migration head. The `release_hold` flag
is still `true`, which is correct: this receipt qualifies one deployed surface, not the release.

## What this receipt does not establish

- **The product is not qualified.** This is one live surface on the Private Preview. The
  source-matched `supported-compose` surface is still `stale` against the tip, `onboarding-and-people`
  still has no receipt, and the release gate remains `HOLD`.
- **The unread badge was not re-verified in a browser.** The 2026-10-29 browser-badge proof
  stands at serving revision `c8e72ef86`; this run proves the API and storage layers at
  `dece01821` and does not re-assert the rendered badge. The badge is proven in one browser only.
- **The consent HTTP surface was not exercised**, because the Preview profile quarantines
  `iddb`. Storage-layer enforcement is proven; endpoint behaviour is not.
- **No crash-durability claim.** No assertion is made about acknowledged commits surviving a
  server crash.
- **The `music_projects` and `inference_usage_events` surfaces were not exercised.** Their
  migrations are applied and their schema objects are present; no application behaviour on either
  table was tested here.
- **The serving-overlay correction is not carried by the repository.** The file it lives in is
  operator-local and untracked, so the correction must be re-applied to any future serving
  worktree. This is a real gap in the tracked state, not a claim that it is handled.
- **No migration was rewritten** and no revision identity was altered. Both merge revisions remain
  graph-only. ADR-016, ADR-097, ADR-102, ADR-103 and ADR-104 are unchanged.

## Release and ADR posture

No ADR change. The migration chain that carried the read-state feature was applied to the live
Preview database, the serving application containers run the merged mainline source, and a
two-account live test exercised the read-state contract against the running service over HTTP.

## Reproduction

```sh
# 1. serving source
git worktree add --no-checkout --detach \
    /Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106 dece01821
cd /Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106
git sparse-checkout set --no-cone '/*' '!/.claude/'
git checkout -f dece01821
cp <previous-serving-worktree>/docker-compose.private-preview-serving.yml .

# 2. image
export BUILDX_CONFIG=<workspace-local-buildx-config>
docker buildx build --builder desktop-linux --load \
    -f backend/Dockerfile --target runtime -t codexify-backend-runtime:latest .
docker buildx build --builder desktop-linux --load \
    -f backend/Dockerfile --target worker-coding-runtime \
    -t codexify-worker-coding-runtime:latest .

# 3. backup before migrating
docker exec codexify_private_preview-db-1 pg_dump -U codexify -d Codexify -Fc > backup.dump

# 4. migrator (the actor that actually advances the schema)
docker compose --project-directory "$REPO" --env-file "$REPO/.env.private-preview" \
  -p codexify_private_preview \
  -f "$SOURCE_ROOT/docker-compose.yml" \
  -f "$SOURCE_ROOT/docker-compose.private-preview.yml" \
  -f "$SOURCE_ROOT/docker-compose.private-preview-serving.yml" \
  up -d --no-deps --force-recreate migrator

# 5. application containers
docker compose ... up -d --force-recreate backend worker-chat worker-chat-embed \
    worker-document-embed worker-account-import worker-voice worker-warmup \
    worker-coding frontend private-preview-origin

# 6. confirm the pin names the new source, or the LaunchAgent reverts the deployment
cat ~/Library/Application\ Support/Codexify/private-preview/serving-source
```

# Amendment — 2026-11-07: the reconciler advanced the live database past `a7d4c9e2f1b3`

Everything above records the advance to `a7d4c9e2f1b3` and is unchanged. This
section records what happened afterwards, and is appended rather than folded
into the text above.

**What happened.** The serving-source pin moved to a new serving worktree
(`private-preview-serving-20261107`, at `b85036b02`), whose migration head is
`c4f7a9e2b810` — the `music_jobs` table added by the Music Producer work. The
`LaunchAgent` reconciler rebuilt the image and applied that revision to the
live database. It did so **without** an operator present, and nothing in this
receipt predicted it: the three current-state claims in
`docs/architecture/00-current-state.md` still said the live database sat at
`a7d4c9e2f1b3`. They were false.

**The mechanism, stated once.** The live Preview database tracks the **serving
source's** head, not `main`'s. The reconciler advances it to whatever the
pinned serving checkout contains, and `main` moves independently. So the
distance between the live database and `main`'s published head is not a property
of `main` — it is the gap between what the serving source has adopted and what
`main` has published, and it changes whenever either moves. **That distance is
therefore a dated observation, not a value bound to a tip**, and the release
truth now states the mechanism instead of copying the number.

**Measured on the live database, directly:**

```text
alembic_version      : c4f7a9e2b810        (exactly one row)
public tables        : 141                 (140 at a7d4c9e2f1b3, plus music_jobs)
music_jobs           : 0 rows              (new table, empty)
chat_messages        : 113554 rows         (113547 at the advance above — grew by 7)
```

`c4f7a9e2b810` was the repository's single migration head on 2026-11-07, when the
reconciler applied it. It has since been superseded by `b3f8c2d1e907` (the
local-node marker), so the live Preview database is **one revision behind** the
published head — and would close that gap the moment the serving source adopts
the newer revision.

**The current state was proven restorable.** The live database was dumped,
restored into a disposable PostgreSQL, and compared with the live database it
was dumped from — the schema revision, the table count, and the row count of
**every** public table, not only the tables the read-state contract names:

```text
live      : revision=c4f7a9e2b810 tables=141
restored  : revision=c4f7a9e2b810 tables=141
RESTORE_EQUIVALENCE: EQUIVALENT
tables compared: 141
```

**The image's provenance still holds.** The migration files baked into the
running backend image and the migration files in the served checkout were
compared by content hash — 136 files on each side:

```text
MIGRATION_SOURCE_PROVENANCE: BYTE_IDENTICAL
```

**What this does not change.** The reconciler applied a schema revision on its
own; the *recovery path* that this receipt proves is the operator-driven one.
The two are different acts. What is proven here is that the state the
reconciler produced is intact and fully restorable, not that the reconciler
exercised a proven recovery path.

**What this does not establish.** Nothing about the product's qualification.
The Preview remains one live surface; the `release_hold` flag is still `true`.
