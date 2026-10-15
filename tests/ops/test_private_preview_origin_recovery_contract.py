from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_OVERLAY = ROOT / "docker-compose.private-preview.yml"
NGINX = ROOT / "docker/private-preview/nginx.conf"
LIFECYCLE = ROOT / "scripts/ops/codexify_private_preview.sh"
TUNNEL = ROOT / "scripts/ops/codexify_private_preview_tunnel.sh"
STACK_PLIST = (
    ROOT / "config/launchd/com.resonant.codexify-private-preview.plist.template"
)
TUNNEL_PLIST = (
    ROOT
    / "config/launchd/com.resonant.codexify-private-preview-tunnel.plist.template"
)


def test_private_preview_origin_uses_dynamic_backend_dns_resolution() -> None:
    nginx = NGINX.read_text(encoding="utf-8")

    assert "resolver 127.0.0.11 valid=10s ipv6=off;" in nginx
    assert re.search(
        r"upstream guardian_backend\s*\{.*?server backend:8888 resolve;",
        nginx,
        re.DOTALL,
    )
    assert "proxy_pass http://guardian_backend/health;" in nginx
    assert "proxy_pass http://guardian_backend;" in nginx
    assert "proxy_pass http://guardian_backend/api/ws/;" in nginx
    assert not re.search(
        r"(?:proxy_pass|server)\s+https?://?\d+\.\d+\.\d+\.\d+|"
        r"server\s+\d+\.\d+\.\d+\.\d+",
        nginx,
    )


def test_private_preview_compose_keeps_origin_ingress_and_backend_private() -> None:
    compose = COMPOSE_OVERLAY.read_text(encoding="utf-8")

    assert "private-preview-origin:" in compose
    assert "- \"127.0.0.1:${CODEXIFY_PREVIEW_PORT:-8081}:8080\"" in compose
    assert "./docker/private-preview/nginx.conf:/etc/nginx/conf.d/default.conf:ro" in compose
    assert "backend:" in compose
    assert "ports: !reset []" in compose


def test_private_preview_long_running_services_honor_intentional_stop() -> None:
    compose = COMPOSE_OVERLAY.read_text(encoding="utf-8")

    for service in ("db", "neo4j", "backend", "frontend", "private-preview-origin"):
        service_block = re.search(
            rf"(?ms)^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [^ ]|\Z)",
            compose,
        )
        assert service_block is not None
        assert "restart: unless-stopped" in service_block.group("body")


def test_private_preview_lifecycle_has_explicit_manual_off_boundary() -> None:
    lifecycle = LIFECYCLE.read_text(encoding="utf-8")

    assert "PRIVATE_PREVIEW_ENABLED_MARKER" in lifecycle
    assert "set_desired_up" in lifecycle
    assert "clear_desired_up" in lifecycle
    assert "command_auto_start" in lifecycle
    assert "compose stop" in lifecycle
    assert "report_health" in lifecycle
    assert (
        """report_health "http://127.0.0.1:8081/health/chat" '{"ok":true'"""
        in lifecycle
    )
    down_body = lifecycle[lifecycle.index("command_down") :]
    assert down_body.index("clear_desired_up") < down_body.index("compose stop")
    assert "launchctl bootout" in lifecycle
    assert "compose down" not in lifecycle


def test_private_preview_tunnel_is_marker_gated_and_foreground() -> None:
    tunnel = TUNNEL.read_text(encoding="utf-8")

    assert "PRIVATE_PREVIEW_ENABLED_MARKER" in tunnel
    assert 'if [[ ! -f "$PRIVATE_PREVIEW_ENABLED_MARKER" ]]' in tunnel
    assert 'exec "$PRIVATE_PREVIEW_CLOUDFLARED" tunnel' in tunnel
    assert "credentials-contents" not in tunnel


def test_private_preview_launchagents_reconcile_stack_and_tunnel() -> None:
    stack = STACK_PLIST.read_text(encoding="utf-8")
    tunnel = TUNNEL_PLIST.read_text(encoding="utf-8")

    assert "<key>RunAtLoad</key>" in stack
    assert "<key>StartInterval</key>" in stack
    assert "<integer>300</integer>" in stack
    assert "__CODEXIFY_PRIVATE_PREVIEW_HOME__" in stack
    assert "__CODEXIFY_PRIVATE_PREVIEW_RUNNER__" in stack
    assert "<key>KeepAlive</key>" in tunnel
    assert "<key>PathState</key>" in tunnel
    assert "__CODEXIFY_PRIVATE_PREVIEW_HOME__" in tunnel
    assert "__CODEXIFY_PRIVATE_PREVIEW_ENABLED_MARKER__" in tunnel
    assert "__CODEXIFY_PRIVATE_PREVIEW_TUNNEL_CONFIG__" in tunnel


def test_private_preview_installer_waits_for_launchagent_unload() -> None:
    installer = (
        ROOT / "scripts/ops/install_codexify_private_preview_launchagents.sh"
    ).read_text(encoding="utf-8")

    assert "unload_agent" in installer
    assert 'launchctl bootout "$target"' in installer
    assert "LaunchAgent did not unload cleanly" in installer
