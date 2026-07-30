from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_OVERLAY = ROOT / "docker-compose.private-preview.yml"
NGINX = ROOT / "docker/private-preview/nginx.conf"


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
