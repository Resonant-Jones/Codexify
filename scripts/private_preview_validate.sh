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
  "${python_bin}" - "${compose_json}" "${repo_root}" <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
repo_root = Path(sys.argv[2]).resolve()
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
    "LOCAL_CHAT_MODEL": "qwen3.8-27b-4bit",
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
worker_chat = services.get("worker-chat", {}).get("environment", {})
if str(worker_chat.get("CHAT_WORKER_CONCURRENCY", "")) != "1":
    raise SystemExit(
        "worker-chat.CHAT_WORKER_CONCURRENCY must be '1' for the "
        "single-slot MLX-VLM runtime"
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

atlas_source = repo_root / "projection-ui-map/rc-atlas-prototype.html"
if not atlas_source.is_file():
    raise SystemExit(f"canonical Atlas artifact is missing: {atlas_source}")
origin_mounts = services.get("private-preview-origin", {}).get("volumes") or []
atlas_mounts = [
    mount
    for mount in origin_mounts
    if Path(mount.get("source", "")).resolve() == atlas_source
]
if len(atlas_mounts) != 1:
    raise SystemExit(f"expected one canonical Atlas mount, found: {atlas_mounts!r}")
atlas_mount = atlas_mounts[0]
if atlas_mount.get("target") != "/usr/share/nginx/html/codexify-atlas.html":
    raise SystemExit(f"unexpected Atlas mount target: {atlas_mount!r}")
if atlas_mount.get("read_only") is not True:
    raise SystemExit(f"Atlas mount must be read-only: {atlas_mount!r}")
if any("atlas" in service_name for service_name in services):
    raise SystemExit("Atlas must not introduce a Compose service")

nginx = (repo_root / "docker/private-preview/nginx.conf").read_text(
    encoding="utf-8"
)
for required in (
    "location = /atlas {",
    "return 308 /atlas/;",
    "location = /atlas/ {",
    "alias /usr/share/nginx/html/codexify-atlas.html;",
    'add_header Cache-Control "no-store" always;',
    'add_header X-Robots-Tag "noindex, nofollow" always;',
):
    if required not in nginx:
        raise SystemExit(f"private-preview Atlas route is missing: {required}")
if "location /docs" in nginx or "location = /docs" in nginx:
    raise SystemExit("private-preview must not expose repository documentation")

print("static configuration proof: PASS")
print("published ports: private-preview-origin 127.0.0.1:8081 -> 8080")
print("Atlas mount: canonical read-only artifact -> /usr/share/nginx/html/codexify-atlas.html")
print("Atlas route: exact /atlas redirect and exact /atlas/ static response")
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
