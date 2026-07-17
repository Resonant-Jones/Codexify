# Guardian Dashboard Snapshot Contract

Status: implemented viewer-aware slice for private-preview dashboard use.

This contract defines one authenticated, read-only server projection. It does
not add collaboration persistence, realtime presence, shared notes, mentions,
host collectors, or collaboration tables.

## Route and dual-authority model

`GET /api/dashboard/snapshot` is Guardian-owned and requires the existing
`require_api_key` dependency plus a service API key and an authenticated human
Guardian session. The route is enabled in the local-core and friends/family
supported profiles. It is a projection only; the existing Guardian health and
sensor providers remain the sources of truth.

The two authorities are intentionally distinct:

- Service authority is the configured Guardian API key supplied in
  `X-API-Key`. It proves the trusted service path is allowed to request the
  projection.
- Human authority is the signed `gc_session` (or the same Guardian session
  carried as a bearer token). It determines the current viewer. In
  private-preview mode, Guardian resolves the signed session through the
  approved-email allowlist and its server-mapped `admin`/`guest` role policy.

A valid API key without a valid Guardian session is rejected. A valid Guardian
session without the service API key is rejected. `X-User-Id`, request bodies,
query parameters, and other caller-controlled identity fields never determine
the viewer.

Guardian owns identity and authorization. Codexify.Space transports the signed
session and renders Guardian-owned projections. Codexify.Space must not
maintain a parallel user authority.

Codexify.Space owns client presentation, not account authority: it may render
the bounded viewer projection but must not mint identities, map accounts,
assign roles, or persist a competing account store.

## Response schema

```json
{
  "schema_version": "guardian.dashboard.snapshot.v1",
  "generated_at": "<UTC ISO-8601 timestamp>",
  "source": {
    "service": "guardian",
    "projection": "canonical_health_and_sensor_telemetry"
  },
  "viewer": {
    "user_id": "<canonical Guardian account id>",
    "display_name": "<string|null>",
    "role": "admin|guest",
    "avatar_url": "<string|null>",
    "timezone": "<string|null>"
  },
  "health": {
    "core": {},
    "llm": {},
    "chat": {},
    "heartbeat": {}
  },
  "runtime": {
    "provider": "<string|null>",
    "model": "<string|null>",
    "chat_status": "<string|null>",
    "worker_status": "<string|null>",
    "queue_status": "<string|null>"
  },
  "host": {
    "hostname": "<string>",
    "process_id": 0,
    "containerized": false,
    "telemetry_source": "guardian.sensors.state.Sensors",
    "sensors": {}
  },
  "changes": [],
  "attention": [],
  "orientation": {
    "notes": [],
    "presence": [],
    "mentions": []
  }
}
```

`schema_version` remains `guardian.dashboard.snapshot.v1`. Adding the bounded,
required viewer projection does not change the stable projection family or its
telemetry semantics, so this contract does not require a version increment.

## Viewer provenance and isolation

`viewer.user_id` is the canonical Guardian account identity derived from the
authenticated session. In private-preview mode, it is the normalized approved
email resolved from the signed session; a supplied `X-User-Id` cannot replace
it. Chris's approved session resolves Chris's account and the `admin` role;
Zac's approved session resolves Zac's account and the `guest` role.

`display_name`, `avatar_url`, and `timezone` come only from Guardian's existing
current-user profile seam. If a canonical authenticated account has no profile
row, Guardian reuses that seam's lazy profile creation behavior. A viewer can
receive only the profile for the account derived from that viewer's session.

When private-preview mode is active, `viewer.role` comes from
`guardian.core.preview_access` and its approved-email policy, not a request
field or a caller-selected role. Outside private-preview mode, the canonical
Guardian account role supplies the bounded role value. The response excludes
password hashes, plaintext passwords, session tokens, API keys, allowlist
configuration, raw authorization headers, and private account internals.

`health` is composed from the existing health route handlers and heartbeat
status reader. `host.sensors` is the already-wired `Sensors` provider; this
route must not create a second collector. `attention` contains a bounded
component/status/reason projection for non-healthy health payloads.

`changes` is empty until a canonical persisted change feed is implemented.
The orientation arrays are intentionally empty until collaboration persistence
exists. Their presence in the schema is stable and does not imply shared notes,
realtime presence, or mention delivery.

## Architecture boundary

This is aligned with ADR-039's operator/user boundary and ADR-005's account
boundary invariants. The route is an authenticated Guardian projection with a
viewer context, not a parallel identity service, collaboration system, or
operator-impersonation surface. It does not widen the supported release claim
or imply end-to-end runtime completion from health telemetry.

The `orientation.notes`, `orientation.presence`, and `orientation.mentions`
arrays remain empty. Shared notes, presence, mentions, room membership,
last-seen cursors, collaboration tables, and Codexify.Space frontend integration
remain deferred. Their absence must not be inferred from the viewer projection,
and the viewer projection must not weaken account scoping for threads,
projects, documents, media, or chat.
