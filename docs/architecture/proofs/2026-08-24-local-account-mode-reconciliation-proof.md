# Local Account-Mode Reconciliation Proof

Proof date: 2026-08-24

## Outcome

**BLOCKED — Google Drive safe-status storage boundary: `google_drive_connection_storage_unavailable` (HTTP 503).**

The qualifying database is structurally single-user under ADR-005, so the
ambient `CODEXIFY_MULTI_USER_ENABLED=true` value was configuration drift. The
ignored local configuration was reconciled to `false` and the backend was
recreated without changing persistent state. The canonical local identity now
successfully reads Connections. The next required protected read stops at the
Google Drive status storage seam because the current `GuardianDB` bootstrap
rejects the live schema as incomplete.

No migration, schema change, ownership rewrite, account conversion, Google
OAuth operation, Google API request, or Google Command Bus operation was
performed.

## Source identity

| Item | Result |
| --- | --- |
| Worktree | `/private/tmp/codexify-google-drive-knowledge` |
| Branch | `codex/implement-google-drive-knowledge-connection` |
| HEAD before task | `d8eb9d3b5c25a832d518eddc4839725cd2ec9257` |
| Tracked worktree before inspection | clean |
| Required ancestors | `c3e5c87d`, `362e748d`, `62ffc307`, `397b4ea5`, `a7592d1e`, and `d8eb9d3b` all reachable from `HEAD` |

## Pre-reconciliation runtime

| Surface | Result |
| --- | --- |
| Supported profile | `v1-local-core-web-mcp` |
| Auth mode | `local` |
| Multi-user flag | `true` |
| Backend health | `/health`, `/health/chat`, and `/api/health/llm` were `200` |
| Previous protected-read boundary | API-key-only requests to Connections, Google Drive status, and actor-resolving Command Bus control returned `401` because multi-user mode required a session/JWT subject |

The qualifying `.env` existed with mode `600`, was ignored by Git, was not
tracked, and was not staged. No secret, credential, URL, or provider setting
was printed during this proof.

## ADR-005 account-mode evidence

### Durable marker inspection

The current public schema has no table whose name records a runtime/account
mode or bootstrap-mode completion. The only migration metadata inspected was
the normal `alembic_version` table. No canonical durable `multi_user` marker
exists.

### Users and authenticated principals

| Store | Count | Safe posture |
| --- | ---: | --- |
| `users` | 1 | canonical `local` / `local` only |
| `authenticated_principals` | 0 | no subject-to-account mapping |

### Ownership diversity

Read-only counts and distinct owner/account identifiers were collected from
every current table with `user_id`, `account_id`, `owner_user_id`,
`owner_account_id`, or `bound_account_id`.

- `projects` contained one row owned by `local`.
- The ADR-005 AccountBoundary stores for chat threads/messages, generated and
  uploaded documents, media, private personas, and memory entries were empty.
- Connections/OAuth (`oauth_connections`), user settings, user profiles,
  account-scoped capability/extension records, hosted-room account records,
  channel records, continuity records, and every other inspected
  owner-bearing table were empty.
- No non-local owner/account identifier was present.

### Classification and ADR-005 determination

**ACCOUNT MODE = SINGLE_USER — ambient
`CODEXIFY_MULTI_USER_ENABLED=true` was configuration drift.**

The evidence shows one canonical account boundary, no active principal mapping,
no distributed ownership, and no durable completed multi-user marker. Changing
the local runtime flag to `false` therefore restores the governing
single-user contract; it is not an ADR-005 multi-user-to-single-user database
transition.

## Conditional runtime reconciliation

After the evidence gate passed, the sole authorized local configuration edit
was made:

```text
CODEXIFY_MULTI_USER_ENABLED=true
CODEXIFY_MULTI_USER_ENABLED=false
```

No other `.env` value changed. `GUARDIAN_AUTH_MODE=local` remained present
exactly once. The three Google Drive OAuth configuration keys were each
present and nonempty exactly once; their values were never emitted.

A plain backend restart retained the pre-existing container environment, so
the backend service alone was then recreated with Compose using
`--no-deps --force-recreate`. This reloaded the ignored `.env` without deleting
volumes, resetting Postgres, wiping Redis, rerunning migrations, seeding a new
user, or changing any database ownership.

After recreation, effective runtime values were:

| Setting | Result |
| --- | --- |
| Auth mode | `local` |
| Multi-user mode | `false` |
| Canonical single-user identity | `local` |

The `.env` remains mode `600`, ignored, untracked, and unstaged.

## Post-reconciliation health

| Endpoint | Result |
| --- | --- |
| `GET /health` | `200` |
| `GET /health/chat` | `200` |
| `GET /api/health/llm` | `200` |
| Backend service | healthy |

## Protected-read results

All requests below used the existing local API-key mechanism inside the
backend environment. The API key itself was never exposed.

| Surface | Result |
| --- | --- |
| `GET /api/connections` | `200`; the request resolved through canonical `local` identity |
| `google_drive` catalog projection | exactly one entry; category `knowledge`; capabilities `content_search`, `content_read` |
| `GET /api/connect/google-drive/status` | **`503`** with safe error `google_drive_connection_storage_unavailable` |
| Command Bus manifest | `200`; `op::google_drive_content_search` and `op::google_drive_content_read` remain visible |
| Actor-resolving Command Bus activation inspection | `500`; not used to invoke a command |
| Subject consistency across all three protected reads | not provable because the Google Drive status read is the first failing required read |

### First failing protected-read boundary

At startup, the current `GuardianDB` loader rejected the live schema because
the ORM-required `notion_connection_credentials` table is absent. The Google
Drive safe-status router requires that `GuardianDB` binding and therefore
returned `503` before any OAuth state or provider call. The Command Bus
actor-control inspection also remained unavailable (`500`) after that failed
binding. This is a schema/migration/runtime-binding blocker, not evidence of a
multi-user account boundary and not authorized for repair in this task.

## Regression checks

| Command | Result |
| --- | --- |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/core/test_multi_user_auth_mode.py` | 3 passed |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/identity/test_request_user_scope_contract.py` | 3 passed |

## Qualification boundary

Google OAuth was not initiated.

Google APIs were not called.

Google Command Bus operations were not invoked.

No connection was created, disconnected, validated, searched, or read. No
credential, token, OAuth state, external content, memory, provenance record,
or document was persisted by this proof.

## Follow-up boundary

Resolve the schema/migration drift that prevents `GuardianDB` initialization
in a separately authorized task. Once that runtime binding is healthy, rerun
the Google Drive safe-status and actor-resolving Command Bus reads under the
already-proven canonical `local` identity. Only after those reads succeed may
the separate Google OAuth qualification gate begin.

ADR impact: aligned with ADR-005 and ADR-069. No new ADR and no release claim
change.
