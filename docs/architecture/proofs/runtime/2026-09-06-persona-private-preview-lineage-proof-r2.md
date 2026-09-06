# Persona private-preview runtime lineage, attempt 2

Date: 2026-09-06
Result: **BLOCKED — backend startup failure.**

## Source and gates

Source was clean `feature/persona-studio` at
`140184beff32141882319875498d9650fc23e35e`, deployment root
`/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`.
The [earlier blocked receipt](./2026-09-06-persona-private-preview-lineage-proof.md)
remains historical; its database prerequisite was closed by the
[live migration proof](./2026-09-06-persona-private-preview-live-migration-proof.md).

The database reported `d4e0f2a5b7c9` before and after this deployment attempt.
The stack LaunchAgent was unloaded, tunnel agent loaded, and desired-up marker
present. All three conditions remained true at closeout.

Compose rendered successfully using project `codexify_private_preview`, the
Persona worktree, and the existing secure env path
`/Volumes/Dev_SSD/Codexify-main/.env.private-preview`. No credentials were
printed or copied. Render checks confirmed the project, profile
`v1-whooshd-deepseek-web`, existing `codexify_private_preview_pg_data` volume,
and Persona config source. No source/config/Compose/profile file was changed.

## Deployment outcome

The authorized `docker compose ... up -d --build` built the existing targets
and replaced application containers. It failed because the backend never
became healthy. Its repeated startup failures ended with exit 3 and prevented
frontend, origin, and dependent workers from starting.

The structured startup receipt reports `pyo3_runtime.PanicException` along:

`guardian_api._app_lifespan_body → dependencies.init_services → vector.store
→ backend.rag.embedder._create_chroma_client → chromadb.PersistentClient
→ chromadb.api.rust.start`.

This locates the blocker at Chroma initialization; it does not establish the
underlying Rust panic cause or authorize deletion/rebuilding of vector state.
No source/config repair, vector-state mutation, downgrade, or browser proof
was attempted.

| Container | ID | Image ID | Final state |
| --- | --- | --- | --- |
| backend | `a120cb2113232c3dbcbcc2caea2bee4bfc0d521113254358a1e5e4411d4a060e` | `sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b` | explicitly stopped, exit 3 |
| frontend | `5bae24c191917875fdb10c41c45cae1ce17ed8990b5fd2a527ab985f0596a4ee` | `sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293` | created, never started |
| migrator | `7733d5069a72b0863bee559260c2491d1ec2ae9f3dcf718928a89772acbd94a2` | `sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b` | exited 0 |

The frontend uses the existing `node:20-alpine` image plus source bind mount;
there is no custom frontend build target. Its image identity alone cannot
prove Persona frontend source or successful startup.

Backend mount metadata resolves `/app/config` to Docker Desktop's host path
`/host_mnt/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/config`.
This is the intended Persona worktree, but the container is stopped; no live
configuration-authority qualification is claimed.

The normal startup migrator exited 0, with the database revision unchanged at
`d4e0f2a5b7c9`. No extra migration was run for proof. A new full data-preservation
comparison was not performed in this deployment task.

## Uncompleted gates and safe final state

Health failed at backend startup. Running source/container checksum equality,
frontend source qualification, live OpenAPI Persona exposure, anonymous 401,
and reachability validation remain unproven and were not continued after the
startup stop condition. Authenticated browser save/readback remains pending.

The restarting backend was explicitly stopped per the failure boundary.
Application/frontend/origin/workers remain stopped or never-started. PostgreSQL,
Redis, and Neo4j are healthy and running. The database remains at
`d4e0f2a5b7c9`; no volume was removed and no database downgrade or checkpoint
restoration occurred. The old checkout was not modified.

The fresh live-migration checkpoint remains retained at:

`/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/codexify-persona-migration-rehearsal.08qzdrlb/live-20260906T222805Z`.

Its dump SHA-256 was rechecked unchanged:
`510fd0a781febbd4a3e33d6b52405ddac46b533164cec5ba08e391e90a9dd04f`.

**Operator warning:** periodic stack reconciliation remains suspended. Tunnel
LaunchAgent and desired-up remain intact, but the application origin is not
available. Do not resume the old reconciler against this handoff state.

## Validation and next prerequisite

Only this receipt and the authorized current-state document changed.
`python3 scripts/validate_docs.py`, working diff check, and staged diff check
passed. ADR-082 and persistence/auth authority invariants are unchanged; no new
ADR or release claim applies.

Warnings: initial Docker build metadata access was sandbox-denied; the approved
escalated build completed. On continuation, Pi catalog returned zero available
models and exact-pair preflight rejected `deepseek/deepseek-v4-pro`. No inference
or delegated opinion occurred; no Pi repair was attempted.

Failure: backend Chroma/Rust initialization panic prevented healthy startup.
Restricted deployment and startup logs remain outside Git at
`/tmp/persona-deploy-r2.log` and `/tmp/persona-r2-backend-failure.log`.

Next prerequisite is a bounded startup diagnosis and separately authorized
repair of the Chroma initialization failure, preserving canonical data and
the migration checkpoint. Then rerun deployment lineage/health/route proof
before authenticated Persona browser save/readback or reconciliation resumption.
