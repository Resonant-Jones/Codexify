# 2026-09-04 Private-Preview Scheduled Reconciliation Proof

## Conclusion

`PRIVATE_PREVIEW_SCHEDULED_RECONCILIATION_PROVEN`

One intentionally triggered run of the installed
`com.resonant.codexify-private-preview` LaunchAgent completed its normal
`auto-start` reconciliation against the current private-preview PostgreSQL 15
database. The existing shared `codexify-backend-runtime:latest` migrator was
coherent with source, the canonical migrator exited successfully, all healthy
long-running container identities were preserved, and the bounded canonical
database manifest plus account-import queue were byte-identical.

Result: `SHARED_MIGRATOR_IMAGE_TOPOLOGY_ACCEPTED_FOR_CURRENT_PRIVATE_PREVIEW`.

This is a private-preview recovery proof only. It does not widen Beta, admit a
canary, prove provider execution, or close supported-Compose, browser,
persistence, or observability gates.

## Scope, source, and chronology

- Workflow: `architecture-impact` / proof.
- Source: `main` at `a6b2e6cb13f5ac6f2c201d835f99f065871fdea8`; the
  repository was clean before documentation was written.
- ADR impact: none. ADR-005, ADR-076, ADR-079, ADR-080, and ADR-081 remain
  aligned. No migration, stamp, DDL, Compose change, image build, retag,
  scheduler implementation change, or Project-ownership change occurred.
- Raw logs and deterministic row-digest manifests are retained outside Git in
  a mode-0700 temporary capture directory with mode-0600 files. No session
  token, credential, user content, description, message body, or private
  identifier was committed.

The Alembic gap was qualified, then the live database was migrated. The earlier
live-upgrade receipt recorded a stale scheduled migrator. Direct inspection
subsequently proved the shared artifact coherent; this task then exercised the
actual installed scheduler from that coherent baseline.

## Artifact and live-database boundary

| Surface | Evidence |
| --- | --- |
| PostgreSQL and source volume | PostgreSQL 15; container `0e985de32c8b10680a384f4d0a6cbb3dab3888e5cce714085142bd7c662975a4`; `codexify_private_preview_pg_data` unchanged |
| Live Alembic revision | `b2c8d0e3f5a7` before and after |
| Migrator container | `2997727279b70eaa96523b760c256f7b224c542ff2cc46b4913abc612051393f` |
| Image reference and ID | `codexify-backend-runtime:latest`; `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` |
| Image creation | `2026-09-03T23:19:15.406675837Z` |
| Source and baked target SHA-256 | both `1d65bcea5a76b7c6901ed2eebb9739a7350d45fe0f6e6192c16e8324519a2489` |
| Baked script location | `/app/guardian/db/migrations` from `/app/backend/alembic.ini` |
| Baked head and read-only live current | both exactly `b2c8d0e3f5a7` |
| Bounded history | `f41493d13761 -> a1b7c9d2e4f6 -> b2c8d0e3f5a7` |

Before trigger, `MIGRATOR_ARTIFACT_COHERENT` held: 12 recent successful
completions, zero missing-revision errors, and zero Alembic-upgrade errors.
Afterward, the bounded window contained 14 completions and still zero errors.

## Static validation and scheduled authority

- `.venv/bin/pytest -v tests/ops/test_private_preview_contract.py`: `6 passed
  in 0.49s`.
- The exact Compose render passed. `backend`, `worker-chat`,
  `worker-account-import`, and `migrator` retain
  `codexify-backend-runtime:latest`; the migrator retains the canonical
  `backend/Dockerfile` `runtime` build and
  `/app/backend/scripts/docker/run_migrator.py` command. No dedicated image
  exists.
- The installed LaunchAgent invokes the copied
  `codexify_private_preview_autostart.sh auto-start` runner. Its SHA-256,
  `a367c5cf860cd82d2ebb7bad24137cc2da61c06c68d7ca55884e6724bbec7cbb`,
  exactly matches the tracked lifecycle script. It targets
  `/Volumes/Dev_SSD/Codexify-main`; desired-up was present; StartInterval was
  300 seconds; and no parallel private-preview stack reconciler was active.

At `2026-09-04T09:28:08Z`, this task invoked exactly one
`launchctl kickstart -k gui/501/com.resonant.codexify-private-preview`.
At `2026-09-04T09:28:15Z` the agent was `not running` with last exit code `0`.
Its bounded stdout reported:

```text
Codexify private-preview auto-start reconciliation completed.
```

Result: `SCHEDULED_RECONCILIATION_EXECUTION_PASS`.

## One-shot and long-running preservation

The reconciliation reran the existing `model-prep`, `e2e`, `migrator`, and
`graph-init` one-shots in place. Each retained its container and image
identity and exited `0`. The migrator started at
`2026-09-04T09:28:11.592406930Z`, finished at
`2026-09-04T09:28:13.543278708Z`, and emitted no missing-revision or
Alembic-upgrade failure.

Every healthy long-running service retained the same full container ID, image
ID, CreatedAt, StartedAt, restart count, state, and health posture. The table
lists the identical before/after identity values; the retained external
capture holds the exact timestamps.

