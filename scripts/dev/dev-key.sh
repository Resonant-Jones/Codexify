# scripts/dev-key.sh
#!/usr/bin/env bash
set -euo pipefail

# Look in local-first order; print the LAST value found (allows overrides)
grep -h -E '^GUARDIAN_API_KEY=' .env.local .env.backend.development .env 2>/dev/null \
  | tail -n1 \
  | cut -d= -f2- \
  | tr -d '\r'
