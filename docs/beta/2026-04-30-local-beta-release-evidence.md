# 2026-04-30 Local Beta Release Evidence

This note records the public-pull state for the local-beta runtime images and the small handoff bundle that testers can download and run directly.

The browser handoff bundle lives in `Codexify-Beta/README.md`.

## Registry Pull Checks

- Clean shell baseline: `docker logout ghcr.io`
- Runtime image pull: `docker pull ghcr.io/resonant-jones/codexify-runtime:local-beta`
  - Result: successful anonymous pull
- WebUI image pull: `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta`
  - Result: successful anonymous pull

## Bundle Validation

- `docker compose -f Codexify-Beta/docker-compose.yml config` rendered successfully.
- `docker compose -f Codexify-Beta/docker-compose.yml pull` completed successfully.
- The first public cold-path attempt failed because `codexify-neo4j-1` became unhealthy and Compose returned `dependency failed to start: container codexify-neo4j-1 is unhealthy`.
- The corrected handoff bundle moves Neo4j and `graph-init` behind the optional `graph` profile so the default tester path does not wait on optional graph health.
- `docker compose -f Codexify-Beta/docker-compose.yml up -d` now starts the default bundle without requiring Neo4j health.
- `docker compose -f Codexify-Beta/docker-compose.yml ps` shows the backend, frontend, db, redis, and required workers up on the default path.
- `curl -sS http://localhost:8888/health | jq` returned `status: ok`.
- `curl -sS http://localhost:8888/health/chat | jq` returned `status: healthy`.
- `curl -sS http://localhost:8888/api/health/llm | jq` returned `status: ok`.
- `curl -I http://localhost:3000` returned `HTTP/1.1 200 OK`.

## Interpretation

- `ghcr.io/resonant-jones/codexify-runtime:local-beta` is publicly pullable from a clean shell.
- `ghcr.io/resonant-jones/codexify-webui:local-beta` is publicly pullable from a clean shell.
- The small-folder webUI beta handoff path is now low-friction and does not require GHCR authentication for normal testers.
- The bundle is still local Docker only and does not imply cloud hosting or remote multi-user deployment.

## Fallback Validation Path

- If a tester runs into local Docker cache issues or a private fork/mirror, the bundle README still points them at the normal `docker compose pull` and `docker compose up -d` flow.
- The repo-level script `bash scripts/verification/check_beta_handoff_bundle.sh` replays the same proof from the workspace.
