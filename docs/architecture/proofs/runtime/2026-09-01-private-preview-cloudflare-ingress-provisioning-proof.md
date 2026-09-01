# 2026-09-01 Private-Preview Cloudflare Ingress Provisioning Proof

## Conclusion

`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_PROVEN`

The existing private-preview Cloudflare boundary and the corrected local
single-origin router are live-runtime proven. Anonymous requests stop at
Cloudflare Access. An Access-admitted browser reaches a distinct Guardian
login boundary, a normal Guardian session reaches the Codexify workspace, the
Vite module graph loads through the canonical hostname, semantic `/api/`
requests remain Guardian-owned, and Cloudflare Tunnel reports healthy with
four connections.

This result qualifies ingress only. It does not admit a guest, prove provider
execution or persistence, install connector resumption, widen the allowlist,
or establish a public Beta claim. The friends-and-family canary remains a
separate atomic proof.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: bug fix, contract test, and live proof
- Evidence posture: live-runtime proven for private-preview ingress
- Execution date: 2026-09-01 local time
- Source branch and pre-fix commit: local `main` at
  `3248ccb980141c8136b10813ad0978e8b188d753`
- Runtime project: `codexify_private_preview`
- Canonical hostname: `preview.codexify.space`
- Sole application origin: `http://127.0.0.1:8081`
- Cloudflare resources: reconciled read-only; none were created, updated, or
  deleted during this corrective proof
- API token: read only from the operator's mode-`0600` file and never printed,
  copied into Git, or placed in a process argument

The unrelated pre-existing deletion of
`docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md` remained untouched and
unstaged.

## Blocked lineage and corrective change

The preceding run proved the named Tunnel, DNS, Access OTP policy, anonymous
denial, and operator Access admission, but stopped with
`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_BLOCKED`. Nginx sent
`/api/codex.ts` to Guardian, which returned HTTP 404; the browser's React root
therefore remained empty.

The corrective classifier is deliberately narrow:

```nginx
location ~ ^/api/.*\.(?:ts|tsx|js|jsx)$ {
    proxy_pass http://frontend:5173;
    # bounded proxy headers omitted here
}

location /api/ {
    proxy_pass http://guardian_backend;
    # Guardian API headers omitted here
}
```

The regex admits only `/api/` paths ending in `.ts`, `.tsx`, `.js`, or `.jsx`
to Vite. `proxy_pass` has no URI suffix, so the full path and query string are
preserved. The ordinary `/api/` prefix has no `^~`, allowing the bounded regex
to win; all other `/api/**` traffic remains Guardian-owned. There is no
backend-404 fallback to Vite.

## Local route-ownership proof

After `nginx -t` passed, only the active `private-preview-origin` Nginx process
was reloaded. No Compose service was restarted or recreated.

| Request | Result | Proven owner |
| --- | --- | --- |
| `GET /api/codex.ts?v=private-preview-proof` | HTTP 200, `text/javascript`, 9,619 bytes | Vite source module; path and query preserved |
| `GET /api/llm/catalog?include=all` | HTTP 200, `application/json`, top-level `providers` key | Guardian semantic API |
| `GET /health` | HTTP 200, `application/json` | Guardian health surface |

The canonical static validator passed 39 checks and the reachability validator
passed. Live Docker publication still showed only
`127.0.0.1:8081->8080/tcp` for `private-preview-origin`; Guardian, Vite,
Postgres, Redis, Neo4j, workers, and provider services remained unpublished.

## Public browser and authentication proof

The corrective public proof used the existing Access application and operator
session without reading cookies, OTPs, passwords, Guardian tokens, or private
content.

1. Anonymous requests to `/`, `/api/codex.ts`, `/api/llm/catalog`, and
   `/health` each returned HTTP 302 to
   `resonant-constructs.cloudflareaccess.com`.
2. After Access admission, the canonical public page loaded with title
   `Codexify`. The formerly empty root mounted the real application shell,
   including the private-preview notice, navigation, dashboard, documents,
   and gallery surfaces.
3. Origin logs recorded browser module traffic under `/api/` returning HTTP
   200, including `/api/piCoderDryRun.ts`, while browser Guardian health calls
   under `/api/health/` also returned HTTP 200.
4. A fresh browser tab in the already Access-admitted browser opened
   `https://preview.codexify.space/login` and rendered the Guardian form with
   email and password fields. This proves Cloudflare admission does not
   substitute for Guardian authentication.
5. The operator completed normal Guardian login without sharing credentials.
   The browser returned to the canonical workspace. Revisiting `/login`
   rendered `Your workspace is ready` and `An active session was found on this
   device`, proving the distinct Guardian session was active.

The browser continued to report a Vite development HMR WebSocket attempt to
`localhost:5173`. The application mounted despite that development-only
warning. The workspace also displayed `Provider degraded` with
`chat_unhealthy`; provider diagnosis and execution are outside this ingress
proof and are not relabeled as success.

## Tunnel, isolation, and credential proof

- Cloudflare Tunnel's authenticated read-only API returned `healthy` with four
  active connections after the corrective reload.
- The foreground connector process remained alive. No boot/login resumption
  mechanism was installed or claimed.
- Cloudflare Tunnel still terminates only at `127.0.0.1:8081`; the fallback
  ingress rule remains `http_status:404`.
- The contract test proves private-preview browser-facing Vite environment
  values do not contain Guardian server API keys or provider credentials.
- Nginx injects the Guardian API key only on the server-side Guardian upstream
  request. The Vite module location contains no Guardian key header.
- No Cloudflare resource, allowlist, provider policy, persistence volume, or
  unrelated Docker workload changed.

## Validation results

- `pytest -v tests/ops/test_private_preview_contract.py` — ENVIRONMENTAL
  FAILURE under system Python because `fastapi` was unavailable; no test body
  ran.
- `.venv/bin/python -m pytest -v tests/ops/test_private_preview_contract.py`
  — PASS, 6 tests.
- `nginx -t` in `private-preview-origin` — PASS.
- Reload of only the active `private-preview-origin` Nginx process — PASS.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static`
  — PASS, 39 checks.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability`
  — PASS.
- Local source-module, semantic-API, and health route matrix — PASS.
- Anonymous public Access-denial matrix — PASS, four HTTP 302 redirects.
- Access-admitted public application render — PASS.
- Independent Guardian login boundary and authenticated session — PASS.
- Cloudflare Tunnel API health — PASS, healthy with four connections.
- Provider execution and persistence — NOT RUN; outside this ingress task.

## ADR impact

Aligned with ADR-005, ADR-039, ADR-040, ADR-041, ADR-042, ADR-049, and
ADR-069. No new ADR is required. The bounded source-module exception repairs
the accepted development-preview single origin without changing Guardian
authority, account ownership, telemetry, provider policy, or support posture.

## Documentation follow-through

`docs/Ops/private-browser-preview.md` now records the exact path-ownership
contract: bounded `/api/` source modules belong to Vite; every other
`/api/**` request and `/health` belong to Guardian. The runbook explicitly
states that the exception preserves path/query, provides no 404 fallback, and
is not a general production-web architecture.

## Axis KB addition

Record that the Cloudflare ingress lineage moved from a proven routing blocker
to a bounded repair: Nginx now recognizes only Vite source-module extensions
under `/api/`, while semantic API traffic remains Guardian-owned. Local and
public browser proof passed; Access and Guardian remain separate authentication
layers; internal services remain unpublished. Guest admission, provider
execution, persistence, connector resumption, and public Beta support remain
unproven by this receipt.
