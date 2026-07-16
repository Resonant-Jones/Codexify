# Guardian Dashboard Snapshot Contract

Status: implemented first slice for private-preview operator dashboard.

This contract defines one authenticated, read-only server projection. It does
not add collaboration persistence, realtime presence, shared notes, mentions,
host collectors, or collaboration tables.

## Route and ownership

`GET /api/dashboard/snapshot` is Guardian-owned and requires the existing
`require_api_key` authentication dependency. The route is enabled in the
local-core and friends/family supported profiles. It is a projection only;
the existing Guardian health and sensor providers remain the sources of truth.

## Response schema

```json
{
  "schema_version": "guardian.dashboard.snapshot.v1",
  "generated_at": "<UTC ISO-8601 timestamp>",
  "source": {
    "service": "guardian",
    "projection": "canonical_health_and_sensor_telemetry"
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

`health` is composed from the existing health route handlers and heartbeat
status reader. `host.sensors` is the already-wired `Sensors` provider; this
route must not create a second collector. `attention` contains a bounded
component/status/reason projection for non-healthy health payloads.

`changes` is empty until a canonical persisted change feed is implemented.
The orientation arrays are intentionally empty until collaboration persistence
exists. Their presence in the schema is stable and does not imply shared notes,
realtime presence, or mention delivery.

## Architecture boundary

This is aligned with ADR-039's operator/user boundary: the route is an
authenticated operator-owned infrastructure snapshot, not a user identity or
collaboration surface. It does not widen the supported release claim or imply
end-to-end runtime completion from health telemetry.
