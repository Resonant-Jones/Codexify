# C08-T002 Endpoint Health Proof: Whoosh'd Configuration & Health-Check Semantics

## Gate Decision

**`go`** — C08-T003 may proceed by name only.

## Scope

This proves endpoint configuration and health-check semantics only. It does **not** prove model inventory, context fidelity, system identity delivery, or operator diagnostics. It does **not** alter runtime behavior.

## Endpoint Configuration Map

| Element | Source | Value | Consuming Code |
|---------|--------|-------|----------------|
| Base URL | `WHOOSHD_HOST` + `WHOOSHD_PORT` | `http://{host}:{port}` | `WhooshdSidecar.base_url` property |
| Host config | Settings | User-configurable | `whooshd_sidecar.py:88` |
| Port config | Settings | User-configurable | `whooshd_sidecar.py:89` |
| Managed mode | `WHOOSHD_MANAGED` | `False` default | `whooshd_sidecar.py:93` |
| Vendor check | `LOCAL_PROVIDER_VENDOR` | `"whooshd"` required | `whooshd_sidecar.py:97` |

## Health-Check Map

| Element | Value | Source |
|---------|-------|--------|
| Probe 1 | `GET /health` (HTTP) | `whooshd_sidecar.py:107` |
| Probe 2 | `GET /health/runtime` (JSON) | `whooshd_sidecar.py:116` |
| Probe 3 | `GET /v1/models` (JSON) | `whooshd_sidecar.py:143` |
| Probe 4 | `GET /api/tags` (JSON) | `whooshd_sidecar.py:151` |
| Timeout | 5.0 seconds | `whooshd_sidecar.py:104` |
| Success criteria | All probes return 200 | `whooshd_sidecar.py:106-155` |
| Failure criteria | Connection refused → OFFLINE; non-200 → ERROR | Test-proven |
| Polling | `detect()` called on demand; no auto-poll loop | Source-verified |
| Lifecycle | `Ownership.NONE` / `EXTERNAL` / `MANAGED` tracked by session_id + PID | `whooshd_sidecar.py` |

## Truth Table

| Claim | Status |
|-------|--------|
| Endpoint source known | `true` |
| Endpoint override known | `true` |
| Health probe path known | `true` |
| Success criteria known | `true` |
| Failure criteria known | `true` |
| Timeout semantics known | `true` |
| Lifecycle ownership known | `true` |
| Endpoint health proven without real daemon | `true` |
| Model inventory proven | `not true` |
| Context fidelity proven | `not true` |
| System identity delivery proven | `not true` |
| Operator diagnostics proven | `not true` |
| Cloud fallback prevented at this seam | `not true` (not tested) |

## Boundary Table

| Boundary | Status |
|----------|--------|
| Endpoint availability is not model inventory proof | Explicit |
| Model inventory proof is not context fidelity proof | Explicit |
| Context fidelity proof is not execution authority | Explicit |
| Health-check success is not release support | Explicit |
| Sidecar lifecycle support is not provider routing proof | Explicit |
| Sidecar launch support is not prompt/context proof | Explicit |
| Local-only posture must not silently fall back to cloud | Explicit |

## Gap Register

| Gap | Evidence | Blast Radius | Proposed Task |
|-----|----------|-------------|---------------|
| Model inventory not verified against preset | `detect()` returns `/v1/models` data but no cross-check with `WHOOSHD_MODEL` | Operator may see wrong model | C08-T003 |
| Context fidelity not tested at call boundary | No message payload verification exists | Model may receive empty context | C08-T004 |
| System identity not verified in Whoosh'd messages | No identity marker injection verified | Model has no Codexify identity | C08-T004 |
| Operator cannot see Whoosh'd status | Status object is internal only | Operator blind to runtime state | C08-T005 |

## Risk Register

| Risk | Evidence | Mitigation (future task) |
|------|----------|-------------------------|
| Endpoint configured but not verified at runtime | Tests mock; real endpoint may differ | C08-T002 integration test (deferred) |
| Model ID mismatch between preset and runtime | No cross-check exists | C08-T003 model inventory proof |
| Cloud fallback possible from other provider paths | Not tested at this seam | C08-T002 cloud-fallback test (deferred) |
| Health success interpreted as full readiness | `READY` state after runtime probe | Explicit boundary documentation |

## Test Evidence

| Test file | Count | Coverage |
|-----------|-------|----------|
| `tests/providers/test_whooshd_endpoint_health_semantics.py` | 16 | Endpoint config, managed mode, vendor check, health failure (offline, error), probe order, runtime state, stub runtime, model inventory population, no real process/network, health ≠ model inventory proof |

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C08-T003: Prove Whoosh'd model inventory identity semantics`
