# scripts/dev-key.sh
#!/usr/bin/env bash
set -euo pipefail

# Read GUARDIAN_API_KEY from .env only (single source of truth).
key=$(grep -h -E '^GUARDIAN_API_KEY=' .env 2>/dev/null \
  | tail -n1 \
  | cut -d= -f2- \
  | tr -d '\r')

if [ -z "$key" ]; then
  echo "GUARDIAN_API_KEY is not set in .env" >&2
  exit 1
fi

printf '%s' "$key"
