# Host-owned music job attribution — the host no longer depends on the engine's age

Date: 2026-11-07. Disposition: **the host now records which project a music
job belongs to, and the finished files are attributed whether or not the
service echoes the context back.** Release: **HOLD**. This is a code change
on a quarantined surface: the `music_projects` route is not in the default
profile's route posture and `v1-music-producer` is not a qualified supported
path. It qualifies nothing and widens no release gate.

## Revision custody and scope

| Source | Verified revision |
| --- | --- |
| Base of this branch | `cbc5dee70` (`origin/main` at branch creation, the #1005 merge commit) |
| This change | `38b4f3ec9` — `fix(music): the host owns the job's attribution` |
| Migration | `c4f7a9e2b810` — `add music_jobs table`, revising `a7d4c9e2f1b3` |
| Alembic head after this change | `c4f7a9e2b810`, single head, 136 revision files |

Files belonging to this change:

- `guardian/routes/music_projects.py` — record the attribution when the job
  handle is minted; resolve it at poll time.
- `guardian/core/pgdb.py` — `record_music_job()`, `get_music_job()`.
- `guardian/db/models.py` — the `MusicJob` model.
- `guardian/db/migrations/versions/c4f7a9e2b810_add_music_jobs_table.py` —
  the schema.
- `tests/routes/test_music_projects.py` — six tests, five of them
  mutation-proven.
- `scripts/proofs/prove_music_job_attribution.py` — the live proof harness,
  committed so the receipt can be reproduced.
- `scripts/proofs/mutate_music_attribution_tests.py` — the mutation check,
  committed for the same reason.
- `scripts/proofs/README.md` — the harnesses' documentation.
- `docs/architecture/00-current-state.md` — publishes the new head, and
  names the host's ownership of the attribution.
- `docs/architecture/adr/108-codexify-music-producer-authority-and-agentdaw-service-boundary.md`
  — a dated note. The ADR is unchanged in substance and remains `Proposed`.

## The defect

The route read which project a finished job belonged to out of the context
the service echoed back on the job. That made the host's attribution depend
on the engine's age.

It is the same shape as the three registration defects PR #1003 fixed, one
layer up. The engine's own source shows the defect at its origin: in
`v0.1.2`, `jobs.create()` takes no context at all.

```
$ docker exec agentdaw-v012 grep -n "def create" -A 4 /app/agentdaw/serve.py
    def create(self, action: str) -> _Job:
        job = _Job(action)
```

In `v0.1.6` the same method takes the context and stores it. The difference
between the two is the whole defect.

## The fix

The host sent the context, so it already knows what the work belongs to. It
now keeps its own copy, in a new `music_jobs` table, written when the job
handle is minted — the one moment the host knows the answer.

| Property | How it is enforced |
| --- | --- |
| The first write wins | `INSERT ... ON CONFLICT (job_id) DO NOTHING`; a later write cannot move a job |
| The host's record wins at poll time | `_attribution_for()` reads `music_jobs` first |
| The service's echo is a fallback | Used only when the host has no record, and **logged as a warning** |
| A refused write does not fail the compose | The write is wrapped, logged and swallowed |
| The table stays minimal | `job_id`, `project_id`, `thread_id`, `created_at` — no `user_id`, because the asset row already carries it |

`thread_id` is nullable and set to null on delete: a thread that goes away
leaves the job attributed to its project alone, because losing the
attribution to a thread is not a reason to lose the project.

## Mutation check

Five mutations, each caught by the test that names it. A test that passes
with and without the fix proves nothing, so each mutation was applied to the
real source and the named test was run against it.

| Mutation | Test | Result |
| --- | --- | --- |
| The host never records the attribution | `test_the_host_records_which_project_a_job_belongs_to` | **failed (caught)** |
| The poll reads only the context the service echoed | `test_a_service_that_echoes_nothing_still_gets_its_files_attributed` | **failed (caught)** |
| The echoed context wins over the host's record | `test_the_hosts_own_record_wins_over_what_the_service_echoed` | **failed (caught)** |
| A later record moves the job | `test_a_job_is_not_moved_by_a_later_record` | **failed (caught)** |
| A refused record write fails the compose | `test_a_record_that_cannot_be_written_does_not_cost_the_files` | **failed (caught)** |

The mutation harness is `scripts/proofs/mutate_music_attribution_tests.py`. It
restores each file it touches from a byte-verified backup after every
mutation, whether the mutation was caught or not.

## Live proof

The route's real functions, a real engine, a real PostgreSQL at
`127.0.0.1:55599` (database `codexify_music`, schema at head), and a real
`media_assets` table. Project `7`, chat thread `1`.

Both engines were run as local processes so that the artifacts they produce
are at paths the host can actually read — the same shared-volume arrangement
the Compose deployment uses.

### v0.1.6 — the engine that echoes the context

```
compose returned: {'job_id': 'a55aa118ee1448daba9ab52a094085df', 'status': 'running'}
music_jobs row:   [{'job_id': 'a55aa118ee1448daba9ab52a094085df', 'project_id': 7, 'thread_id': 1}]
job status:       succeeded
echoed context:   {'request_id': None, 'thread_id': '1', 'user_id': 'local', 'project_id': '7'}
artifacts:        5
media_assets:     5 row(s) — every one project_id=7, thread_id=1
```

### v0.1.2 — the engine that discards the context

This is the leg that matters. Its echoed context is empty, exactly as the
defect describes, and the files are still attributed — because the host
recorded the attribution itself.

```
compose returned: {'job_id': '9e3d27ad36ea4c89bb13ba18ba7f0875', 'status': 'running'}
music_jobs row:   [{'job_id': '9e3d27ad36ea4c89bb13ba18ba7f0875', 'project_id': 7, 'thread_id': 1}]
job status:       succeeded
echoed context:   {}
artifacts:        5
media_assets:     5 new row(s) — every one project_id=7, thread_id=1
```

Before this change, that leg produced five files and zero registrations,
and the host reported success.

The committed harness was then run again against both engines from this
checkout — project `8`, chat thread `2` — and reproduced the same result:

```
VERDICT
-------
engine                       status       echoed a context
v0.1.6                       succeeded    yes
v0.1.2                       succeeded    no

PASS: every engine's files were attributed against the right project and thread
```

The harness is `scripts/proofs/prove_music_job_attribution.py`. It is
committed, so this receipt can be reproduced rather than taken on trust.
Its pass condition is the invariant — the files are attributed against the
right project and thread, for every engine exercised — and whether the
engine echoed the context back is reported as an observation, because that
is a property of the engine and not of the host.

## Automated coverage

| Suite | Result |
| --- | --- |
| `tests/routes/test_music_projects.py` | 34 passed (28 before this change, 6 added) |
| `tests/routes/test_media_routes.py`, `tests/routes/test_media_upload.py`, `tests/test_media_identity.py` | 36 passed |
| `tests/test_migrations.py` (the CI migration contract) | 1 passed |
| `tests/architecture`, `tests/evidence_packets` | the published-migration-head claim now passes; five failures remain and are environmental |

The five remaining architecture failures are `PermissionError` on `unlink`
of files under the pytest temp directory. `unlink(2)` is denied on this
host — probed directly, in `/tmp` as well as on the repository volume — and
the failures are in the knowledge-graph projection and evidence-packet
validators, which this change does not touch. The published-migration-head
claim test failed before the head was updated and passes now.

## What this does not establish

- **Not a runtime qualification.** The music surface is behind a quarantining
  profile and is not a qualified supported path.
- **The live Preview database is not advanced by this change.** It stands at
  `a7d4c9e2f1b3`, one revision behind the head this change publishes.
- **The engine pin is still the right default**, but the host's attribution
  no longer depends on it. The service's echo remains the fallback for a job
  the host never recorded, and using it is logged.
- **ADR-108 is not ratified by this change.** Its dated note records the
  host's ownership of the attribution; the ADR's substance and its `Proposed`
  status are unchanged.
