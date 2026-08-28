# Tester migrator rerun side-effect and backend-only lifecycle proof

## Result

`TESTER_MIGRATOR_RERUN_EFFECTS_QUALIFIED`

The prior `docker compose start backend` lifecycle event is now qualified as a
Compose dependency fan-out, not a backend-entrypoint migration. Its automatic
migrator invocation was an Alembic no-op: the database was already at the sole
source head before the event, remained at that head afterward, and the rerun
log contains no Alembic `Running upgrade` record. The automatic seed invocation
is classified separately as
`SEED_DEFAULTS_RERUN_IDEMPOTENT_BUT_MUTATION_NOT_HISTORICALLY_PROVABLE`:
the implementation bounds its writes, and the post-event readback is
canonical, but no pre-event project/FK snapshot exists from which to prove
that no row was reassigned or removed.

The exact future existing-container-only ritual is:

```text
docker start codexify_tester-backend-1
```

It was not executed in this task. The current backend was left running and
healthy throughout. No runtime lifecycle action, migration, seed, model
request, DeepSeek request, Watchdog action, or storage mutation occurred while
this proof was being collected.

## Scope and lineage

- Codexify checkout: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`.
- Codexify branch: `codex/diagnose-tester-fresh-chroma-failure`.
- Codexify HEAD before this proof: `90a3e24df1030da90f2724b8c75f638fde8d3b68`.
- Required predecessor `90a3e24df1030da90f2724b8c75f638fde8d3b68` was verified
  with `git cat-file -e` and `git merge-base --is-ancestor`.
- The unrelated `guardian/workers/watchdog_review_worker.py` remained
  untouched and unstaged.
- Active Tester source: `/Volumes/Dev_SSD/Codexify-main`.
- Active source branch/HEAD: `main`/
  `6b383badb1eb5c5301df0c92c88215e605bf9fff`.
- Active source remote: `https://github.com/Resonant-Jones/Codexify.git`.
- Active source working tree was clean (`main...origin/main [behind 40]`).
- Active Compose project: `codexify_tester`, using the active source's
  `docker-compose.yml`, `docker-compose.tester.yml`,
  `docker-compose.whooshd-deepseek.yml`, and `.env.tester`.

No `.env.tester`, Compose file, migration, seed, backend source, Whoosh'd
source/configuration, model artifact, Redis, Chroma, Postgres, Guardian policy,
DeepSeek configuration, or Watchdog file was changed.

## Historical lifecycle event

The previous lifecycle task issued exactly this command from the active source
root:

```text
docker compose --project-name codexify_tester --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml start backend
```

The existing backend container began at
`2026-08-26T15:34:56.359647755Z`. The Compose dependency graph caused the
following stopped containers to start before it:

| Container | Started | Finished | Result |
| --- | --- | --- | --- |
| `model-prep` | `15:34:42.102364638Z` | `15:34:42.518987055Z` | exit `0` |
| `migrator` | `15:34:42.616520638Z` | `15:34:44.208537014Z` | exit `0` |
| `graph-init` | `15:34:54.240333837Z` | `15:34:55.847565672Z` | exit `0` |
| `neo4j` (transitive dependency) | `15:34:42.122809263Z` | still running | healthy |

The active Compose render proves the dependency edges:

- `backend` requires healthy `db` and successful completion of `graph-init`,
  `migrator`, and `model-prep`.
- `graph-init` requires healthy `neo4j`.
- `worker-chat` requires healthy `redis` and `backend`, plus completed
  `model-prep`; Redis is not a direct backend dependency.

The backend entrypoint (`backend/scripts/docker/run_backend.py`) waits for
Postgres, verifies required tables and `alembic_version`, runs
`seed_defaults.py`, and then execs Uvicorn. It does not invoke Alembic. The
Compose `migrator` entrypoint (`backend/scripts/docker/run_migrator.py`) is the
component that runs `alembic --raiseerr ... upgrade heads` and then invokes
`seed_defaults.py`.

## Alembic effect

### Evidence

- The prior coherence proof, committed as
  `d6659590aa844e66f467fc98121833c26037d59f` on 2026-08-25, records the live
  Tester `alembic_version` as `6e9f0a1b2c3` before and after its read-only
  runtime checks.
