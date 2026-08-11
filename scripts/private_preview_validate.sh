#!/usr/bin/env bash
set -euo pipefail

mode="${1:-static}"
case "${mode}" in
  static|reachability|providers) ;;
  *)
    echo "usage: $0 {static|reachability|providers}" >&2
    exit 2
    ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${PRIVATE_PREVIEW_ENV_FILE:-${repo_root}/.env.private-preview}"
base_url="${PRIVATE_PREVIEW_BASE_URL:-http://127.0.0.1:8081}"
compose_json="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview.compose.XXXXXX.json")"
chmod 600 "${compose_json}"
trap 'rm -f "${compose_json}"' EXIT

compose=(
  docker compose
  --env-file "${env_file}"
  -f "${repo_root}/docker-compose.yml"
  -f "${repo_root}/docker-compose.private-preview.yml"
)
python_bin="${PRIVATE_PREVIEW_PYTHON:-${repo_root}/.venv/bin/python}"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="$(command -v python3)"
fi

static_validation() {
  test -f "${env_file}" || {
    echo "private-preview env file is missing: ${env_file}" >&2
    return 1
  }

  (
    cd "${repo_root}"
    "${python_bin}" -m pytest -q \
      tests/core/test_supported_profile.py \
      tests/ops/test_private_preview_contract.py \
      tests/ops/test_private_preview_provider_proof.py
  )

  "${compose[@]}" config --format json >"${compose_json}"
  "${python_bin}" - "${compose_json}" <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
services = config.get("services", {})
expected = {
    "CODEXIFY_SUPPORTED_PROFILE": "v1-whooshd-deepseek-web",
    "LLM_PROVIDER": "local",
    "ALLOW_CLOUD_PROVIDERS": "true",
    "CODEXIFY_LOCAL_ONLY_MODE": "false",
    "CODEXIFY_EGRESS_ALLOWLIST": "deepseek",
    "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
    "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
    "LOCAL_PROVIDER_VENDOR": "whooshd",
    "LOCAL_CHAT_MODEL": "gemma-4-12b-it-qat-4bit",
    "DEEPSEEK_CHAT_MODEL": "deepseek-v4-flash",
}
for service_name in ("backend", "worker-chat"):
    environment = services.get(service_name, {}).get("environment", {})
    for key, value in expected.items():
        actual = str(environment.get(key, ""))
        if actual.lower() != value.lower():
            raise SystemExit(
                f"{service_name}.{key} expected {value!r}, found {actual!r}"
            )
frontend = services.get("frontend", {}).get("environment", {})
for key in ("VITE_GUARDIAN_API_KEY", "VITE_GUARDIAN_DEV_API_KEY"):
    if str(frontend.get(key) or ""):
        raise SystemExit(f"frontend.{key} must remain empty")
for server_field in (
    "DEEPSEEK_API_KEY",
    "GUARDIAN_API_KEY",
    "GUARDIAN_SESSION_SECRET",
    "GUARDIAN_JWT_SECRET",
):
    if server_field in frontend:
        raise SystemExit(
            f"frontend must not receive server-only credential field: {server_field}"
        )

ports = []
for service_name, service in services.items():
    for port in service.get("ports") or []:
        ports.append(
            (
                service_name,
                str(port.get("host_ip") or ""),
                int(port["published"]),
                int(port["target"]),
            )
        )
expected_ports = [("private-preview-origin", "127.0.0.1", 8081, 8080)]
if ports != expected_ports:
    raise SystemExit(f"published port contract mismatch: {ports!r}")

print("static configuration proof: PASS")
print("published ports: private-preview-origin 127.0.0.1:8081 -> 8080")
PY
}

reachability_validation() {
  static_validation
  curl --fail --silent --show-error "${base_url}/health" >/dev/null
  curl --fail --silent --show-error "${base_url}/health/chat" >/dev/null
  curl --fail --silent --show-error "${base_url}/api/health/llm" >/dev/null
  curl --fail --silent --show-error \
    "${base_url}/api/llm/catalog?include=all" >/dev/null
  curl --fail --silent --show-error --head "${base_url}/" >/dev/null
  echo "unauthenticated reachability proof: PASS (${base_url})"
  echo "reachability does not prove provider execution or persistence"
}

providers_validation() {
  reachability_validation
  if [[ -z "${PRIVATE_PREVIEW_SESSION_TOKEN_FILE:-}" ]]; then
    echo "PRIVATE_PREVIEW_SESSION_TOKEN_FILE is required for providers mode" >&2
    return 1
  fi
  "${python_bin}" "${repo_root}/scripts/ops/private_preview_provider_proof.py" \
    --base-url "${base_url}" \
    --session-token-file "${PRIVATE_PREVIEW_SESSION_TOKEN_FILE}"
  echo "authenticated dual-provider execution proof: PASS"
}

case "${mode}" in
  static) static_validation ;;
  reachability) reachability_validation ;;
  providers) providers_validation ;;
esac
