# Localhost Remote Session Qualification Proof

Proof date: 2026-08-24

## Outcome

**BLOCKED — NO LOCALHOST REMOTE LOGIN PATH**

The qualifying backend is healthy and remains in `remote` authentication
mode, but its active supported profile quarantines the normal user-auth router.
The localhost frontend consequently renders the existing registration/login UI
but receives `404` for its normal registration request. No existing supported
browser login path can mint a user-scoped remote session for
`http://localhost:8888` under this profile.

This is a supported-profile/auth-route registration boundary. It is not a
Google Drive, OAuth, provider, Connections, or Command Bus failure.

## Source identity

- Worktree: `/private/tmp/codexify-google-drive-knowledge`
- Branch: `codex/implement-google-drive-knowledge-connection`
- HEAD before this proof: `397b4ea5f295b3d793b85148951c1c549ee97ca4`
- Tracked working tree before this proof artifact: clean.
- Required ancestry was confirmed for `c3e5c87d`, `362e748d`, `62ffc307`, and
  `397b4ea5`.

## Preserved runtime posture

| Surface | Result |
| --- | --- |
| `GUARDIAN_AUTH_MODE` | `remote` |
| `GET /health` | `200` |
| `GET /health/chat` | `200` |
| `GET /api/health/llm` | `200` |
| Compose backend | running and healthy |

The normal Vite client was served at `http://127.0.0.1:5173` with its API
proxy targeted at `http://localhost:8888`. Its API-key environment values
were blank, so it did not supply an API-key fallback. No authentication mode,
environment, source, profile, cookie policy, manual actor header, or session
credential was changed, copied, or exposed.

## Canonical flow discovered

The current frontend calls `POST /auth/login` through its `/api` client path,
receives a session token from the normal auth router, and stores it in browser
session storage for `Authorization: Bearer` requests in remote mode. The
registration view similarly calls `POST /auth/register` before redirecting to
login.

Source registration in `guardian/guardian_api.py` would include both the auth
router and its `/api` router under the `auth` router label. The same startup
helper first asks the active supported-profile manifest for that label; any
label absent from the manifest is `quarantined` and is not registered.

The active `v1-local-core-web-mcp` profile does not admit `auth`. Live
OpenAPI therefore exposes neither `/auth/login` nor `/api/auth/login`, and
the user-controlled normal registration submission returned `404`. No
credentials from that submission were retained in this proof.

The published `/auth/session` and `/auth/session/cookie` endpoints are admin
API-key exchanges, not the normal user login/session bootstrap. Using either
would require the very API-key authority this qualification explicitly does
not permit, so neither was used.

## Required authenticated reads

| Required surface | Result |
| --- | --- |
| `GET /api/connections` | not attempted: no legitimate localhost remote session exists |
| `GET /api/connect/google-drive/status` | not attempted after the session-establishment blocker |
| `GET /api/guardian/commands/manifest` | not attempted after the session-establishment blocker |
| Same-subject consistency | not provable: no user-scoped local session was minted |

## Qualification boundary

Google OAuth was not initiated. No Google API was called, and no Google Drive
or Docs object was searched or read. No provider credential, OAuth state,
content, memory, document, embedding, graph, sync, or Command Bus record was
created.

Connections remains a read-only projection and Command Bus remains the
authority for agent-invocable operations. Server-owned credential and
provenance boundaries were unchanged.

## Validation

| Check | Result |
| --- | --- |
| Required source ancestry | pass |
| Backend health and remote-auth posture | pass |
| Normal localhost frontend route | pass; registration/login UI rendered |
| Normal user auth router registration | blocked; quarantined by active profile |
| Normal registration request | blocked; `404` |
| API-key/session fallback | not used |
| OAuth/provider execution | not attempted |
| Source/config/test modification | none |

`git diff --check` passes for this proof artifact.

## Next gate

This proof task cannot change the auth system. A separate authorized
architecture/implementation decision must either admit the normal auth router
to the supported localhost remote profile or define an existing supported,
user-scoped session bootstrap path that preserves the same authentication and
authority contracts. Only then can the three read-only authenticated checks
resume, followed by the separately authorized Google OAuth qualification.

ADR impact: none. Release truth is unchanged.
