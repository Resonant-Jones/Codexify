#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${1:-codexify-runtime-compiled:local}"

docker run --rm --entrypoint sh "${IMAGE_NAME}" -lc '
  set -eu
  test -x /app/runtime/codexify-runtime
  test -L /app/runtime/codexify-backend
  test -d /app/runtime/_internal
  test -d /app/config
  test -d /app/docs/builtin-help
  test -f /app/runtime/alembic.ini
  test -d /app/runtime/migrations
  test ! -d /app/backend
  test ! -d /app/tests
  test ! -d /app/guardian
'
