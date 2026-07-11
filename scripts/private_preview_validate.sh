#!/usr/bin/env bash
set -euo pipefail

port="${CODEXIFY_PREVIEW_PORT:-8080}"
base="http://127.0.0.1:${port}"

curl --fail --silent --show-error "${base}/health" >/dev/null
curl --fail --silent --show-error --head "${base}/" >/dev/null

# The single origin must not leak direct backend/frontend ports from the
# preview overlay; inspect Compose rather than relying on host-network probes.
docker compose --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml ps

echo "private-preview origin is healthy at ${base}"
