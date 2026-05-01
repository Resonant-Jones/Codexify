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
- `docker compose -f Codexify-Beta/docker-compose.yml up -d` started the bundle.
- `docker compose -f Codexify-Beta/docker-compose.yml ps` showed the backend and frontend up.
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
