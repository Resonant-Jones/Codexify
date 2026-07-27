from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = ROOT / "scripts" / "ops" / "codexify_tester.sh"
BASE_COMPOSE = ROOT / "docker-compose.yml"
TESTER_COMPOSE = ROOT / "docker-compose.tester.yml"

EXPECTED_START_SERVICES = [
    "backend",
    "frontend",
    "worker-chat",
    "worker-chat-embed",
    "worker-document-embed",
    "worker-warmup",
    "worker-account-import",
    "tailscale-codexify-test",
]

EXPECTED_REQUIRED_SERVICES = [
    "db",
    "neo4j",
    "backend",
    "redis",
    "frontend",
    "worker-chat",
    "worker-chat-embed",
    "worker-document-embed",
    "worker-warmup",
    "worker-account-import",
    "tailscale-codexify-test",
]


def _array_values(script: str, name: str) -> list[str]:
    match = re.search(rf"{name}=\((.*?)\)", script, re.DOTALL)
    assert match is not None
    return re.findall(r"^  ([a-z0-9-]+)$", match.group(1), re.MULTILINE)


def _write_mock_docker(tmp_path: Path) -> Path:
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    docker = mock_bin / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ \"${1:-}\" == \"info\" ]]; then
  exit 0
fi
if [[ \"${1:-}\" == \"compose\" ]]; then
  case \"$*\" in
    *\" ps --all --format \"*)
      printf '%s\\n' \"${MOCK_COMPOSE_ROWS:-}\"
      ;;
    *\" ps\"*)
      printf '%s\\n' 'mock compose table'
      ;;
  esac
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    curl = mock_bin / "curl"
    curl.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    curl.chmod(0o755)
    return mock_bin


def _run_status(tmp_path: Path, rows: list[str]) -> subprocess.CompletedProcess[str]:
    mock_bin = _write_mock_docker(tmp_path)
    env_file = tmp_path / ".env.tester"
    env_file.touch()
    environment = {
        **os.environ,
        "PATH": f"{mock_bin}{os.pathsep}{os.environ['PATH']}",
        "CODEXIFY_TESTER_REPO_ROOT": str(ROOT),
        "CODEXIFY_TESTER_ENV_FILE": str(env_file),
        "CODEXIFY_TESTER_STATE_DIR": str(tmp_path / "state"),
        "CODEXIFY_TESTER_PROJECT_NAME": "codexify_tester",
        "MOCK_COMPOSE_ROWS": "\n".join(rows),
    }
    return subprocess.run(
        ["bash", str(LIFECYCLE), "status"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_tester_startup_and_status_rosters_include_account_import_worker_once() -> None:
    script = LIFECYCLE.read_text(encoding="utf-8")

    assert _array_values(script, "TESTER_START_SERVICES") == EXPECTED_START_SERVICES
    assert _array_values(script, "TESTER_REQUIRED_SERVICES") == EXPECTED_REQUIRED_SERVICES
    assert script.count("worker-account-import") == 2


def test_account_import_worker_is_defined_once_without_tester_override_duplication() -> None:
    base_text = BASE_COMPOSE.read_text(encoding="utf-8")
    tester_text = TESTER_COMPOSE.read_text(encoding="utf-8")

    assert base_text.count("  worker-account-import:\n") == 1
    assert "  worker-account-import:\n" not in tester_text


def test_tester_status_marks_a_missing_account_import_worker_degraded(tmp_path: Path) -> None:
    rows = [
        f"{service}|running|"
        for service in EXPECTED_REQUIRED_SERVICES
        if service != "worker-account-import"
    ]

    result = _run_status(tmp_path, rows)

    assert result.returncode == 1
    assert "required_service=worker-account-import state=missing healthy=false" in result.stdout
    assert "tester_status=degraded" in result.stderr
    assert "project=codexify_tester" in result.stdout
    assert "project=codexify\n" not in result.stdout


def test_tester_status_accepts_a_running_account_import_worker(tmp_path: Path) -> None:
    rows = [f"{service}|running|" for service in EXPECTED_REQUIRED_SERVICES]

    result = _run_status(tmp_path, rows)

    assert result.returncode == 0
    assert "required_service=worker-account-import state=running healthy=true" in result.stdout
    assert "tester_status=healthy" in result.stdout
