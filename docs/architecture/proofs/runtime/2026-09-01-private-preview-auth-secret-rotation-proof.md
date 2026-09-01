# 2026-09-01 Private-Preview Guardian Authentication Secret Rotation Proof

## Conclusion

`PRIVATE_PREVIEW_AUTH_SECRET_ROTATION_PROVEN`

Codexify-owned private-preview authentication secrets are rotated and
pre-rotation sessions are invalidated.

Guest traffic remains closed. The next prerequisite is provider-side
DeepSeek credential rotation and requalification.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: implementation
- Evidence posture: live-runtime proven
- Source Git commit: `bf91ab08c39e1c4545e61bebbebf7b43fc9c7ed0`
- Recovery proof commit: `bf91ab08c39e1c4545e61bebbebf7b43fc9c7ed0`
- Runtime project: `codexify_private_preview`
- Target configuration: untracked `.env.private-preview`

The three rotated keys were exactly:

- `GUARDIAN_SESSION_SECRET`
- `GUARDIAN_JWT_SECRET`
- `GUARDIAN_API_KEY`

`DEEPSEEK_API_KEY`, database credentials, Cloudflare credentials, allowlists,
provider/model configuration, URLs, ports, and all other non-target env content
were preserved. No users were invited, no public ingress was opened, and no
guest traffic was enabled.

The earlier recovery qualification remains the governing prerequisite:
[`2026-09-01-private-preview-backup-restore-after-docker-recovery-proof.md`](2026-09-01-private-preview-backup-restore-after-docker-recovery-proof.md).
No external engineering model was used because this task handled
authentication-sensitive state.

## Pre-rotation proof

- `.env.private-preview` existed, was ignored by Git, was not tracked, and was
  mode `0600`.
- Each target assignment occurred exactly once, was non-empty, and was not a
  committed placeholder.
- A mode-`0600` temporary evidence file held only one-way SHA-256 fingerprints
  of the three pre-rotation values. It was never printed or committed.
- The running backend issued a synthetic
  `private-preview-secret-rotation-proof` session through canonical
  `guardian.core.auth.issue_session_token`; canonical verification passed
  before rotation. The token was never persisted or sent to a browser.

## Rotation and persistence

Each replacement was independently generated in local memory with a
cryptographically secure `secrets.token_urlsafe(64)` call. A bounded helper
replaced only the three target assignments through a mode-`0600` temporary
sibling, flushed and fsynced it, atomically replaced `.env.private-preview`,
and rechecked the final mode.

The final values differed from the original pre-task fingerprints for all
three targets. A private non-target-content comparison passed, including the
unchanged DeepSeek credential and runtime configuration. No secret value or
fingerprint appears in this receipt or Git.

## Runtime consumer adoption

Resolved Compose configuration was rendered only to a mode-`0600` temporary
file outside the repository. The running consumers identified by service name
were:

- `backend`
- `db`
- `worker-account-import`
- `worker-chat`
- `worker-chat-embed`
- `worker-document-embed`
- `worker-warmup`

Those services were recreated with exact service-scoped
`--no-deps --force-recreate` operations. Frontend, private-preview origin,
Redis, Neo4j, one-shot jobs, and unrelated Buzz/Tester/watchdog/audit stacks
were not recreated. The final in-memory runtime comparison passed for every
applicable target: `live_consumer_secret_rotation=PASS`. No running consumer
matched an old target fingerprint.

## Session security proof

The first 5-minute synthetic sentinel was valid before the first rotation and
was rejected afterward, but its expiry had elapsed before an independent
freshness check. That result was deliberately discarded rather than credited
as rotation evidence.

A fresh bounded rerun then issued a new 30-minute synthetic sentinel under the
first rotated runtime, verified it before the final rotation, generated a new
independent set of all three Guardian values, and recreated the same affected
consumers. The final sentinel was still unexpired when checked and the
recreated backend reported:

```text
pre_rotation_sentinel_unexpired=PASS
old_session_token_valid=false
new_session_roundtrip=PASS
```

The old-token check used stdin and canonical
`guardian.core.auth.verify_session_token`; no token was printed, persisted, or
placed in browser storage.

## Browser and runtime proof

