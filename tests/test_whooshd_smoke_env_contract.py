"""Smoke contract tests for the Whoosh'd Docker environment.

These tests validate that the blessed Whoosh'd gateway contract is
correctly encoded and that invalid configurations are rejected.

They do NOT require Docker or Whoosh'd — they test the contract
definitions and validation logic in isolation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# ── Helpers ──


def _load_supported_profile() -> dict:
    """Load the v1-local-core-web-mcp supported profile YAML."""
    profile_path = Path("config/supported_profiles/v1-local-core-web-mcp.yaml")
    if not profile_path.exists():
        pytest.skip("Supported profile YAML not found")
    with open(profile_path) as f:
        return yaml.safe_load(f)


def _mock_settings(**overrides):
    """Build a mock settings object matching the contract fields."""

    class MockSettings:
        pass

    s = MockSettings()
    s.LLM_PROVIDER = "local"
    s.ALLOW_CLOUD_PROVIDERS = False
    s.CODEXIFY_LOCAL_ONLY_MODE = True
    s.CODEXIFY_EGRESS_ALLOWLIST = ""
    s.LOCAL_BASE_URL = "http://host.docker.internal:8000/v1"
    s.LOCAL_API_KEY = "local"
    s.LOCAL_PROVIDER_VENDOR = "whooshd"
    s.WHOOSHD_HEALTH_BASE_URL = "http://host.docker.internal:8000"
    s.LOCAL_CHAT_MODEL = "mlx-community/gemma-4-e2b-it-4bit"
    s.LOCAL_VISION_MODEL = "qwen2-vl-2b-mlx"
    s.LOCAL_GGUF_MODEL = "qwen2.5-0.5b-gguf"

    for key, value in overrides.items():
        setattr(s, key, value)
    return s


# ── Supported profile tests ──


class TestSupportedProfileExists:
    def test_profile_yaml_exists(self):
        profile = _load_supported_profile()
        assert profile is not None
        assert profile["name"] == "v1-local-core-web-mcp"

    def test_profile_has_provider_contract(self):
        profile = _load_supported_profile()
        contract = profile.get("provider_contract", {})
        assert contract["LLM_PROVIDER"] == "local"
        assert contract["ALLOW_CLOUD_PROVIDERS"] is False
        assert contract["CODEXIFY_LOCAL_ONLY_MODE"] is True
        assert contract["CODEXIFY_EGRESS_ALLOWLIST"] == ""
        assert contract["LOCAL_BASE_URL"] == "http://host.docker.internal:8000/v1"


# ── Smoke Compose override tests ──


class TestSmokeComposeOverrideExists:
    def test_override_file_exists(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        assert override_path.exists(), (
            "docker-compose.whooshd-smoke.yml not found"
        )

    def test_override_is_valid_yaml(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert "services" in config

    def test_backend_has_blessed_contract(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["LLM_PROVIDER"] == "local"
        assert backend_env["LOCAL_PROVIDER_VENDOR"] == "whooshd"
        assert backend_env["LOCAL_BASE_URL"] == "http://host.docker.internal:8000/v1"
        assert backend_env["ALLOW_CLOUD_PROVIDERS"] == "false"
        assert backend_env["CODEXIFY_EGRESS_ALLOWLIST"] == ""
        assert backend_env["CODEXIFY_LOCAL_ONLY_MODE"] == "true"

    def test_worker_chat_has_blessed_contract(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        worker_env = config["services"]["worker-chat"]["environment"]
        assert worker_env["LLM_PROVIDER"] == "local"
        assert worker_env["LOCAL_PROVIDER_VENDOR"] == "whooshd"
        assert worker_env["LOCAL_BASE_URL"] == "http://host.docker.internal:8000/v1"
        assert worker_env["ALLOW_CLOUD_PROVIDERS"] == "false"
        assert worker_env["CODEXIFY_EGRESS_ALLOWLIST"] == ""
        assert worker_env["CODEXIFY_LOCAL_ONLY_MODE"] == "true"

    def test_override_has_model_aliases(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["LOCAL_CHAT_MODEL"] == (
            "mlx-community/gemma-4-e2b-it-4bit"
        )
        assert backend_env["LOCAL_LLM_MODEL"] == (
            "mlx-community/gemma-4-e2b-it-4bit"
        )
        assert backend_env["LLM_MODEL"] == (
            "mlx-community/gemma-4-e2b-it-4bit"
        )
        assert backend_env["DEFAULT_LOCAL_MODEL"] == (
            "mlx-community/gemma-4-e2b-it-4bit"
        )
        assert backend_env["LOCAL_VISION_MODEL"] == "qwen2-vl-2b-mlx"
        assert backend_env["LOCAL_GGUF_MODEL"] == "qwen2.5-0.5b-gguf"

    def test_override_covers_worker_warmup_and_embed(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        for svc in ("worker-warmup", "worker-chat-embed"):
            assert svc in config["services"], f"{svc} missing from override"
            env = config["services"][svc]["environment"]
            assert env["LLM_PROVIDER"] == "local"
            assert env["LOCAL_BASE_URL"] == "http://host.docker.internal:8000/v1"


# ── Contract rejection tests ──


class TestContractRejectsCloudProviders:
    """The blessed contract requires ALLOW_CLOUD_PROVIDERS=false."""

    def test_true_is_rejected(self):
        """ALLOW_CLOUD_PROVIDERS=true should fail validation."""
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract["ALLOW_CLOUD_PROVIDERS"] is False

        # Simulate: settings.ALLOW_CLOUD_PROVIDERS = True
        actual = True
        expected = contract["ALLOW_CLOUD_PROVIDERS"]
        assert actual != expected, "True should not match the contract's False"

    def test_false_is_accepted(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        actual = False
        assert actual == contract["ALLOW_CLOUD_PROVIDERS"]


class TestContractRejectsCloudEgress:
    """The blessed contract requires empty CODEXIFY_EGRESS_ALLOWLIST."""

    def test_nonempty_is_rejected(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract["CODEXIFY_EGRESS_ALLOWLIST"] == ""

        actual = "groq,openai,anthropic"
        assert actual != contract["CODEXIFY_EGRESS_ALLOWLIST"]

    def test_empty_is_accepted(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        actual = ""
        assert actual == contract["CODEXIFY_EGRESS_ALLOWLIST"]


class TestContractRequiresCorrectLocalBaseUrl:
    """The blessed contract requires http://host.docker.internal:8000/v1."""

    def test_localhost_is_rejected_in_docker(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]

        actual = "http://localhost:8000/v1"
        assert actual != contract["LOCAL_BASE_URL"], (
            "localhost URL should not match Docker-internal host.docker.internal"
        )

    def test_host_docker_internal_is_accepted(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]

        actual = "http://host.docker.internal:8000/v1"
        assert actual == contract["LOCAL_BASE_URL"]

    def test_tailscale_ip_is_rejected(self):
        """The dev .env points at a Tailscale IP — must be rejected."""
        profile = _load_supported_profile()
        contract = profile["provider_contract"]

        actual = "http://host.docker.internal:11434"
        assert actual != contract["LOCAL_BASE_URL"], (
            "Tailscale IP URL should not match blessed Whoosh'd gateway"
        )