- Static parsing of the active source migration graph found 92 migration
  nodes and exactly one head: `6e9f0a1b2c3`.
- The active head file is
  `guardian/db/migrations/versions/6e9f0a1b2c3_add_github_watchdog_review_dispatches.py`.
  Its source SHA-256 is
  `3820e65ae666fc26bb07775bdbe008759c75558cf61fb866b5a36f6b53047207`.
- The live Postgres read-only query after the event returned exactly
  `6e9f0a1b2c3` from `alembic_version`.
- The 15:34 rerun log contains the `upgrade heads` command and Alembic
  context setup, followed by `Running seed defaults`; it contains no
  `Running upgrade <revision> -> <revision>` record.
- The migrator container exited `0` at
  `2026-08-26T15:34:44.208537014Z` and was not rerun during this proof.

### Classification

`ALEMBIC_RERUN_NOOP`

The historical pre-event head, active source head, post-event database head,
and absence of an Alembic upgrade record agree. No migration revision was
applied, stamped, downgraded, or rewritten by the unintended rerun.

## Seed effect

### Implementation and log boundary

The active `backend/scripts/seed_defaults.py` (SHA-256
`18629dfc41160e1323857eae524ad090433b5c6908611a4ed3c17b802c4f1cc5`) has two
seed-owned operations:

1. `ensure_project("General", ...)` inserts only when no row with that name
   exists (`INSERT ... SELECT ... WHERE NOT EXISTS`). It does not update an
   existing canonical row.
2. `dedupe_default_project_aliases` checks the canonical `General` and legacy
   `Loose Threads` names. If an alias exists, it updates every discovered
   `project_id` foreign-key table and deletes the alias project; if no alias
   exists, it returns without reassignment or deletion.

The historical migrator log records `[Migrator] Running seed defaults` at
`2026-08-26T15:34:43.860877222Z`, the `seed_defaults.py` process launch at
`15:34:43.860897597Z`, and `[Migrator] Done` at
`15:34:44.203909805Z`. The payload of the seed logger lines is redacted by the
host diagnostic surface, so it is not treated as a mutation receipt.

### Bounded Postgres readback

The read-only post-event state is:

- `projects` contains 4 rows overall.
- The seed names contain one canonical row:
  `id=1`, `name=General`, description `Default project for content without a
  specified project`, created/updated `2026-07-25 19:13:26.182433+00`.
- No `Loose Threads` row exists.
- Project-bearing rows by table were:

  | Table | Rows with `project_id` |
  | --- | ---: |
  | `chat_threads` | 5137 |
  | `eval_trace_snapshots` | 50 |
  | `generated_documents` | 0 |
  | `generated_images` | 0 |
  | `guardian_delegation_intents` | 0 |
  | `media_assets` | 4535 |
  | `project_document_links` | 0 |
  | `repository_bindings` | 0 |
  | `tts_outputs` | 0 |
  | `uploaded_documents` | 0 |
  | `uploaded_images` | 4535 |

No pre-rerun project/FK snapshot was captured, and the seed SQL can delete a
legacy alias or reassign foreign keys when one exists. Therefore a strict
historical no-op claim is not justified even though the implementation is
idempotent for the observed canonical state.

### Classification

`SEED_DEFAULTS_RERUN_IDEMPOTENT_BUT_MUTATION_NOT_HISTORICALLY_PROVABLE`

This is a bounded, known limitation rather than an unresolved seed effect: the
write surface is identified and the canonical post-state is recorded. Future
operator runs should capture the project rows and project-FK counts before
running any seed path if a historical no-op claim is required.

## Backend-only lifecycle ritual

The existing backend container is `/codexify_tester-backend-1` (short ID
`475bb0079346`). Its Compose labels bind it to the active source root and the
three active Compose files. Read-only inspection recorded:

- image digest `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf`;
- working directory `/app`;
- entrypoint `python` and the existing backend command;
- the existing `127.0.0.1:8889 -> 8888/tcp` binding;
- `restart_policy=no`, `auto_remove=false`; and
- the existing source, model, data, Chroma, and named-volume mounts.

