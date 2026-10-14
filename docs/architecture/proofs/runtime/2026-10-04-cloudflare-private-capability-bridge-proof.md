# Cloudflare Private Guardian Capability Bridge Proof — 2026-10-05

## Result

**PASS for the bounded CE-02 Worker-to-Guardian capability path.** The
deployed `codexify-edge` Worker reached the exact Guardian health capability
through one Workers VPC Service and the existing VaultNode Cloudflare Tunnel.
The live proof used an isolated branch runtime, which was removed after the
checks. The retained Worker and service fail closed while that proof origin is
absent. This does not prove operation against the canonical private-preview
runtime, change release truth, or establish Beta support.

## Task and baseline

- Task: CE-02 — Establish the Private Guardian Capability Bridge
- Governing architecture: [ADR-099](../../adr/099-cloudflare-edge-platform-boundary.md)
- Governing mesh principle: [ADR-061](../../adr/061-capability-oriented-mesh-architecture.md)
- Branch: `feature/cloudflare-edge-services`
- Starting commit: `cb956c5bb528d964f8ca6e7e16fc77c1f9f23f1b`
- Worker: `codexify-edge`
- Wrangler: `4.147.0`
- CE-02 Worker version: `751dffe7-0936-41c0-850e-75935ff9b31e`
- Deployment date: `2026-10-05` (UTC)

## Private service boundary

- One Workers VPC Service was created: `codexify-guardian-capability`
  (`01a10a40-909e-78a1-93da-3fa98cf98e17`).
- The service is HTTP-only and pins to `127.0.0.1:18081` through existing
  Tunnel `codexify-private-preview`
  (`4ab3913d-eaec-4ecc-aca2-f17adb1ed9da`). No HTTPS port or additional
  destination was configured.
- `codexify-edge` has exactly one VPC Service binding,
  `GUARDIAN_CAPABILITY`. No Workers VPC Network binding was configured.
- The Worker calls only
  `http://guardian-vpc.internal/api/internal/edge/health` with a fresh GET,
  the dedicated `X-API-Key` credential, and its generated
  `X-Codexify-Edge-Request-ID`. Caller URL, path, query, headers, body, and
  credentials do not select or widen the destination.
- Guardian validates only `GUARDIAN_EDGE_CAPABILITY_KEY` for this route. The
  edge credential does not create an account, user, or operator principal and
  is not accepted by the ordinary Guardian service-key verifier. The
  dedicated value was freshly generated, differs from the active preview's
  `GUARDIAN_API_KEY`, and was the same value used by the local proof
  environment and Cloudflare Worker secret.

Cloudflare documentation was rechecked on `2026-10-05`:

