from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ops/private_preview_backup_restore_proof.sh"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _restore_run_block(script: str) -> str:
    start = script.index('docker run -d \\\n  --name "${RESTORE_CONTAINER}"')
    end = script.index('wait_for_postgres "${RESTORE_CONTAINER}"', start)
    return script[start:end]


def test_disposable_restore_identity_is_explicit_and_nonempty() -> None:
    script = _script_text()

    user_match = re.search(r'^RESTORE_POSTGRES_USER="([^"]+)"$', script, re.MULTILINE)
    database_match = re.search(r'^RESTORE_POSTGRES_DB="([^"]+)"$', script, re.MULTILINE)

    assert user_match is not None
    assert database_match is not None
    assert user_match.group(1) not in {"root", "postgres"}
    assert database_match.group(1)


def test_restore_identity_is_validated_before_container_start() -> None:
    script = _script_text()
    restore_start = script.index("RESTORE_SUFFIX=")
    run_start = script.index("docker run -d", restore_start)

    assert (
        script.index('[[ -n "${RESTORE_POSTGRES_USER}" ]]', restore_start) < run_start
    )
    assert script.index('[[ -n "${RESTORE_POSTGRES_DB}" ]]', restore_start) < run_start


def test_restore_container_initializes_both_identity_values_and_trust_auth() -> None:
    block = _restore_run_block(_script_text())

    assert '-e "POSTGRES_USER=${RESTORE_POSTGRES_USER}" \\' in block
    assert '-e "POSTGRES_DB=${RESTORE_POSTGRES_DB}" \\' in block
    assert "-e POSTGRES_HOST_AUTH_METHOD=trust" in block


def test_restore_clients_use_container_identity_environment() -> None:
    script = _script_text()

    assert 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' in script
    assert 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' in script
    assert (
        'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" '
        '-d "$POSTGRES_DB"'
    ) in script


def test_restore_has_no_root_role_fallback() -> None:
    script = _script_text()

    assert "-U root" not in script
    assert 'RESTORE_POSTGRES_USER="root"' not in script


def test_restore_isolation_contract_remains_intact() -> None:
    script = _script_text()
    block = _restore_run_block(script)

    assert "--network none" in block
    assert "codexify.proof=private-preview-backup-restore" in block
    assert "source=${RESTORE_VOLUME}" in block
    assert '[[ "${RESTORE_DB_MOUNT}" != "${SOURCE_VOLUME}|true" ]]' in script
    assert '[[ "${RESTORE_PORTS}" == "{}" || "${RESTORE_PORTS}" == "null" ]]' in script


def _function(name: str) -> str:
    script = _script_text()
    start = script.index(f"{name}() {{")
    return script[start : script.index("\n}\n", start) + 2]


