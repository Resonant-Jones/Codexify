#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${1:-codexify-runtime-compiled:local}"

docker run --rm --entrypoint sh "${IMAGE_NAME}" -lc '
  set -eu
  test -x /app/runtime/codexify-runtime
  test -d /app/runtime/_internal
  test -f /app/runtime/alembic.ini
  test -d /app/runtime/migrations
  test -d /app/config
  test -d /app/docs/builtin-help
  test ! -d /app/backend
  test ! -d /app/tests
  test ! -d /app/guardian
  test ! -e /app/runtime/codexify-backend
  /app/runtime/codexify-runtime --help >/dev/null 2>&1
'