`docker start --help` defines `docker start` as starting one or more stopped
**containers**. It accepts container names/IDs, not Compose service names, and
has no dependency traversal, build, recreate, or project-resolution option.
The named-container command therefore starts only the already-created backend
container and preserves its inspected image, command, mounts, environment,
network, and port configuration. It is valid only while that container still
exists and is stopped; a removed container would require a separately
authorized lifecycle decision.

The prior `docker compose start backend` command is not the backend-only
ritual: in this active Compose project it traversed the declared completed and
health dependencies and reran the one-shot migrator/seed path. No command was
executed to test `docker start` because this task forbids lifecycle actions.

## Runbook posture

`docs/Ops/friends-family-tester-runtime.md` contains `make tester-up`, explicit
`up` commands, and an isolated `run --rm migrator` ritual. It does not contain
the misleading `docker compose start backend` command. No runbook edit was
therefore necessary or authorized; this proof is the only Codexify file in
scope.

## Current runtime and execution boundary

The runtime remained healthy during this proof:

- backend: running, healthy, restart count `0`, started
  `2026-08-26T15:34:56.359647755Z`; `GET /health` returned HTTP `200` with
  profile `v1-whooshd-deepseek-web`, valid profile state, and provider `local`;
- Postgres: running, healthy, restart count `0`, started
  `2026-08-26T15:33:58.73601484Z`;
- Redis: running, healthy, restart count `0`;
- `worker-chat`: running, restart count `0`; heartbeat TTL was `42` seconds
  and the heartbeat payload reported `status=idle`;
- chat queue `codexify:queue:chat`: depth `0`; and
- Watchdog tables remained empty: 0 attempts, 0 dispatches, and 0 results.

The counts below describe this proof task only; the historical automatic
migrator/seed invocation is accounted for above:

```text
TESTER_BACKEND_LIFECYCLE_ACTIONS_DURING_SIDE_EFFECT_PROOF=0
TESTER_POSTGRES_LIFECYCLE_ACTIONS_DURING_SIDE_EFFECT_PROOF=0
MIGRATOR_INVOCATIONS_DURING_SIDE_EFFECT_PROOF=0
SEED_INVOCATIONS_DURING_SIDE_EFFECT_PROOF=0
MODEL_INVOCATIONS_DURING_SIDE_EFFECT_PROOF=0
DEEPSEEK_REQUESTS_DURING_SIDE_EFFECT_PROOF=0
WATCHDOG_ACTIVITY_DURING_SIDE_EFFECT_PROOF=0
```

Only read-only `docker inspect`, `docker logs`, `docker compose config`,
`psql SELECT`, Redis health/queue/heartbeat reads, `curl /health`, and local
source inspection were performed. There was no chat task, completion,
provider request, model download, GitHub I/O, Command Bus action, Build Loop
action, manual Postgres/Redis/Chroma mutation, Whoosh'd operation, or release
truth change.

## ADR impact and validation

**Aligned with ADR-074 and the existing migration/persistence and Tester
runtime contracts; no ADR change.**

Validation performed:

- prerequisite ancestry, branch, HEAD, and working-tree checks;
- active source remote/branch/HEAD and Compose project identity;
- active Compose dependency graph render;
- static source migration-head graph and migration-file hash;
- live `alembic_version` readback;
- historical migrator/seed log window and container timestamps;
- seed implementation inspection and bounded Postgres project/FK readback;
- `docker start --help` and existing backend container configuration/mount
  inspection;
- backend `/health`, Redis queue/heartbeat, and container health readback;
- `python3 scripts/validate_docs.py`;
- `git diff --check`.

`docs/architecture/00-current-state.md` remains untouched. No release or
current-state claim changes.

## Deferred next slice

Use the proven `docker start codexify_tester-backend-1` ritual only when the
existing backend container is stopped but not removed. After a separately
authorized backend-only recovery, the next proof may qualify Guardian's
current Qwen inventory; it must still avoid inference, DeepSeek execution, and
Watchdog activity until the authenticated Qwen completion gate passes.
