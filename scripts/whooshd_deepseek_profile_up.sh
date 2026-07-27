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
EXPECTED_MODEL="gemma-4-12b-it-qat-4bit"

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

python3 - "$WHOOSHD_BASE_URL" "$EXPECTED_MODEL" <<'PY'
import json, sys, urllib.request

base, expected = sys.argv[1:]
def get(path):
    with urllib.request.urlopen(base + path, timeout=5) as response:
        return json.load(response)

health = get('/health')
if health.get('status') != 'ready' and health.get('ok') is not True:
    raise SystemExit(f"Whoosh'd is not ready: {health!r}")
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
        return response.status, body

with ThreadPoolExecutor(max_workers=2) as pool:
    responses = list(pool.map(complete, (1, 2)))
for index, (status, body) in enumerate(responses, start=1):
    if status != 200:
        raise SystemExit(f"Whoosh'd concurrent LOAD-{index} returned HTTP {status}: {body!r}")
    choices = body.get('choices') or []
    content = choices[0].get('message', {}).get('content') if choices else None
    if str(content or '').strip() != f'LOAD-{index}':
        raise SystemExit(
            f"Whoosh'd concurrent LOAD-{index} body mismatch; got {content!r}: {body!r}"
        )
print("Whoosh'd concurrent x2 gate passed")
PY

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-codexify_tester}" \
  docker compose --env-file "$ENV_FILE" \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml \
  up -d frontend backend db redis worker-chat worker-document-embed migrator

python3 - "$BACKEND_URL" <<'PY'
import json, sys, urllib.request

base = sys.argv[1]
for path in ('/api/health/chat', '/api/health/llm'):
    with urllib.request.urlopen(base + path, timeout=15) as response:
        payload = json.load(response)
    if response.status != 200:
        raise SystemExit(f'{path} returned HTTP {response.status}: {payload!r}')
    expected_status = 'healthy' if path.endswith('/chat') else 'ok'
    if payload.get('status') != expected_status:
        raise SystemExit(f'{path} is not ready: {payload!r}')
    print(path, json.dumps(payload, sort_keys=True))

with urllib.request.urlopen(base + '/api/llm/catalog', timeout=15) as response:
    providers = json.load(response).get('providers') or []
by_id = {str(item.get('id') or '').strip(): item for item in providers}
if set(by_id) != {'local', 'deepseek'}:
    raise SystemExit(f'provider pin failed; expected local and deepseek only: {sorted(by_id)}')
if [str(item.get('id') or '').strip() for item in by_id['local'].get('models', [])] != ['gemma-4-12b-it-qat-4bit']:
    raise SystemExit('local provider is not pinned to Gemma 12B IT QAT')
if [str(item.get('id') or '').strip() for item in by_id['deepseek'].get('models', [])] != ['deepseek-v4-flash']:
    raise SystemExit('DeepSeek provider is not pinned to DeepSeek V4 Flash')
print('provider catalog pinned: local Gemma + deepseek-v4-flash')
PY

echo "Dual-provider Codexify profile is up: local Gemma + approved DeepSeek V4 Flash."
echo "Bounded Whoosh'd x2 concurrency gate passed before startup."
