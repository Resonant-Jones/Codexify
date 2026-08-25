# Google Drive / Docs Remote-Auth Gate Proof

Proof date: 2026-08-24

## Outcome

**BLOCKED — REMOTE AUTH CONNECTIONS ACCESS**

The qualifying backend is healthy and correctly remains in remote-auth mode.
An existing legitimate Codexify remote session was available in Chrome for a
private deployment, but that deployment advertises Connections as unavailable
in its runtime profile. It therefore cannot establish authenticated
Connections access for the local qualifying backend.

The Chrome browser client also blocked direct, read-only navigation to both
the private deployment's Connections route and the qualifying
`localhost:8888` Connections route before an HTTP request could be issued.
Consequently, this proof has no authenticated HTTP status for the qualifying
Connections route and makes no claim that the session was invalid or that the
backend rejected it.

This is an authentication-access boundary, not a Google Drive implementation,
OAuth, provider, or Command Bus failure.

## Source identity

- Worktree: `/private/tmp/codexify-google-drive-knowledge`
- Branch: `codex/implement-google-drive-knowledge-connection`
- HEAD before this proof: `e96ca618d2f95abc419c5ec1020a8c149519bf4c`
- Tracked working tree before this proof artifact: clean.
- The existing Chrome session was used only through its normal browser/UI
  path. No cookie, bearer token, session identifier, JWT, password, or
  authorization header was read, copied, printed, or committed.

## Preserved runtime posture

Bounded live checks against the qualifying local Compose runtime reported:

| Surface | Result |
| --- | --- |
| `GUARDIAN_AUTH_MODE` | `remote` |
| `GET /health` | `200` |
| `GET /health/chat` | `200` |
| `GET /api/health/llm` | `200` |
| Compose backend | running and healthy |

`GUARDIAN_AUTH_MODE` was not modified. No Compose override, authentication
middleware change, manual actor injection, session manufacture, or local
API-key fallback was used in this task.

## Existing remote-session check

Chrome contained an already authenticated Codexify UI session for a private
remote deployment. The UI rendered the account-scoped thread workspace,
which establishes that the existing session is active for that deployment
without exposing an authenticated subject identifier.

In that same authenticated UI, the Settings > Connectors view reported:

```text
Connections are unavailable in this runtime profile.
```

That is a capability/profile result for the private deployment. It is not a
successful `GET /api/connections` projection for the qualifying local runtime,
and it must not be treated as evidence that the canonical `google_drive`
entry is visible there.

## Authenticated-route results

| Required surface | Result |
| --- | --- |
| `GET /api/connections` on qualifying `localhost:8888` | blocked before HTTP: Chrome client blocked direct route navigation; no session credential was extracted or replayed |
| Canonical `google_drive` projection | not reached |
| Google Drive setup/status `GET /api/connect/google-drive/status` | not attempted after the first protected-surface blocker |
| Command Bus manifest `GET /api/guardian/commands/manifest` | not attempted after the first protected-surface blocker |
| Subject consistency across the three surfaces | not provable; no cross-surface authenticated response exists |

A matching direct navigation to the private deployment's Connections route
was also blocked by the browser client before HTTP. This prevents a false
inference from either a missing route or an unknown server response.

## Qualification boundary

Google OAuth was not initiated.

No Google provider API was called. No Google Drive or Google Docs object was
searched or read. No OAuth state, provider credential, token, content,
memory, document, embedding, graph, sync, or Command Bus record was created.

## Scope and authority boundaries

- The active remote authentication/current-user boundary was preserved.
- Connections remained a read-only projection; it was not used as an RPC
  router or execution owner.
- Command Bus authority was not bypassed or exercised.
- No implementation, test, migration, checked-in configuration, or release
  documentation file changed.
- ADR impact: none. The task is aligned with the existing authority and
  credential boundaries in ADR-071, ADR-072, and ADR-075.
- Release truth is unchanged.

## Validation

| Check | Result |
| --- | --- |
| Qualifying Compose backend health | pass |
| Qualifying health endpoints | pass; all three returned `200` |
| Active auth mode inspection | pass; `remote` |
| Existing private remote session | pass for its own browser/UI runtime |
| Authenticated qualifying Connections projection | blocked before HTTP |
| Provider setup/status authentication | not reached |
| Command Bus authentication | not reached |
| OAuth/provider execution | not attempted |
| Credential/session containment | pass |
| Source/config/test modification | none |

## Next gate

Establish a legitimate existing remote session scoped to the qualifying local
backend through the product's normal remote-login client path, without
changing `GUARDIAN_AUTH_MODE` and without exposing the credential to this
task. Then repeat the three safe authenticated reads in this order:

1. `GET /api/connections` and verify the `google_drive` Knowledge projection;
2. `GET /api/connect/google-drive/status` and record the pre-OAuth safe state;
3. `GET /api/guardian/commands/manifest` and verify Command Bus access under
   the same server-derived subject.

Only after those three reads pass may the separately approved Google Drive
live qualification resume at OAuth initiation.
