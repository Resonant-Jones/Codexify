# 2026-09-01 Private-Preview Cloudflare Ingress Provisioning Proof

## Conclusion

`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_BLOCKED`

Cloudflare ingress provisioning itself is live: the dedicated named Tunnel is
healthy, canonical DNS resolves, TLS succeeds, one exact-email operator policy
protects the hostname through One-time PIN, anonymous callers cannot reach the
application, and the authenticated operator completed the Access login.

The complete ingress qualification is nevertheless blocked. After Access
admission, the browser receives the Codexify HTML shell but renders a blank
page because the frontend module request `/api/codex.ts` is routed by the
private-preview Nginx origin to Guardian's `/api/` upstream and returns HTTP
404. The module exists at `frontend/src/api/codex.ts` and is imported through
the frontend `@/api/codex` alias. This is a deterministic application-origin
routing defect, not a Cloudflare authentication failure.

Per task scope, no application, Vite, or Nginx behavior was repaired. Guardian
session login, public authenticated health, provider execution, and persistence
were not claimed. No guest account was provisioned or admitted. The
friends-and-family canary remains closed pending a separate atomic defect fix
and rerun of the remaining gates.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: implementation plus live proof
- Evidence posture: live-runtime proven through Cloudflare Access admission;
  fail-closed at authenticated application bootstrap
- Execution date: 2026-09-01 local time
- Source branch and pre-proof commit: local `main` at
  `e0f7414a9d3f5b4420983194e365dba856ca75ad`
- Runtime project: `codexify_private_preview`
- Canonical hostname: `preview.codexify.space`
- Sole application origin: `http://127.0.0.1:8081`
- Cloudflare account and zone identities: operator-supplied values were
  verified through authenticated API responses and are not reproduced here
- API token: read only from the operator's mode-`0600` file; never printed,
  copied into Git, or placed in a process argument

The unrelated pre-existing deletion of
`docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md` remained untouched and
unstaged.

## Provisioned Cloudflare state

| Surface | Result | Bounded evidence |
| --- | --- | --- |
| Named Tunnel | PASS | One locally managed Tunnel named `codexify-private-preview` was created. Cloudflare reported `healthy` with four live QUIC connections. |
| Local credentials | PASS | The Tunnel credential and config are outside Git under `/Users/chriscastillo/.cloudflared`; directory mode is `0700` and both files are mode `0600`. No `cert.pem`, quick Tunnel, or API token copy was created. |
| Ingress rules | PASS | `preview.codexify.space` matches only `http://127.0.0.1:8081`; a nonmatching hostname selects the terminal `http_status:404` rule. `cloudflared tunnel ... ingress validate` passed. |
| Canonical DNS | PASS | Exactly one proxied CNAME for `preview.codexify.space` targets the dedicated Tunnel. Public A resolution succeeded. |
| Access application | PASS | Exactly one self-hosted application named `Codexify Private Preview` protects the canonical hostname. It auto-redirects to exactly one allowed IdP: One-time PIN. |
| Access policy | PASS | Exactly one `allow` policy contains exactly one exact-email rule sourced from the existing private-preview administrator allowlist. No wildcard, Everyone, domain, bypass, or service-token rule exists. |
| Anonymous denial | PASS | `/`, `/health`, `/health/chat`, and `/api/health/llm` each returned HTTP 302 to Cloudflare Access without exposing application content. |
| Approved operator Access login | PASS | The operator completed OTP in the browser. The final URL was the canonical hostname and the document title was `Codexify`, proving successful Access admission. No email, OTP, cookie, or credential was captured. |

Cloudflare's Zero Trust dashboard showed One-time PIN and Cloudflare as built-in
identity providers. The account identity-provider list API returned an empty
array and rejected an attempted explicit OTP creation with error `1010`; no OTP
resource was created by that API attempt. Dashboard state and successful live
OTP authentication supersede that incomplete list response.

## Preservation and isolation proof

- Authenticated pre-mutation inventory found zero intended Tunnels, zero
  preview DNS records, and zero Access applications.
- The zone had eight unrelated DNS records before provisioning and nine total
  afterward.
- Normalized authenticated before/after hashes for every DNS record other than
  `preview.codexify.space` were identical:
  `0f4d44febb90c4e3f197eccd20de841c21b1afa92f542a2e65e67a7f302217b7`.
- Apex and `www` records remained present.
- Live Docker publication showed only
  `127.0.0.1:8081->8080/tcp` for the private-preview origin. Guardian, Vite,
  Postgres, Redis, Neo4j, workers, and provider services had no non-loopback
  host publication.
- No unrelated Docker project or Cloudflare resource was changed.

## Local runtime prerequisite