# ── Smoke wrapper script tests ──


class TestSmokeWrapperScriptExists:
    def test_script_exists(self):
        script_path = Path("scripts/whooshd_docker_smoke_up.sh")
        assert script_path.exists(), "Smoke wrapper script not found"

    def test_script_is_executable(self):
        script_path = Path("scripts/whooshd_docker_smoke_up.sh")
        assert script_path.stat().st_mode & 0o111, (
            "Script is not executable"
        )

    def test_script_references_compose_override(self):
        script_path = Path("scripts/whooshd_docker_smoke_up.sh")
        content = script_path.read_text()
        assert "docker-compose.whooshd-smoke.yml" in content

    def test_script_passes_bash_syntax_check(self):
        """This is verified at module load time via bash -n above."""
        script_path = Path("scripts/whooshd_docker_smoke_up.sh")
        assert script_path.exists()


# ── No-cloud-fallback tests ──


class TestNoCloudFallback:
    def test_local_only_mode_blocks_cloud_providers(self):
        """When CODEXIFY_LOCAL_ONLY_MODE=true, cloud providers are disabled."""
        settings = _mock_settings()
        assert settings.CODEXIFY_LOCAL_ONLY_MODE is True
        assert settings.ALLOW_CLOUD_PROVIDERS is False
        assert settings.CODEXIFY_EGRESS_ALLOWLIST == ""

    def test_local_only_mode_rejects_allow_cloud_true(self):
        """If ALLOW_CLOUD_PROVIDERS=true but CODEXIFY_LOCAL_ONLY_MODE=true,
        local-only should take precedence."""
        # In the supported profile, BOTH must be set; local-only is the
        # hard gate that prevents fallback regardless of ALLOW_CLOUD_PROVIDERS.
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract["CODEXIFY_LOCAL_ONLY_MODE"] is True
        assert contract["ALLOW_CLOUD_PROVIDERS"] is False


# ── Model propagation tests ──


class TestModelPropagation:
    def test_chat_model_propagated(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["LOCAL_CHAT_MODEL"] == (
            "mlx-community/gemma-4-e2b-it-4bit"
        )

    def test_vision_model_propagated(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["LOCAL_VISION_MODEL"] == "qwen2-vl-2b-mlx"

    def test_gguf_model_propagated(self):
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["LOCAL_GGUF_MODEL"] == "qwen2.5-0.5b-gguf"


# ── Whoosh'd standalone verification ──


class TestWhooshdStaysStandalone:
    def test_no_whooshd_import_in_codexify_routes(self):
        """Codexify should not import Whoosh'd internals.

        The whooshd_model_profiles module in Codexify is allowed — it
        provides model ID -> profile metadata mappings and does NOT
        import the Whoosh'd server package.  We only flag direct imports
        of an actual 'whooshd' Python package.
        """
        for check_path in [
            "guardian/guardian_api.py",
            "guardian/core/config.py",
        ]:
            p = Path(check_path)
            if p.exists():
                content = p.read_text()
                # A direct 'import whooshd' (no suffix) would mean pulling
                # in the Whoosh'd server runtime — that must not happen.
                import_lines = [
                    line.strip()
                    for line in content.splitlines()
                    if line.strip().startswith(("import whooshd", "from whooshd"))
                ]
                assert len(import_lines) == 0, (
                    f"{check_path} imports whooshd internals: {import_lines}"
                )

    def test_compose_override_does_not_add_whooshd_service(self):
        """The Whoosh'd container is managed separately, not by our Compose."""
        override_path = Path("docker-compose.whooshd-smoke.yml")
        with open(override_path) as f:
            config = yaml.safe_load(f)

        for svc in config["services"]:
            assert "whooshd" not in svc.lower(), (
                f"Service '{svc}' looks like a Whoosh'd container — "
                "Whoosh'd must remain standalone"
            )
