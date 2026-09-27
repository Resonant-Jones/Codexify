# Generic Authentication Consumer Classification: HOLD

**Date:** 2026-09-27
**Outcome:** HOLD — the remaining consumer map and operator migration set are not frozen
**Branch / baseline HEAD:** `codex/restore-conversation-import-pipeline` / `12899eedc0b6d71a1dd821f26f33cb4533a1cfe0`
**Starting worktree:** only the pre-existing modification to `docs/architecture/proofs/runtime/2026-09-25-public-ingress-auth-boundary-proof.md`

## Purpose and proven baseline

This was a read-only runtime inventory for ADR-092. Explicit
`operator_session` issuance, `require_operator_auth`, and its six Continuity
operator consumers exist. Their PostgreSQL qualification is recorded in
[`2026-09-26-continuity-operator-auth-postgres-proof.md`](2026-09-26-continuity-operator-auth-postgres-proof.md).
This inventory does not change their implementation or qualification.

## Discovery performed

The repository-wide production Python search covered direct references to
`verify_api_key`, `require_api_key`, `require_operator_auth`, `require_auth`,
and `require_user`, excluding tests, docs, and migrations. Route decorators
and router-level dependencies were inspected, including the transitive
`_operator_dependencies` wrapper in
`guardian/routes/account_observability.py`. The same inspection traced the
session-store resolver through `dependencies.py`, `preview_access.py`,
WebSocket auth, dashboard, account observability, and logout. A complete
consumer count was not established because the stop condition below was met.

The decisive current primitive chain is:

| Primitive | Current behavior relevant to the stop |
|---|---|
| `require_api_key` | Wraps `verify_api_key`; in private preview it requires an approved stored account session, while generic remote mode accepts valid signed credentials without exact account purpose. Local mode accepts configured API keys. |
| `get_current_user` | Calls `require_api_key`, then resolves request identity through `get_request_user_id`; it is not an operator-only principal. |
| `require_admin` | Adds `X-Admin-Token`, private-preview account-admin, or bounded local debug authorization. |
| `require_operator_auth` | Accepts configured API-key authority or an exact-purpose `operator_session`; rejects account-purpose signed tokens. |
| `require_service_api_key` | Requires a configured raw service key separately from session authentication on the dashboard. |
| `resolve_session_user_id` | Resolves a Bearer or `gc_session` token by session-store lookup without an account-purpose check. |

## Blocking dual-authority consumer

`guardian/routes/account_observability.py::_operator_dependencies` combines
`Depends(require_api_key)`, `Depends(require_admin)`, and
`Depends(get_current_user)` in one wrapper. These existing routes consume it:

| Function | Route family | Current authority inputs |
|---|---|---|
| `create_operator_invite` | `POST /api/operator/account-observability/invites` | Generic auth, admin gate, current user |
| `list_operator_invites` | `GET /api/operator/account-observability/invites` | Same wrapper |
| `disable_operator_invite` | `POST /api/operator/account-observability/invites/{invite_id}/disable` | Same wrapper |
| `revoke_operator_invite` | `POST /api/operator/account-observability/invites/{invite_id}/revoke` | Same wrapper |
| `trigger_retention_cleanup` | `POST /api/operator/account-observability/retention/cleanup` | Same wrapper |

The cleanup handler itself describes its requirement as an API key plus admin
session. The wrapper passes its resolved current user into invite audit
attribution. ADR-049, section 9, requires an authenticated Guardian human
session and explicit operator/admin authorization for account-observability
operator access, plus a server-held service credential where the dashboard
boundary requires it. The accepted account-observability contract also
defines an operator as a canonical human account with admin authority.

`guardian/routes/dashboard.py::dashboard_snapshot` independently demonstrates
the existing service-key-plus-human-session boundary: its router uses
`require_api_key`, while `resolve_dashboard_viewer` calls
`require_service_api_key` and resolves a stored Guardian account session.

ADR-092 says the operator credential lane does not resolve a canonical user
and defines account-plus-operator credential material in one protected request
as mixed. A mechanical replacement of `require_api_key` with
`require_operator_auth` in the account-observability wrapper could reject its
existing account-session path; retaining a raw service key beside an account
session also requires a precise decision about whether that key is an
operator-lane selector or a distinct service gate. Current accepted contracts
and code do not settle that classification for this migration.

## Classification status

The account-observability operator routes above are **unresolved for the
ADR-092 migration cutover**. Their explicit operator/admin function and
canonical human-account requirement are both established. Assigning only
`operator_only` or only `account_user` would discard one current authority
requirement. This meets the task's stop conditions for a legitimate combined
account/operator boundary and an accepted-contract interaction requiring a
decision.

Therefore no complete consumer table, consumer count, `Operator Migration
Set`, `Account-Purpose Strict Set`, `Local/Dev Preservation Set`, or complete
session-store-resolver set is claimed here. The eight-step migration order in
the task brief remains a proposed sequence, not a frozen execution plan.
Task-event SSE remains a separate account/guest authentication and ADR-091
thread-authorization problem; it was not inspected for implementation or
repaired in this task.

## Required prerequisite

Reconcile ADR-049's human-session/admin/service-key requirements with
ADR-092's account, operator, and mixed-principal rules for the current
account-observability and dashboard boundaries. The decision must say how a
server-held service key is classified, how a canonical human admin is
authenticated and attributed, and which gate is allowed on each current
route. Then rerun the complete generic-auth consumer inventory and freeze its
migration sets. No production, test, configuration, ADR, or public-ingress
receipt was changed for this HOLD.

`PUBLIC_INGRESS_AUTH_BOUNDARY=HOLD` remains unchanged.
