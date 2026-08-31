# Dual-provider private browser preview

This is an opt-in friends-and-family demonstration lane, not a new supported
public product surface. Its supported profile is
`v1-whooshd-deepseek-web`: local Whoosh'd remains the default provider and
DeepSeek V4 Flash is the only admitted cloud lane. The global beta posture
remains local-first and local-only.

## Provider and network posture

- Whoosh'd serves `gemma-4-12b-it-qat-4bit` from a loopback-bound host process.
  Docker reaches it at `http://host.docker.internal:8000/v1`; Compose, Nginx,
  and Cloudflare do not publish port 8000.
- Guardian reaches DeepSeek outbound at `https://api.deepseek.com`. The
  provider policy token and entire egress allowlist are exactly `deepseek`.
  Never use wildcard egress.
- The sole host-published application origin is
  `http://127.0.0.1:8081`. It serves the frontend at `/`, Guardian at `/api`,
  task and domain events through the same origin, and health at `/health` and
  `/health/*`.
- The future approved hostname is `preview.codexify.space`. Cloudflare Tunnel
  terminates only at `127.0.0.1:8081`; it never connects directly to Whoosh'd
  or DeepSeek.
- Guardian remote/session authentication remains authoritative behind
  Cloudflare Access. The browser receives neither a Guardian API key nor a
  DeepSeek credential.

The UI persists provider and model choice in the thread configuration through
`PATCH /api/chat/threads/{thread_id}/config` using `providerId` and `modelId`.
The proof helper also supplies the provider and model explicitly on each
completion. Existing cloud-to-local rescue behavior is unchanged, but a
rescued turn fails provider-specific proof.

## Configure

Copy the committed template and fill only the untracked copy:

```bash
cp .env.private-preview.example .env.private-preview
chmod 600 .env.private-preview
```

Generate fresh Guardian session, JWT, and internal service-key values. Add the
approved/admin email lists and the DeepSeek API credential. Keep:

```text
CODEXIFY_SUPPORTED_PROFILE=v1-whooshd-deepseek-web
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=deepseek
```

These values belong only to this named preview lane. Do not copy them into
`v1-local-core-web-mcp`.

Provision each allowlisted account. The password is read interactively:

```bash
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  exec backend python -m guardian.cli.private_preview_provision \
  --email guest@example.com
```

## Render, start, and inspect

Render the secret-bearing resolved configuration only outside the repository:

```bash
umask 077
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  config --format json > /tmp/codexify-private-preview.compose.json
```

Start:

```bash
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  up -d --build
```

Inspect services and ports:

```bash
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml ps

docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E 'codexify|private-preview'
```

The only application publication may be
`127.0.0.1:8081->8080/tcp`. Guardian 8888, Vite 5173, Whoosh'd 8000, Redis,
Postgres, Neo4j, migrators, and workers must not have host bindings.

### Backend replacement recovery

The private-preview origin resolves the Compose `backend` service through
Docker's embedded DNS and refreshes that upstream on a bounded interval. After
the backend is restarted or force-recreated, `private-preview-origin` should
continue routing to the current healthy container without an origin restart.

The incident signature for the previous failure was:

- the backend reports healthy;
- `http://127.0.0.1:8081/health` returns `502 Bad Gateway`; and
- the backend container was recently restarted or recreated.

Inspect the container identities and health state:

```bash
docker compose --env-file .env.private-preview \
  -p codexify_private_preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  ps -q private-preview-origin backend

docker inspect --format '{{json .State}}' \
  codexify_private_preview-backend-1
```

Inspect nginx upstream failures without printing the resolved environment:

```bash
docker compose --env-file .env.private-preview \
  -p codexify_private_preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  logs --tail=200 private-preview-origin
```

Restarting only `private-preview-origin` can diagnose stale resolution in an
older image/configuration, but it must no longer be the normal recovery
requirement after backend replacement. An `exit 137` or `OOMKilled=true` state
is a resource failure; this nginx change does not increase Docker memory or
repair backend OOM pressure.

## Validation levels

Static configuration proof:

```bash
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
  bash scripts/private_preview_validate.sh static
```

Unauthenticated origin, health, chat, and catalog reachability:

```bash
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
  bash scripts/private_preview_validate.sh reachability
```

Authenticated provider execution requires an existing Guardian session token.
Log in normally, save only the returned token to a mode-600 file outside the
repository, then run:

```bash
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
PRIVATE_PREVIEW_SESSION_TOKEN_FILE=/secure/path/guardian-session-token \
  bash scripts/private_preview_validate.sh providers
```

The provider proof creates separate local and DeepSeek threads, persists one
user turn in each, waits for canonical terminal task events, reads the durable
transcript, requires exactly one assistant message per thread, and compares
attempted/final provider and model evidence. It never prints the token or
credential-bearing response fields.

## Independent failure diagnosis

Whoosh'd:

```bash
curl --fail --silent http://127.0.0.1:8000/v1/models
curl --fail --silent http://127.0.0.1:8081/api/health/llm
```

Confirm the exact Gemma model is inventoried and that the catalog local entry
reports vendor `whooshd`, runtime preset `whooshd-mlx`, and availability.

DeepSeek:

```bash
curl --fail --silent \
  http://127.0.0.1:8081/api/llm/catalog?include=all
```

Confirm DeepSeek alone is authorized among cloud providers, its credential is
recognized, `deepseek-v4-flash` is present, and egress is not denied. Do not
print `.env.private-preview` or resolved container environments.

Queue/worker:

```bash
curl --fail --silent http://127.0.0.1:8081/health/chat
```

Redis must be healthy and the chat-worker heartbeat fresh. HTTP 200 or enqueue
acceptance does not establish completion.

Recent logs, without environment inspection:

```bash
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  logs --tail=250 private-preview-origin backend worker-chat
```

## Stop and backup boundary

Stop without deleting volumes:

```bash
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml stop
```

Never use `down -v`. Before preview use with durable data, establish a separate
tested Postgres/media backup and restoration procedure; this task does not
implement or prove one.

The [2026-08-31 private-preview backup/restore attempt](../architecture/proofs/runtime/2026-08-31-private-preview-backup-restore-proof.md)
failed closed before backup because the preserved source database migration
revision trailed current local `main`. It created no retained checkpoint and
does not clear this prerequisite.

## Truth boundaries

- Catalog presence proves neither authorization nor execution.
- A successful Whoosh'd turn does not prove DeepSeek; a successful DeepSeek
  turn does not prove Whoosh'd.
- Route acceptance and task-event publication do not prove terminal completion
  or persistence.
- Fallback completion is not proof for the requested provider.
- Static tests and Compose rendering do not prove a running preview.
- This runbook does not prove Cloudflare Tunnel, Access, DNS, public-host
  behavior, guest isolation, rate limiting, backup restoration, reboot
  recovery, or general cloud-provider beta support.