def test_restores_exact_existing_ids_and_checks_inventory(tmp_path) -> None:
    import subprocess

    result = subprocess.run(
        [
            "bash",
            "-c",
            _function("restore_original_service_state")
            + r"""
set -e
CHECKPOINT_DIR="$1"
ORIGINAL_INVENTORY="$1/before.json"
printf 'same\n' >"$ORIGINAL_INVENTORY"
ORIGINAL_RUNNING_IDS=(backend-id coding-id voice-id account-import-id)
log() { printf '%s\n' "$*"; }
fail() { printf '%s\n' "$*" >&2; return 1; }
capture_inventory() { printf '%s\n' "${INVENTORY:-same}"; }
docker() {
  case "$1" in
    inspect)
      if [[ "$3" != *Running* ]]; then return 1; fi
      if [[ "$4" == backend-id ]]; then
        printf '%s true\n' "$4"
      else
        printf '%s false\n' "$4"
      fi
      ;;
    start) printf '%s\n' "$2" >>"$start_LOG" ;;
    *) return 1 ;;
  esac
}
start_LOG="$1/start.log"
restore_original_service_state
[[ "$(cat "$start_LOG")" == $'coding-id\nvoice-id\naccount-import-id' ]]
INVENTORY=changed
if restore_original_service_state; then exit 1; fi
""",
            "fixture",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Manual recovery required" in result.stderr


def test_reconciler_gate_refuses_desired_up_before_docker_stop(tmp_path) -> None:
    import subprocess

    (tmp_path / "enabled").touch()
    script = _script_text()
    assert script.index("reconciler_quiet || exit 1\nSOURCE_FROZEN=1") < script.index(
        'docker stop "${WRITER_IDS[@]}"'
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            _function("reconciler_quiet")
            + """
STATE_DIR="$1"
PYTHON_BIN=python3
RECONCILER_TARGET=fixture
fail() { printf '%s\n' "$*" >&2; return 1; }
reconciler_quiet
""",
            "fixture",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "desired-up is enabled" in result.stderr


def test_pinned_compose_is_read_only_and_precedes_freeze() -> None:
    script = _script_text()
    assert "docker-compose.private-preview-serving.yml" in script
    assert "Development checkout cannot serve the proof" in script
    assert "compose up " not in script
    assert "compose stop" not in script
    assert script.index("Insufficient guest restore capacity") < script.index(
        'docker stop "${WRITER_IDS[@]}"'
    )
    assert 'docker rm -f "${RESTORE_CONTAINER_ID}"' in script


def test_reconciler_checks_block_lifecycle_on_unresolved_state(tmp_path) -> None:
    import subprocess

    launchctl = tmp_path / "launchctl"
    launchctl.write_text(
        """#!/bin/bash
case "$CASE" in
  active) printf 'fixture = {\n\tstate = running\n\tpid = 42\n}\n' ;;
  timeout) exec sleep 10 ;;
  missing) exit 1 ;;
  unknown) printf 'fixture = {\n\tstate = pending\n}\n' ;;
  idle) printf 'fixture = {\n\tstate = not running\n}\n' ;;
esac
"""
    )
    launchctl.chmod(0o700)
    shell = (
        _function("reconciler_quiet")
        + """
STATE_DIR="$1"
RECONCILER_TARGET=fixture
PYTHON_BIN=python3
export PATH="$1:$PATH" CASE="$2"
reconciler_quiet || exit 1
printf 'lifecycle reached\n'
"""
    )
    for case in ("active", "timeout", "missing", "unknown", "idle"):
        result = subprocess.run(
            ["bash", "-c", shell, "fixture", str(tmp_path), case],
            capture_output=True,
            text=True,
            timeout=8,
        )
        assert (result.returncode == 0) == (case == "idle"), result.stderr
        assert ("lifecycle reached" in result.stdout) == (case == "idle")
        if case == "timeout":
            assert "timed out" in result.stderr


def test_serving_identity_checks_image_overlay_and_live_bind(tmp_path) -> None:
    import json
    import os
    import subprocess
    import sys

    check = (
        _script_text().split("<<'PY_INVENTORY'\n", 1)[1].split("\nPY_INVENTORY", 1)[0]
    )
    config_path = tmp_path / "config.json"
    inventory_path = tmp_path / "inventory.json"
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\nprintf 'sha256:expected\\n'\n")
    docker.chmod(0o700)
    root, dev = "/pinned", "/unrelated-development-checkout"
    image = "codexify-backend-runtime:private-preview-tree-123456789"
    rows = [
        dict(
            service=name,
            id=name,
            state="running",
            running=True,
            workdir=dev,
            config_files="base,preview,serving",
            config_hash=name,
            ports={},
            image_ref=image if name == "backend" else name,
            image="sha256:expected",
            mounts=[],
        )
        for name in ("backend", "db", "private-preview-origin")
    ]
    backend, _, origin = rows
    origin["ports"] = {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8081"}]}
    for path in ("guardian", "backend", "data/media", "data/imports"):
        backend["mounts"].append(
            dict(
                Source=root + "/" + path,
                Destination="/app/" + path,
                Type="bind",
                RW=True,
            )
        )
    config = {
        "services": {
            row["service"]: {
                "image": row["image_ref"],
                "volumes": [
                    dict(type="bind", source=m["Source"], target=m["Destination"])
                    for m in row["mounts"]
                ],
            }
            for row in rows
        }
    }
    command = [
        sys.executable,
        "-c",
        check,
        str(inventory_path),
        "base,preview,serving",
        dev,
        root,
        "123456789",
        "\n".join(f"{r['service']} {r['service']}" for r in rows),
        str(config_path),
    ]

    def run():
        config_path.write_text(json.dumps(config))
        inventory_path.write_text(json.dumps(rows))
        return subprocess.run(
            command,
            env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
            capture_output=True,
            text=True,
            timeout=8,
        )

    # The development checkout is just the project directory. Its HEAD is not consulted.
    assert run().returncode == 0
    config["services"]["backend"]["image"] = image.replace("123456789", "987654321")
    assert "disagrees with pinned checkout tree" in run().stderr
    config["services"]["backend"]["image"] = image
    backend["mounts"][0]["Source"] = dev + "/guardian"
    assert "live bind does not match" in run().stderr
    backend["mounts"][0]["Source"] = root + "/guardian"
    backend["image"] = "sha256:other"
    assert "running image ID disagrees" in run().stderr