| Service | Before = after container ID | Before = after image ID | Restart / state / health |
| --- | --- | --- | --- |
| `db` | `0e985de32c8b10680a384f4d0a6cbb3dab3888e5cce714085142bd7c662975a4` | `sha256:3b0d656f5fff31c7d8a64f500a703dcf3f35e98ce78f602831a73059a5e6a012` | 0 / running / healthy |
| `backend` | `ad60947f13d262ab6db4bf1fc570a82db2a54d15243c056bdddbf4b2c7538c61` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / healthy |
| `worker-chat` | `4345324e45bde1905e47bb3becb3129ced5fd80d0ccce35932b8583a5a6223e4` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / n/a |
| `worker-chat-embed` | `f960f106d393e4b247edb5dd98ae8a71b6f74e143a701b761def81ae4f11b0db` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / n/a |
| `worker-document-embed` | `2a9b7ed41c2c95a96836c102997e9fbbf2710e2629ecc52dfa9ac9a3015598a3` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / n/a |
| `worker-warmup` | `5b6e6ee7a9c2c37eb6c84b0c974368b752a4419de6928e78e597db8635a45e9b` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / n/a |
| `worker-voice` | `e2bb14f6a3eb7293ba723c0344b4be615c8316d88cf8d30a588e4ee17582b451` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / n/a |
| `worker-account-import` | `259e630aa60c1afdd41dd52f5e993d8dbaae2d8020f5afb3cf07e7f64507dc83` | `sha256:dcefae58161d76f01ba4cb25a628cda1fd9b4c7701fb6216fd4c0ca98a22504b` | 0 / running / n/a |
| `frontend` | `b97763a71fcbbed68cd7a1f0ae9dbe907a210de94a655e1b30b46c5c630ff215` | `sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293` | 0 / running / n/a |
| `private-preview-origin` | `f60cc46baaeacdbb784f55929231ff6943c915d5c9e88ddb42b811da8fdeea43` | `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10` | 0 / running / n/a |
| `redis` | `36a0ea12a5ab147201ae6e3aeee617cee2d2a4ea0ac1ded03af26b35d99cbeee` | `sha256:6ab0b6e7381779332f97b8ca76193e45b0756f38d4c0dcda72dbb3c32061ab99` | 0 / running / healthy |
| `neo4j` | `7dc682e1b908c59085e5aa8bf2e8a7f51112006d3a9d045bcdfb7ab2827419fc` | `sha256:937fbd163e302a5751dd329b719c1b05e2a4293af223d61b1aa17e3dea087709` | 0 / running / healthy |
| `tts` | absent | absent | not started |

`worker-coding` was already restarting due its separate Pi authentication
prerequisite. Its container and image ID were unchanged; its restart count
moved from 65 to 67 through that pre-existing policy. It was not a healthy
service restored or recreated by this proof.

Result: `LONG_RUNNING_CONTAINER_IDENTITY_PRESERVED` and
`SCHEDULED_MIGRATOR_NOOP_PASS`.

## Canonical database, queue, and runtime stability

The complete pre/post manifest was byte-identical. It captured deterministic
ordered row digests for Projects, `projects.user_id`, descriptions, threads,
messages, media, documents, images, all direct-message tables, and
`openai_account_import_jobs`.

| Surface | Before and after |
| --- | --- |
| Projects / threads / messages | `4` / `69` / `793` |
| Project IDs / owner / description digest | `257cde944bf50d4fe05001bc33dd0ca4` / `cd5b2bc32121de321f5055069796126d` / `3fbe14874501fbd84b5794b9a10e09ea` |
| Thread / message digest | `8401c4370ad57d8cd6ba7d0d689ec204` / `c89a49081d0297c7cc5d2ccfddaddc68` |
| Media / uploaded-image digest | `331df0aa6a190b38fe3d29d0fc090a66` / `eecca7fd6eaf751c928890ffa0c48b5a` |
| DM domain | zero rows in each table; provenance-null posture `0/0/0` |
| Account-import jobs | 14; digest `c8887bdcb38fdabf51c380276856ed08`; 4 `completed_with_warnings`, 10 `receiving` |
| Account-import Redis queue | 0, unchanged |

The account-import worker remained running and logged idle `recovered=0`.
No queue item was consumed and no import executed. The source database
container, source volume, Project ownership, legacy descriptions, threads,
messages, documents, media, and direct-message persistence were unchanged.

Result: `SCHEDULED_RECONCILIATION_DATABASE_STABLE`.

Post-run runtime checks passed: origin `/health` HTTP 200; origin
`/health/chat` HTTP 200; authenticated unfiltered
`GET /api/chat/threads?limit=200` HTTP 200 with 66 visible threads; and
authenticated `GET /api/projects` HTTP 200 with one visible Project. The proof
used an already-live approved session in memory and retained no token,
account identifier, title, Project name, or message content.

The desired-up marker remained present. The LaunchAgent remained loaded with
StartInterval 300, last exit code 0, and no missing-revision or Alembic-upgrade
error in the bounded observation window.

## Documentation follow-through and deferred scope

`docs/architecture/00-current-state.md` is corrected because its exact claim
that the deployed reconciler artifact remained stale is materially false. The
correction records this proof without widening Beta or private-preview
admission claims.

No dedicated private-preview migrator image is justified by current evidence.
The next eligible independent slice is Project runtime authorization
convergence to canonical `projects.user_id`. Dedicated image isolation remains
deferred unless future evidence shows source/artifact drift, healthy-service
recreation, recurrent missing revisions, or an inability to refresh the
migrator without an application rollout.
