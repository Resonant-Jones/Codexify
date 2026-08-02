from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "browser_host" / "launch_with_attachment_grant.py"
GRANT = "SYNTHETIC_NON_SECRET_TEST_BEARER_000000000000000000000000"
API_KEY = "synthetic-parent-guardian-api-key"


class _GrantHandler(BaseHTTPRequestHandler):
    status = 201
    payload: dict[str, Any] | None = None
    requests: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path == "/dev/browser-host/v1/attachment-grants":
            self.__class__.requests.append(
                {
                    "path": self.path,
                    "apiKey": self.headers.get("X-API-Key"),
                    "body": json.loads(body),
                }
            )
            status = self.__class__.status
            payload = self.__class__.payload or {"error": "failed"}
        elif self.path == "/dev/browser-host/v1/negotiate":
            status = 422
            payload = {"error": "synthetic-route-probe"}
        else:
            status = 401
            payload = {"error": "synthetic-route-probe"}
        response_body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(405 if self.path in {
            "/dev/browser-host/v1/negotiate",
            "/dev/browser-host/v1/attachments",
        } else 404)
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _server(*, status: int = 201, payload: dict[str, Any] | None = None) -> ThreadingHTTPServer:
    _GrantHandler.status = status
    _GrantHandler.payload = payload
    _GrantHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GrantHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _grant(instance_id: str) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0.0",
        "grantId": "grant-test-1",
        "authorizationScheme": "browser_host_attachment_grant",
        "grantBearer": GRANT,
        "protocolVersion": "1.0.0",
        "attachmentVersion": "1.0.0",
        "browserHostInstanceId": instance_id,
        "requestId": "grant-request-test-1",
        "retentionClass": "ephemeral",
        "maxContentBytes": 32768,
        "remainingUses": 1,
        "issuedAt": "2026-08-01T14:00:00.000Z",
        "expiresAt": "2026-08-01T14:02:00.000Z",
    }


def _child_code(result_path: Path, exit_code: int = 0) -> str:
    return (
        "import json, os, pathlib, sys; "
        f"pathlib.Path({str(result_path)!r}).write_text(json.dumps({{"
        "'grantPresent': bool(os.getenv('CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT')), "
        "'apiKeyPresent': bool(os.getenv('GUARDIAN_API_KEY')), "
        "'sessionPresent': bool(os.getenv('GUARDIAN_SESSION_SECRET')), "
        "'jwtPresent': bool(os.getenv('GUARDIAN_JWT_SECRET')), "
        "'providerKeysPresent': any(os.getenv(name) for name in ('OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'GROQ_API_KEY', 'ANTHROPIC_API_KEY', 'MISTRAL_API_KEY', 'OPENAI_TOKEN')), "
        "'proofTokenPresent': bool(os.getenv('CODEXIFY_BROWSER_HOST_PROOF_TOKEN'))"
        "}), encoding='utf-8'); "
        f"sys.exit({exit_code})"
    )


def _run(server: ThreadingHTTPServer, result_path: Path, *, child_exit: int = 0, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    instance_id = "browser-host-launcher-test"
    env = {
        **os.environ,
        "GUARDIAN_API_KEY": API_KEY,
        "GUARDIAN_SESSION_SECRET": "synthetic-session-secret",
        "GUARDIAN_JWT_SECRET": "synthetic-jwt-secret",
        "OPENAI_API_KEY": "synthetic-provider-key",
        "DEEPSEEK_API_KEY": "synthetic-deepseek-key",
        "OPENAI_TOKEN": "synthetic-provider-token",
        "CODEXIFY_BROWSER_HOST_PROOF_MODE": "1",
        "CODEXIFY_BROWSER_HOST_PROOF_TOKEN": "CODEXIFY-SYNTHETIC-1234567890abcdef",
        "CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN": "http://127.0.0.1:43123",
        "CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN": "http://127.0.0.1:43124",
    }
    if extra_env:
        env.update(extra_env)
    command = [
        sys.executable,
        "-c",
        _child_code(result_path, child_exit),
    ]
    return subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--guardian-origin",
            f"http://127.0.0.1:{server.server_port}",
            "--browser-host-instance-id",
            instance_id,
            "--grant-ttl-seconds",
            "120",
            "--max-attachment-bytes",
            "32768",
            "--timeout-ms",
            "3000",
            "--",
            *command,
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_launcher_sanitizes_child_environment_and_requests_one_grant(tmp_path: Path) -> None:
    server = _server(payload=_grant("browser-host-launcher-test"))
    result_path = tmp_path / "child-result.json"
    try:
        completed = _run(server, result_path)
        assert completed.returncode == 0
        result = json.loads(result_path.read_text())
        assert result == {
            "grantPresent": True,
            "apiKeyPresent": False,
            "sessionPresent": False,
            "jwtPresent": False,
            "providerKeysPresent": False,
            "proofTokenPresent": True,
        }
        assert len(_GrantHandler.requests) == 1
        assert _GrantHandler.requests[0]["path"] == "/dev/browser-host/v1/attachment-grants"
        assert _GrantHandler.requests[0]["apiKey"] == API_KEY
        request = _GrantHandler.requests[0]["body"]
        assert request["browserHostInstanceId"] == "browser-host-launcher-test"
        assert request["requestedAttachmentCount"] == 1
        assert request["requestedRetention"] == "ephemeral"
        assert request["requestedTtlSeconds"] == 120
        assert request["requestedMaxContentBytes"] == 32768
        assert GRANT not in completed.stdout + completed.stderr
        assert API_KEY not in completed.stdout + completed.stderr
        assert "Authorization" not in completed.stdout + completed.stderr
        assert not any("grant" in path.name.lower() for path in tmp_path.iterdir())
    finally:
        server.shutdown()
        server.server_close()


def test_launcher_preserves_child_exit_code_without_forwarding_child_output(tmp_path: Path) -> None:
    server = _server(payload=_grant("browser-host-launcher-test"))
    result_path = tmp_path / "child-result.json"
    try:
        completed = _run(server, result_path, child_exit=7)
        assert completed.returncode == 7
        assert "child exit code: 7" in completed.stdout
        assert GRANT not in completed.stdout + completed.stderr
    finally:
        server.shutdown()
        server.server_close()


def test_launcher_does_not_launch_after_issuance_failure(tmp_path: Path) -> None:
    server = _server(status=503)
    result_path = tmp_path / "child-result.json"
    try:
        completed = _run(server, result_path)
        assert completed.returncode == 2
        assert not result_path.exists()
        assert "child command started" not in completed.stdout
    finally:
        server.shutdown()
        server.server_close()


def test_launcher_rejects_malformed_grant_without_launching(tmp_path: Path) -> None:
    server = _server(payload={"schemaVersion": "1.0.0", "grantBearer": GRANT})
    result_path = tmp_path / "child-result.json"
    try:
        completed = _run(server, result_path)
        assert completed.returncode == 2
        assert not result_path.exists()
    finally:
        server.shutdown()
        server.server_close()


def test_launcher_rejects_non_loopback_origin(tmp_path: Path) -> None:
    env = {
        "CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN": "http://127.0.0.1:43123",
    }
    result_path = tmp_path / "child-result.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--guardian-origin",
            "http://localhost:43123",
            "--",
            sys.executable,
            "-c",
            _child_code(result_path),
        ],
        cwd=ROOT,
        env={**os.environ, **env, "GUARDIAN_API_KEY": API_KEY},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert not result_path.exists()
    assert API_KEY not in completed.stdout + completed.stderr
