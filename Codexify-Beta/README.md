# Codexify Beta Handoff Bundle

This folder is the small public-pull beta handoff for the browser UI.

If you received the bundle as a zip, unzip it first and work from the extracted `Codexify-Beta/` folder.

It uses the same local backend runtime as the macOS desktop path, but it opens in a browser instead of the Tauri shell.

It is local Docker only.
It is not cloud hosting.
It is not remote multi-user deployment.

## Prerequisites

- Docker Desktop, or Docker Engine with Compose
- A local Ollama or compatible host model setup if you want the default local model path

## Setup

1. Copy the example env file:

   ```bash
   cp .env.example .env
   ```

2. Pull the published images:

   ```bash
   docker compose pull
   ```

3. Start the bundle:

   ```bash
   docker compose up -d
   ```

4. Open the web UI:

   ```text
   http://localhost:3000
   ```

## What Is In This Folder

- `docker-compose.yml`
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