- Existing static private-preview validation — PASS; 39 focused tests passed.
- Frontend secret isolation — PASS; the browser received none of the three
  Guardian secrets or `DEEPSEEK_API_KEY`.
- Post-rotation reachability — PASS at `http://127.0.0.1:8081`.
- Post-rotation Compose health — PASS: Postgres, backend, Neo4j, and Redis
  healthy; workers, frontend, and loopback origin up; one-shot migrator,
  model-prep, and graph-init jobs remained exited `0`.
- Private origin publication remained exactly loopback-only:
  `127.0.0.1:8081 -> 8080`.
- Source Postgres volume `codexify_private_preview_pg_data` remained present;
  no media or database migration/schema operation was performed.

Reachability and health do not prove DeepSeek provider execution, persistence,
guest isolation, or canary acceptance. Those remain separate gates.

## Secret hygiene and preservation

- `.env.private-preview` remains ignored, untracked, and mode `0600`.
- A final in-memory scan found no rotated secret value in any tracked file.
- The resolved Compose file, old/new fingerprint files, synthetic session files,
  and all other temporary rotation evidence were deleted.
- No secret value, fingerprint, environment dump, password, session token, or
  provider credential entered Git.
- No `docker compose down -v`, volume deletion, password reset, migration,
  provider change, or public-ingress operation occurred.
- The unrelated deletion of
  `docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md` remains untouched and
  unstaged.

## Warnings and documentation boundary

The current `docs/architecture/00-current-state.md` still contains an older
statement that private-preview recovery is unproven, while the newer recovery
receipt above proves that gate. This task was explicitly forbidden from
changing current-state/release assertions, so the contradiction remains
visible and is not treated as silently normalized release truth.

The first sentinel expiry and temporary harness serialization retries were
non-production proof-harness issues. They produced no secret output, did not
mutate tracked files, and were not used for the final conclusion. The final
unexpired sentinel sequence is the sole session-invalidation evidence.

## Validation results

- `git status --short` — PASS before and after; only the unrelated Dev Log
  deletion was present outside this receipt.
- `git check-ignore -q .env.private-preview` — PASS.
- `.env.private-preview` existence and mode check — PASS, `0600`.
- `docker desktop status` — PASS, `running`.
- `docker version` — PASS, Docker Desktop `4.88.1` / Engine `29.7.2`,
  `desktop-linux`.
- Structural target-key validation — PASS.
- Canonical pre-rotation session sentinel — PASS.
- Final target-change and non-target-preservation comparison — PASS.
- Affected-consumer runtime fingerprint comparison — PASS.
- Old-session invalidation with unexpired sentinel — PASS.
- New-session canonical roundtrip — PASS.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static` — PASS.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` — PASS.
- Final tracked-secret scan and temporary-file cleanup — PASS.
- `python3 scripts/validate_docs.py` — PASS after this receipt was added.
- `git diff --check` — PASS after this receipt was added.

## ADR impact

Aligned with ADR-005, ADR-039, ADR-041, ADR-042, and ADR-069, plus the
accepted authentication-boundary decision. No new ADR is required. This task
performs credential hygiene inside the existing identity, session, and
private-preview exposure boundary; it does not alter those contracts.

## Documentation follow-through

Only this live proof receipt is authorized and changed. The private-preview
runbook, `.env.private-preview.example`, current-state assertions, recovery
receipts, Compose files, authentication source, provider routing, and ADRs were
left unchanged.

## Axis KB addition

Record that the private-preview Guardian session, JWT, and API secrets were
rotated locally with atomic mode-`0600` replacement, all seven resolved
running consumers were recreated, the final unexpired pre-rotation session was
rejected by canonical verification, a new session round-tripped, frontend
secret isolation and private reachability remained green, and temporary
secret-bearing evidence was deleted. A first 5-minute sentinel expired before
its post-check and was discarded; only the fresh rerun supplies closure.
Guest exposure remains blocked pending separate provider-side DeepSeek key
rotation/revocation and requalification.

Next action: rotate/revoke the previously exposed DeepSeek private-preview API
credential at the provider boundary and revalidate the admitted DeepSeek lane
before external guest exposure.
