# Private browser preview behind Cloudflare Tunnel

This is an opt-in preview lane, not a new supported public product surface.
It exposes one loopback origin only: the frontend at `/`, the API at `/api`,
WebSocket RPC at `/ws`, and the backend health probe at `/health`. The base
Compose file is unchanged.

## Trust boundaries

- Browser and Cloudflare edge are untrusted clients; the tunnel is transport,
  not authorization.
- `private-preview-origin` is the only host-published service (`127.0.0.1:8080`
  by default). Backend, Vite, Postgres, Neo4j, and TTS are Compose-network-only.
- Backend enforces a signed session, an email allowlist, and the role derived
  from the server environment. The UI never receives an API key.

## Start

1. Copy `.env.private-preview.example` to `.env.private-preview` and fill in
   fresh secrets plus the approved/admin email lists. Keep it untracked.
2. Pre-provision each email account from the backend container; the command
   reads the password interactively and refuses addresses outside the server
   allowlist. Preview mode deliberately returns `404` from `/auth/register`.

   ```bash
   docker compose --env-file .env.private-preview -f docker-compose.yml -f docker-compose.private-preview.yml exec backend python -m guardian.cli.private_preview_provision --email guest@example.com
   ```
3. Start the origin:

   ```bash
   docker compose --env-file .env.private-preview -f docker-compose.yml -f docker-compose.private-preview.yml up -d
   ```

4. Validate it:

   ```bash
   CODEXIFY_PREVIEW_PORT=8080 ./scripts/private_preview_validate.sh
   ```

5. In Cloudflare Zero Trust, create a self-hosted private web application for
   the chosen hostname. Add an explicit Allow policy for the same email set as
   `CODEXIFY_PREVIEW_APPROVED_EMAILS`; do not use an `Everyone`, `Bypass`, or
   unconstrained one-time-PIN policy. Copy
   `config/cloudflared/private-preview.yml.example` to an ignored local path,
   set the generated tunnel UUID/credential path and hostname, then run the
   named tunnel on the operator host:

   ```bash
   cloudflared tunnel --config ~/.cloudflared/codexify-private-preview.yml run codexify-private-preview
   ```

Do not use `cloudflared tunnel --url ...` for this lane: it creates a Quick
Tunnel rather than the named, Access-protected preview contract.

## Authorization contract

- `CODEXIFY_PREVIEW_ADMIN_EMAILS` maps those exact normalized email identities
  to `admin` on every request.
- Every other authenticated address in `CODEXIFY_PREVIEW_APPROVED_EMAILS` is
  `guest`; all other users receive `401`.
- Admin routes require the server-resolved admin role; `X-Admin-Token` and
  local debug bypasses are not accepted in preview mode.
- Multi-user ownership scope is enabled, so projects and chat threads are
  queried and mutated only for the authenticated email account.

## Validation checklist

- `GET /health` succeeds through the origin.
- No `8888`, `5173`, database, or TTS ports appear in the preview Compose
  publication list.
- An allowlisted guest can log in but receives `403` on an admin endpoint.
- A guest cannot list, read, mutate, or append to another account's project or
  thread (expect `403` or `404`, depending on the route).
- Browser requests stay relative (`/api/...`, `/ws/...`); no API key appears in
  the delivered JavaScript or browser request headers.
