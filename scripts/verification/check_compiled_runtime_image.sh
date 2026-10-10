#!/usr/bin/env bash
set -euo pipefail

if (( $# > 2 )); then
  printf 'Usage: %s [local-image [expected-source-revision]]\n' "$0" >&2
  exit 2
fi
IMAGE_NAME="${1:-codexify-runtime-compiled:local}"
EXPECTED_REVISION="${2:-}"
if (( $# == 2 )) && [[ ! "$EXPECTED_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Expected source revision must be a full lowercase Git commit SHA.\n' >&2
  exit 2
fi

# Resolve once; all subsequent operations use immutable local content identity.
# A missing local reference must fail here, never trigger an implicit pull.
IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$IMAGE_NAME")"
if [[ ! "$IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  printf 'Docker did not return a valid local image content ID.\n' >&2
  exit 1
fi
REVISION="$(docker image inspect --format '{{if .Config.Labels}}{{index .Config.Labels "org.opencontainers.image.revision"}}{{end}}' "$IMAGE_ID")"
if [[ -n "$EXPECTED_REVISION" && "$REVISION" != "$EXPECTED_REVISION" ]]; then
  printf 'Source revision mismatch: expected=%s observed=%s image_id=%s\n' "$EXPECTED_REVISION" "${REVISION:-<missing>}" "$IMAGE_ID" >&2
  exit 1
fi

docker run --rm --pull never --network none --read-only --entrypoint sh "$IMAGE_ID" -lc '
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
  sha256sum /app/runtime/codexify-runtime
'
printf 'image_id=%s\nsource_revision=%s\n' "$IMAGE_ID" "${REVISION:-<missing>}"
if [[ -n "$EXPECTED_REVISION" ]]; then
  printf 'verification=source-revision-matched-and-structural; behavioral readiness unproven\n'
else
  printf 'verification=structural-only; source attestation and behavioral readiness unproven\n'
fi
