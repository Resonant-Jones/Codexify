# Cloudflare Edge Worker Runtime Proof — 2026-10-04

## Result

**PASS for the minimal CE-01 public EdgeNode surface.** The deployed Worker
serves only a static health endpoint and default-deny responses. This proves
the CE-01 architecture boundary; it does not establish Beta support or any
later Campaign capability.

## Task and baseline

- Task: CE-01 — Establish the minimal Cloudflare Worker EdgeNode
- Governing architecture decision: [ADR-099](../../adr/099-cloudflare-edge-platform-boundary.md)
- Branch: `feature/cloudflare-edge-services`
- Starting commit: `deab6332f1ec7b0747806df2246c72e4390fc4a2`
- Worker: `codexify-edge`
- Wrangler: `4.147.0`

## Deployment

- Result: Wrangler upload and deployment succeeded.
- Deployment time: `2026-10-05T01:47:07Z` (UTC; local task date was 2026-10-04).
- `workers.dev` endpoint: <https://codexify-edge.codexify-cloudflare-edge.workers.dev>
- Deployed version: `403acdd7-f8ba-4adb-a138-f8e71c3a648c` (100% traffic).
- The first TLS probes failed while the newly enabled hostname propagated;
  HTTPS checks succeeded afterward. No alternate origin was used.
- Wrangler identity check returned `loggedIn: true` for one standard account.
  Account identifiers, email, and credentials are omitted.

## Local validation

- `pnpm --filter @codexify/cloudflare-edge test`: **7 passed, 0 failed**.
- `pnpm --filter @codexify/cloudflare-edge deploy:dry-run`: **passed**;
  upload size 1.92 KiB, gzip 0.86 KiB; no bindings found.

## Deployed HTTPS checks

Two `GET /healthz` requests returned HTTP 200, the expected body, and
`Cache-Control: no-store`:

```json
{"service":"codexify-edge","role":"edge_node","status":"ok","canonical":false}
```

| Request | HTTP result | `X-Codexify-Edge-Request-ID` |
| --- | --- | --- |
| Health request 1 | 200 | `ead965d7-5603-47af-83a2-54168301960c` |
| Health request 2 | 200 | `20bba1e5-925e-4a33-bb0c-a2a931f08f42` |

The IDs differ. `GET /does-not-exist` returned `404` with
`{"error":"not_found"}`. `POST /healthz` returned `405`,
`Allow: GET`, and `{"error":"method_not_allowed"}`.

The Worker source contains no `fetch()` proxy path or origin configuration;
the local test also replaces `fetch` with a spy and proves it is not called
for an unknown route. **No Guardian/origin connectivity exists yet.**

## Logging and correlation

While `wrangler tail codexify-edge --format json` was active, the second HTTPS
health request emitted this structured application log record. The
`edge_request_id` matches the response header above:

```json
{"event":"codexify_edge_request","edge_request_id":"20bba1e5-925e-4a33-bb0c-a2a931f08f42","method":"GET","pathname":"/healthz","status":200,"cf_ray":"a458ca65ccea7b6f","colo":"MIA"}
```

The Worker logs only the event name, generated EdgeNode ID, method, pathname,
status, and validated Cloudflare Ray/colo metadata. Wrangler invocation-log
persistence is disabled; the proof retains only the structured application
record.

## Spend and authority invariants

- `ZERO_NON_INFERENCE_SPEND`: no paid plan, paid capability, billing
  activation, overage setting, secret, or paid resource was enabled by this
  task. Deployment completed without a payment or plan-upgrade prompt. The
  Worker has no bindings. Wrangler's identity command does not report any
  pre-existing account subscription details, so this proof makes no claim
  about account billing history outside this task.
- Only the `codexify-edge` Worker was deployed for CE-01. No custom domain,
  R2 bucket, Workers VPC, AI Gateway, Turnstile, Queue, Workflow, database,
  or other Cloudflare service was created.
- Guardian remains the orchestration and authorization authority; VaultNode
  remains canonical runtime/audit authority; Postgres remains canonical
  application authority. The Worker stores no user state and handles no
  application content.
- No Tunnel configuration, Docker Compose path, supported Beta boundary, or
  release claim changed. `docs/architecture/00-current-state.md` was not
  modified.

## Known limitations and next slice

- Free-quota exhaustion was not induced; no quota override or paid fallback
  was configured.
- This Worker has no application, Guardian, Tunnel, storage, provider, or
  private-network integration.
- CE-02 remains a separate task. CE-01 does not authorize or implement it.
