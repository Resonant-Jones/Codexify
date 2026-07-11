from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.tester.yml"
ENV_TEMPLATE_PATH = ROOT / ".env.tester.example"
SERVE_CONFIG_PATH = ROOT / "config" / "tailscale" / "codexify-test-serve.json"
RUNBOOK_PATH = ROOT / "docs" / "Ops" / "friends-family-tester-runtime.md"


def test_tester_compose_uses_a_dedicated_persistent_tailscale_sidecar() -> None:
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "tailscale-codexify-test:" in text
    assert "hostname: \"${TAILSCALE_TEST_HOSTNAME:-codexify-test}\"" in text
    assert "TS_AUTHKEY:" in text
    assert "TS_STATE_DIR: /var/lib/tailscale" in text
    assert "TS_SERVE_CONFIG: /config/codexify-test-serve.json" in text
    assert "--advertise-tags=tag:codexify-test" in text
    assert "codexify_tailscale_test_state:/var/lib/tailscale" in text
    assert "network_mode: \"service:tailscale-codexify-test\"" in text
    assert "network_mode: host" not in text
    assert "TS_ROUTES:" not in text
    assert "--advertise-exit-node" not in text


def test_tester_compose_keeps_non_web_ports_off_non_loopback_interfaces() -> None:
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert '"127.0.0.1:5434:5432"' in text
    assert '"127.0.0.1:7475:7474"' in text
    assert '"127.0.0.1:7688:7687"' in text
    assert '"127.0.0.1:8889:8888"' in text
    assert '"127.0.0.1:${CODEXIFY_TESTER_LOCAL_PORT:-5174}:5173"' in text
    assert text.count("ports: !override") == 3
    assert "ports: !reset []" in text


def test_tailscale_serve_config_exposes_only_private_https_to_frontend() -> None:
    text = SERVE_CONFIG_PATH.read_text(encoding="utf-8")

    assert '"443"' in text
    assert '"HTTPS": true' in text
    assert '"Proxy": "http://127.0.0.1:5173"' in text
    assert '"AllowFunnel"' in text
    assert "false" in text
    assert "TS_CERT_DOMAIN" in text
    assert "8888" not in text
    assert "5432" not in text


def test_tester_environment_and_runbook_keep_auth_material_private() -> None:
    env_template = ENV_TEMPLATE_PATH.read_text(encoding="utf-8")
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "TAILSCALE_TEST_AUTHKEY=<tskey-auth-tagged-codexify-test>" in env_template
    assert "TAILSCALE_TEST_FQDN=codexify-test.<your-tailnet>.ts.net" in env_template
    assert "autogroup:shared" in runbook
    assert '"ip": ["tcp:443"]' in runbook
    assert "Share** action" in runbook
    assert "Tailscale Funnel stays disabled" in runbook
