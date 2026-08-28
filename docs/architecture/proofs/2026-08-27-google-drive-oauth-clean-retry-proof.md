# Google Drive OAuth clean retry proof

## Result

`BLOCKED — FRESH GOOGLE OAUTH BROWSER HANDOFF FAILED`

## Scope and source

- Worktree: `/Volumes/Dev_SSD/Codexify-main`
- Branch at execution: `main`
- This receipt covers one bounded retry after the prior OAuth handoff loss.
- ADR impact: aligned with ADR-069, ADR-071, and ADR-075; no new ADR.
- Release-truth impact: none.

## Pre-state

Before retry invalidation, the standard Compose backend was healthy and had
effective local single-user configuration:

- `GUARDIAN_AUTH_MODE=local`
- `CODEXIFY_MULTI_USER_ENABLED=false`
- Google Drive OAuth client ID and replacement secret present (values not
  recorded)
- redirect URI configured for the canonical local callback

The qualifying database remained at `9c66e490a42b`, with one user and one
project. Its sole `google_drive` / `node_local` OAuth row was `pending`, had
the exact two approved read-only scopes, and had neither encrypted access nor
encrypted refresh credentials. Active legacy `google` authority was zero.

## Abandoned-flow disposition

The backend was recreated with:

```text
docker compose up -d --no-deps --force-recreate backend
```

The database container identity remained unchanged. The newly created backend
became healthy, retained the effective local single-user and non-secret Google
configuration checks, and the database row remained one tokenless `pending`
row. This invalidated the abandoned process-local PKCE nonce/verifier state
without database cleanup or schema work.

`ABANDONED_PKCE_FLOW_INVALIDATED = PASS`

## Fresh-flow result

Exactly one new `POST /api/connect/google-drive/start` was issued after the
backend-only recreation. The request was made through the normal local API-key
path. The local handoff validation failed before the returned authorization
URL could be transferred to Chrome: its runtime did not provide the URL parser
used by that handoff layer.

The authorization URL, signed state, verifier, authorization code, client
secret, and token material were not printed, saved to a repository file,
included in this receipt, or committed. The flow was not presented to a
browser. Consequently no Google consent, authorization-code issuance, token
exchange, bounded Drive validation, Drive search, Docs read, Google API call,
or Command Bus invocation occurred.

No second `/start` was issued. The canonical row remained the sole
`google_drive` / `node_local` row, was still `pending`, and still had no
encrypted access or refresh credential. The backend process remained running;
the flow cannot be recovered safely without a new, separately authorized retry.

## Post-stop containment

- Database revision: `9c66e490a42b`
- Google Drive row count: `1`
- Google Drive state: `pending`
- Encrypted access credential present: `false`
- Encrypted refresh credential present: `false`
- Active legacy `google` authority: `0`
- Database migration or DDL: none
- Provider content persistence: none
- Current-state/ADR/implementation changes: none

## Next gate

Authorize a new bounded retry only after the current pending in-memory flow is
invalidated with another backend-only recreation. The replacement handoff must
use a pre-validated direct browser-navigation mechanism that holds the returned
authorization URL only in ephemeral process memory and never emits it to the
terminal, proof artifact, repository, or shell history.
