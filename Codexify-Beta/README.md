# Codexify Beta Handoff Bundle

This folder is the small public handoff bundle for the browser UI.

If you received the bundle as a zip, unzip it first and work from the extracted `Codexify-Beta/` folder.

It uses the same local backend runtime as the desktop path, but this bundle opens in a browser instead of the Tauri shell.

It is local Docker only.
It is not cloud hosting.
It is not remote multi-user deployment.
Graph context is optional for the default tester path; the bundle starts cleanly without Neo4j.
The browser-side beta auth key is localhost/dev only and must match the backend key in `.env`.

## Prerequisites

- Docker Desktop, or Docker Engine with Compose
- A local Ollama or compatible host model setup if you want the default local model path
- Read [AUTHORIZATION.md](./AUTHORIZATION.md) before first launch if you need to set or recover the beta API key.

## Setup

Normal flow:

```bash
cp .env.example .env
# edit .env and replace GUARDIAN_API_KEY and VITE_GUARDIAN_API_KEY with the same local dev key
docker compose pull
docker compose run --rm migrator
docker compose up -d
sleep 20
open http://localhost:3000
```

If you are on Linux or do not have `open`, use your browser normally:

```text
http://localhost:3000
```

If the app shows `Authentication required`, follow [AUTHORIZATION.md](./AUTHORIZATION.md).

If backend API-key auth works but the browser still shows `apiKeyPresent=false`, make sure `VITE_GUARDIAN_API_KEY` matches `GUARDIAN_API_KEY` in `.env`, then restart the WebUI container.

If `/healthz` shows tables as missing, run the migrator before expecting schema-backed routes to work:

```bash
docker compose run --rm migrator
docker compose up -d
```

For diagnostics, source the env file and check backend auth and schema readiness:

```bash
set -a; source .env; set +a
curl -s http://localhost:8888/healthz | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/threads | jq
```

Healthy schema should report:

- `projects_table_exists: true`
- `chat_threads_table_exists: true`

If the authenticated `/threads` request returns `{ "threads": [] }`, backend API-key auth is working.

Optional graph context:

- If you intentionally want the optional graph services, start them with `docker compose --profile graph up -d`.
- Do not enable that profile for the normal tester path unless you are explicitly validating graph behavior.

## What Is In This Folder

- `docker-compose.yml`
- `AUTHORIZATION.md`
- `.env.example`
- `README.md`

That is the entire shareable handoff bundle.

## Update

To refresh the images and restart the bundle:

```bash
docker compose pull && docker compose up -d
```

## Stop

```bash
docker compose down
```

## Troubleshooting

- Docker not running: start Docker Desktop or the Docker Engine daemon, then rerun the commands.
- Ports already in use: free up `3000` for the browser UI and `8888` for the backend.
- Stale local image cache: run `docker compose pull` again before `docker compose up -d`.
- GHCR auth should not be required for the normal public-pull path.
- Neo4j is optional for the public handoff bundle; if the graph profile is not enabled, the default startup does not wait for Neo4j health.
- If the browser says `Authentication required`, check [AUTHORIZATION.md](./AUTHORIZATION.md) and confirm the browser key matches the backend key.
- If `apiKeyPresent=false` appears in Settings, check [AUTHORIZATION.md](./AUTHORIZATION.md) and confirm `VITE_GUARDIAN_API_KEY` matches `GUARDIAN_API_KEY`.
- If `/healthz` reports missing tables, run the migrator before expecting schema-backed routes to work.
- If `source .env` emits `command not found: self` or similar, one of the env values is unquoted; quote the whole CSP-like value or replace the file with the corrected `.env.example`.
- If the UI shows `backend_unreachable`, confirm the backend container is healthy and `http://localhost:8888/healthz` responds before checking the frontend proxy/base URL.
- If the browser shows `Authentication required` or health looks degraded, check [AUTHORIZATION.md](./AUTHORIZATION.md).
- If you are on a private fork or a mirror, or your Docker cache is stale, authenticate to GHCR and retry the pull.

## Packaging

To create the shareable zip from this repo root, run:

```bash
bash scripts/release/package_beta_handoff_bundle.sh
```

The archive is written to `dist/Codexify-Beta-WebUI-local-beta.zip`.

## Notes

- The bundle uses the same local backend runtime as the desktop path.
- Keep your real `.env` local and do not commit it.
