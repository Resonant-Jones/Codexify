#!/usr/bin/env bash
# Start the loopback Whoosh'd service and Codexify's dual-provider profile.
#
# Usage:
#   bash scripts/whooshd_deepseek_profile_up.sh
#   CODEXIFY_ENV_FILE=.env.tester bash scripts/whooshd_deepseek_profile_up.sh
#
# This script only kickstarts an already-installed system LaunchDaemon. It
# never installs a plist, changes listeners, or widens the Whoosh'd bind.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${CODEXIFY_ENV_FILE:-.env.tester}"
WHOOSHD_BASE_URL="${WHOOSHD_BASE_URL:-http://127.0.0.1:8000}"
BACKEND_URL="${CODEXIFY_BACKEND_URL:-http://127.0.0.1:8889}"
WHOOSHD_LABEL="${WHOOSHD_LAUNCHD_LABEL:-system/com.resonant.whooshd}"
# ADR-074: this is an assertion input, not a second runtime selection source.
# The historical tracked default is retained until a separate live-inventory
# reconciliation establishes the current operator selection. Operators may
# supply EXPECTED_MODEL for that assertion without changing Compose authority.
EXPECTED_MODEL="${EXPECTED_MODEL:-qwen3.8-27b-4bit}"
WHOOSHD_READINESS_TIMEOUT_SECONDS="${WHOOSHD_READINESS_TIMEOUT_SECONDS:-120}"
CODEXIFY_READINESS_TIMEOUT_SECONDS="${CODEXIFY_READINESS_TIMEOUT_SECONDS:-120}"

cd "$ROOT_DIR"

if ! curl -fsS --max-time 3 "$WHOOSHD_BASE_URL/health" >/dev/null 2>&1; then
  command -v launchctl >/dev/null 2>&1 || {
    echo "Whoosh'd is down and launchctl is unavailable." >&2
    exit 1
  }
  echo "Whoosh'd is not healthy; kickstarting $WHOOSHD_LABEL"
  launchctl kickstart -k "$WHOOSHD_LABEL"
  readonly WHOOSHD_READY_TIMEOUT_SECONDS="${WHOOSHD_READY_TIMEOUT_SECONDS:-60}"
  readonly WHOOSHD_READY_DEADLINE=$((SECONDS + WHOOSHD_READY_TIMEOUT_SECONDS))
  until curl -fsS --max-time 3 "$WHOOSHD_BASE_URL/health" >/dev/null 2>&1; do
    if (( SECONDS >= WHOOSHD_READY_DEADLINE )); then
      echo "Whoosh'd did not become ready within ${WHOOSHD_READY_TIMEOUT_SECONDS}s after kickstart." >&2
      exit 1
    fi
    sleep 2
  done
fi

python3 - "$WHOOSHD_BASE_URL" "$EXPECTED_MODEL" "$WHOOSHD_READINESS_TIMEOUT_SECONDS" <<'PY'
import json, sys, time, urllib.error, urllib.request

base, expected, readiness_timeout = sys.argv[1:]
deadline = time.monotonic() + float(readiness_timeout)
def get(path):
    with urllib.request.urlopen(base + path, timeout=5) as response:
        return json.load(response)

last_error = None
while time.monotonic() < deadline:
    try:
        health = get('/health')
        if health.get('status') == 'ready' or health.get('ok') is True:
            break
        last_error = f"health payload was not ready: {health!r}"
    except (OSError, ValueError, urllib.error.URLError) as exc:
        last_error = repr(exc)
    time.sleep(2)
else:
    raise SystemExit(
        f"Whoosh'd did not become ready within {readiness_timeout}s; last error: {last_error}"
    )
models = get('/v1/models').get('data') or []
ids = [str(item.get('id') or '').strip() for item in models]
if ids != [expected]:
    raise SystemExit(f"Whoosh'd model pin failed; expected only {expected!r}, got {ids!r}")
print(f"Whoosh'd ready; exclusive model={expected}")

from concurrent.futures import ThreadPoolExecutor

def complete(index):
    payload = json.dumps({
        'model': expected,
        'messages': [{'role': 'user', 'content': f'Reply exactly LOAD-{index}'}],
        'max_tokens': 8,
        'temperature': 0,
    }).encode()
    request = urllib.request.Request(
        base + '/v1/chat/completions',
        data=payload,
        headers={'Authorization': 'Bearer local', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        body = json.load(response)
        choices = body.get('choices') or []
        content = (
            choices[0].get('message', {}).get('content')
            if choices and isinstance(choices[0], dict)
            else None
        )
        return response.status, content

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(complete, (1, 2)))
expected_results = [(200, 'LOAD-1'), (200, 'LOAD-2')]
normalized_results = [
    (status, content.strip() if isinstance(content, str) else content)
    for status, content in results
]
if normalized_results != expected_results:
    raise SystemExit(f"Whoosh'd concurrent x2 gate failed: {normalized_results!r}")
print("Whoosh'd concurrent x2 gate passed")
PY

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-codexify_tester}" \
  docker compose --env-file "$ENV_FILE" \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml \
  up -d frontend backend db redis worker-chat worker-document-embed migrator

python3 - "$BACKEND_URL" "$CODEXIFY_READINESS_TIMEOUT_SECONDS" <<'PY'
import json, os, sys, time, urllib.error, urllib.request

base, readiness_timeout = sys.argv[1:]
deadline = time.monotonic() + float(readiness_timeout)
last_error = None
while time.monotonic() < deadline:
    try:
        health_payloads = {}
        for path in ('/api/health/chat', '/api/health/llm'):
            with urllib.request.urlopen(base + path, timeout=15) as response:
                payload = json.load(response)
            expected_status = 'healthy' if path.endswith('/chat') else 'ok'
            if response.status != 200 or payload.get('status') != expected_status:
                raise RuntimeError(
                    f'{path} is not ready: HTTP {response.status}: {payload!r}'
                )
            health_payloads[path] = payload
        break
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        last_error = repr(exc)
        time.sleep(2)
else:
    raise SystemExit(
        f'Codexify did not become ready within {readiness_timeout}s; last error: {last_error}'
    )

for path, payload in health_payloads.items():
    print(path, json.dumps(payload, sort_keys=True))

with urllib.request.urlopen(base + '/api/llm/catalog', timeout=15) as response:
    providers = json.load(response).get('providers') or []
by_id = {str(item.get('id') or '').strip(): item for item in providers}
if set(by_id) != {'local', 'deepseek'}:
    raise SystemExit(f'provider pin failed; expected local and deepseek only: {sorted(by_id)}')
expected_model = os.environ.get('EXPECTED_MODEL', 'qwen3.8-27b-4bit')
if [str(item.get('id') or '').strip() for item in by_id['local'].get('models', [])] != [expected_model]:
    raise SystemExit(f'local provider is not pinned to {expected_model!r}')
if [str(item.get('id') or '').strip() for item in by_id['deepseek'].get('models', [])] != ['deepseek-v4-flash']:
    raise SystemExit('DeepSeek provider is not pinned to DeepSeek V4 Flash')
print(f'provider catalog pinned: local {expected_model} + deepseek-v4-flash')
PY

echo "Dual-provider Codexify profile is up: local ${EXPECTED_MODEL} + approved DeepSeek V4 Flash."
echo "Bounded Whoosh'd x2 concurrency gate passed before startup."