Docker Desktop was `running`. The scoped Compose bring-up restored the
`codexify_private_preview` project without rebuilding images or touching
unrelated projects. The canonical static validator passed 39 checks and the
reachability validator passed before Cloudflare mutation. Backend, database,
Redis, and Neo4j were healthy when the authenticated-browser defect was
confirmed. The coding worker was observed restarting late in the proof; it was
not diagnosed because the earlier frontend routing defect already terminated
the canary and provider execution was not attempted.

## Authenticated application blocker

The following live facts establish the defect:

1. The operator completed Cloudflare OTP and the browser reached
   `https://preview.codexify.space/` with document title `Codexify`.
2. The document reached `readyState=complete`, but `#root` remained empty and
   the rendered viewport was blank.
3. Origin access logs recorded `GET /api/codex.ts` as HTTP 404 with a frontend
   module referrer.
4. A direct loopback request to
   `http://127.0.0.1:8081/api/codex.ts` also returned HTTP 404, excluding
   Cloudflare as the cause.
5. `frontend/src/api/codex.ts` exists, and live frontend modules import it as
   `@/api/codex`.
6. `docker/private-preview/nginx.conf` sends every `/api/` path to Guardian,
   while only the remaining `/` paths reach Vite. The Vite source alias
   therefore collides with the origin's API routing prefix.

The browser also reported a failed Vite HMR WebSocket attempt to
`localhost:5173`. That development-only HMR warning is recorded but is not used
as the primary blocker because the missing source module is independently
proven by the 404 and empty application root.

## Required next atomic prerequisite

Create a separately authorized defect task to remove the Vite source-module
path collision at the private-preview origin without weakening the canonical
`/api/` Guardian boundary or exposing Vite directly. That task must prove the
normal browser application mounts through `preview.codexify.space` while
Guardian API routes continue to reach Guardian and internal services remain
unpublished.

After that fix is committed and deployed, resume this proof without creating
duplicate Cloudflare resources. Reconcile the existing named Tunnel, DNS,
Access application, and exact-email policy; then prove Guardian session
layering, authenticated public health, server-secret absence, fallback 404,
and connector health. Guest provisioning remains a later task.

## Gates not run or not satisfied

- Guardian login behind authenticated Cloudflare Access: BLOCKED by blank
  frontend.
- Guardian-without-session denial after Access: NOT PROVEN.
- Authenticated public root and health responses: NOT PROVEN.
- Browser server-secret absence: NOT RE-PROVEN after Access because the
  application did not mount.
- Provider execution and persistence: OUT OF SCOPE for this ingress task and
  not attempted.
- Reboot/login connector resumption: NOT CLAIMED; the connector runs in the
  foreground and no persistence mechanism was installed.

## Validation results

- `docker desktop status` — PASS, `running`.
- Scoped `docker compose ... up -d --no-build` — PASS.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static` — PASS, 39 checks.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` — PASS.
- Token, account, zone, Tunnel, DNS, Access-app, and identity-provider inventory — PASS for authorized reads.
- Cloudflare Zero Trust dashboard OTP inspection — PASS; OTP visible.
- `cloudflared tunnel --config ... ingress validate` — PASS.
- Canonical and fallback `cloudflared ... ingress rule` checks — PASS.
- Cloudflare Tunnel API health — PASS, healthy with four connections.
- Authenticated DNS preservation comparison — PASS, exact hash match.
- Anonymous external route matrix — PASS, four Access redirects.
- Approved operator OTP login — PASS.
- Authenticated Codexify render — FAIL, empty root and blank viewport.
- Loopback `/api/codex.ts` — FAIL as expected for the diagnosed collision,
  HTTP 404.
- `python3 scripts/validate_docs.py` — PASS after receipt update.
- `git diff --check` — PASS after receipt update.

## ADR impact

Aligned with ADR-005, ADR-039, ADR-040, ADR-041, ADR-042, ADR-049, and
ADR-069. No new ADR is required. The Cloudflare resources implement the
accepted single-origin and layered-authentication boundary. The failed result
does not widen the release posture or establish a new identity, telemetry,
provider, or support model.

## Documentation follow-through

Only this proof receipt is updated. `docs/Ops/private-browser-preview.md`
remains unchanged because the task permits that runbook update only after
`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_PROVEN`.

## Axis KB addition

Record that Cloudflare provisioning reached a healthy named Tunnel, canonical
proxied DNS, exact-email OTP Access policy, anonymous denial, and successful
operator OTP admission. The authenticated application then failed closed on a
Vite-source/Guardian-API path collision: `/api/codex.ts` was proxied to Guardian
and returned 404, leaving the React root empty. No application repair, guest
admission, provider claim, persistence claim, or public Beta claim followed.
