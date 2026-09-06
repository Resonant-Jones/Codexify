# Persona private-preview deployment lineage — BLOCKED

Date: 2026-09-06

## Conclusion

Deployment stopped at the mandatory database compatibility gate, before
reconciler suspension, Compose rendering/build, or container replacement.
The live Alembic revision set does not equal the Persona source head set.
No deployment qualification or browser persistence claim is established.

## Source and operator boundary

- Intended source: `feature/persona-studio` at
  `099c67a3a075e2554c0a0d73d14849d1538b171c`, initially clean.
- Intended deployment root:
  `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`.
- Existing reconciliation root: `/Volumes/Dev_SSD/Codexify-main`, at
  `a5840b7515a063116be1cda16fe39136662164bf`. Its unrelated staged Dev Log
  deletion was observed and left untouched.
- Existing Compose project: `codexify_private_preview`.
- Existing secure preview env file was checked for existence/readability only;
  its contents were not inspected or copied.
- Both `com.resonant.codexify-private-preview` and
  `com.resonant.codexify-private-preview-tunnel` remained loaded in `gui/501`.
  The desired-up marker remained present. No LaunchAgent was unloaded.
- Pi delegation was not used: deployment/operator actions remained with Codex
  under the skill's deployment exclusion. No Pi repair was attempted.

## Database gate

Source command:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini heads
```

The canonical configuration resolves scripts from `guardian/db/migrations`.
Result: source head set `{d4e0f2a5b7c9}`.

A read-only `SELECT version_num FROM alembic_version ORDER BY version_num`
through the existing database container's `psql` returned
`{b2c8d0e3f5a7}`. No credential values were printed.

**BLOCKED: the revision sets differ.** No migration, stamp, schema repair,
deployment, or post-deployment database read occurred.

## Existing runtime identities

These are pre-existing identities, not images built from the Persona branch.

| Service | Container ID | Image ID |
| --- | --- | --- |
| backend | `53027bbf4153769ce2b04687361dd47adeb4611e5214c4307d7f2371dac35e7c` | `sha256:d104c21e12666f51c62ed623db94c10a801a1808fe96bc2a2cfbc79ea4be5042` |
| frontend | `b97763a71fcbbed68cd7a1f0ae9dbe907a210de94a655e1b30b46c5c630ff215` | `sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293` |
| db | `01d246fa2e1a31859c3e34f84138220ec10566966313932e51644e9bfa755936` | `sha256:3b0d656f5fff31c7d8a64f500a703dcf3f35e98ce78f602831a73059a5e6a012` |

Existing origin `/health` and `/health/chat` requests succeeded; chat reported
`ok: true`, `status: healthy`. This is existing-runtime health only.
The pre-existing coding worker was restarting and was not repaired.

## Unperformed proof and preservation

Build attribution, Persona source/container checksum equality, active config
mount qualification, post-deployment OpenAPI, anonymous 401, and the
reachability validation were not performed after the stop gate. They remain
pending, as does authenticated browser save/readback.

No rollback was required because no replacement or operator-posture mutation
occurred. Periodic stack reconciliation remains active, not suspended.
No source/config/test files, credentials, volumes, or user data were modified
by this task. ADR-082 manifest, revision, binding, account, and runtime
authority invariants remain unchanged; no new ADR or release claim applies.

## Validation and next prerequisite

`python3 scripts/validate_docs.py` and `git diff --check` passed. Only this
authorized proof document changed; current-state remains accurate with
deployed Persona lineage and browser proof pending.

The smallest prerequisite is a separately authorized migration-compatibility
and data-preservation qualification for the preserved private-preview database
from `b2c8d0e3f5a7` to the Persona branch head `d4e0f2a5b7c9`, followed by any
explicitly approved upgrade. Then rerun this deployment task's equality gate.
Do not bypass it with stamping or an opportunistic deployment migration.