- Workers VPC was marked beta and free during open beta; standard Worker
  request/compute pricing applies
  ([pricing](https://developers.cloudflare.com/workers-vpc/platform/pricing/)).
- Creating a VPC Service requires Connectivity Directory Admin; the
  authenticated Wrangler token had `connectivity:admin` and
  `workers_scripts:write` permissions. Account identifiers and email are
  omitted.
- VPC Services pin routing to their configured host/port, while the URL host
  sets only the HTTP `Host` field
  ([VPC Services](https://developers.cloudflare.com/workers-vpc/configuration/vpc-services/)).
- Workers VPC requires `cloudflared` 2025.7.0 or later and `auto` or `quic`
  transport ([Tunnel requirements](https://developers.cloudflare.com/workers-vpc/configuration/tunnel/)).
  The existing client was `2026.8.3`; the local config omits an explicit
  protocol, so the client default `auto` was in effect. Cloudflare documents
  `auto` as selecting QUIC
  ([Tunnel run parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/)).
- Before the proof, the existing tunnel metrics reported four active HA
  connections. Its only public ingress remained
  `preview.codexify.space -> http://127.0.0.1:8081`, with a catch-all `404`.

The active Docker Compose project was `codexify_private_preview`, not this
branch worktree. The origin's Compose labels named
`/Volumes/Dev_SSD/Codexify-main/docker-compose.yml`,
`/Volumes/Dev_SSD/Codexify-main/docker-compose.private-preview.yml`, and the
Scout qualification overlay
`/Volumes/Dev_SSD/Codexify-scout815-auth/f231ef3cf-r2/compose.scout-qualification.yml`.
The backend also had its separate
`/Volumes/Dev_SSD/Codexify-scout815-auth/5836ed986-edge/compose.scout-qualification.yml`
overlay. Both active containers stayed running and unchanged throughout.

The active private-preview origin remained on loopback port `8081` and was
running from a separate checkout with qualification overlays. To avoid
rebuilding or changing that runtime, the proof used an isolated branch Nginx
origin published only on `127.0.0.1:18081`. Branch Guardian code was mounted
read-only; Guardian had no published host port and remained on an internal
Docker network. The isolated app had no database, Redis, user data, model,
filesystem capability, or provider connection. Only Nginx had the second
bridge required for Docker Desktop's loopback-only port publication; no
outbound requests were made.

## Validation and live checks

- Worker tests: `pnpm --filter @codexify/cloudflare-edge test` —
  **15 passed, 0 failed**.
- Focused Guardian and Nginx contract tests — **10 passed, 0 failed**.
- The full two-file Guardian/private-preview test run reported **47 passed,
  3 failed**. The failures are existing LLM catalog tests blocked by invalid
  JSON in `config/whooshd/model-profiles/gemma-4-12b-it-optiq-4bit.json`,
  outside this task's allowlist; the focused CE-02 tests pass.
- Wrangler dry run: `pnpm --filter @codexify/cloudflare-edge deploy:dry-run` —
  **passed** and showed only the single VPC Service binding.
- The package's deploy script succeeded; the deployed Worker version is
  recorded above.
- Container `nginx -t` against the branch Nginx configuration — **passed**.
- Local branch-origin checks: missing, wrong, and ordinary Guardian API keys
  returned `401`; the dedicated key returned a bounded `200`; malformed
  correlation ID returned `400`; non-capability paths and the public host's
  internal route returned `404`.
- The public HTTPS request to
  `https://preview.codexify.space/api/internal/edge/health` returned `401`
  at Cloudflare Access before reaching the origin. At the branch Nginx
  boundary, the same path with `Host: preview.codexify.space` returned `404`
  without reaching Guardian. The untouched canonical origin also returned
  `404` for that path.
- The Worker has only one `GUARDIAN_CAPABILITY` VPC Service binding. The
  service pins one IP, one HTTP port, and the existing Tunnel ID; the internal
  Nginx host proxies only the exact Guardian health path and returns `404`
  for other paths. No VPC Network binding was configured and no VPC Network
  was created by this task.
- Deployed `GET /capabilities/guardian-health` returned `200`,
  `Cache-Control: no-store`, a fresh `X-Codexify-Edge-Request-ID`, and exactly
  `{"service":"codexify-edge","capability":"guardian.health","status":"ok","upstream":"guardian"}`.
  The caller supplied query/auth/cookie/API-key data, none of which was
  forwarded. `GET /healthz` remained `200`; `POST
  /capabilities/guardian-health` returned `405` with `Allow: GET`; an
  unrelated route returned `404`.
- Live correlation ID `de2460af-4ab1-44d5-b8f1-ffb37a9f9485` matched the
  response header, the sanitized Wrangler tail record, and Guardian's
  `event_type=guardian_edge_capability_request` log event with
  `status_code=200`.
- The dedicated secret was absent from Guardian logs. Its value is omitted
  from this proof and remains only in the ignored mode-`0600`
  `.env.private-preview` runtime environment and Cloudflare Worker secret
  storage.
- After removing the isolated origin, the deployed capability returned
  `502` with `guardian_capability_unavailable`; it did not fall back to a
  public or alternate route.
- The untouched canonical origin still returned `200` from `/health` and
  `404` from `/api/internal/edge/health` after proof teardown.

An initial request using Python's default user agent received Cloudflare error
1010 before reaching the Worker. Repeating the request with a browser user
agent reached the Worker; the successful request was independently confirmed
in the Wrangler tail and Guardian log.

## Authority, spend, and runtime invariants

- Guardian remains the authentication, authorization, and routing authority.
  VaultNode remains canonical runtime/audit authority; Postgres remains
  canonical application authority. R2, Redis, account/session state, and
  application data were not accessed.
- `ZERO_NON_INFERENCE_SPEND` remains unchanged. No paid plan, credit, overage,
  or paid feature was enabled. Workers VPC was documented as free during its
  open beta on 2026-10-05; standard Worker request/compute plan terms still
  apply to the existing Worker. Billing settings and account billing history
  were not inspected or changed.
- No Cloudflare Tunnel configuration, Compose file, active private-preview
  container, qualification overlay, public route, `00-current-state.md`,
  supported path, or release claim changed.
- CE-02 created one Workers VPC Service, its one Worker binding, and one
  Worker secret. It created no Workers VPC Network or extra Tunnel. No R2,
  database, Redis, model, queue, workflow, AI Gateway, Turnstile, Web Search,
  or other Cloudflare resource was created.
- The two isolated proof containers and their two task-created Docker
  networks were removed after proof. The existing Tunnel process and
  canonical origin remain untouched. The VPC Service, Worker binding, and
  Worker secret remain configured; while the isolated target is absent, the
  public capability endpoint fails closed as verified above.

## Limitations and follow-up

- This proves transport and Guardian authentication against an isolated
  branch runtime only. The live canonical private-preview runtime remains
  unintegrated and must not be inferred from this proof.
- No application, account, Project, Thread, memory, model, database, Redis,
  filesystem, or operator data is exposed.
- No runtime or release claim changed; `docs/architecture/00-current-state.md`
  remains authoritative.
- CE-03 is the next eligible separate Campaign slice. CE-02 completion does
  not authorize it.
