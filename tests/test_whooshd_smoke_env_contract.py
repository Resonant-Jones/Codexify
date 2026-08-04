"""Static contract tests for the Whoosh'd Docker smoke environment.

These tests validate the supported profile, Compose override, and launcher
contract without starting Docker, Whoosh'd, or any model runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guardian.core.ai_router import (
    WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON,
)

SUPPORTED_PROFILE_PATH = Path(
    "config/supported_profiles/v1-local-core-web-mcp.yaml"
)
SMOKE_OVERRIDE_PATH = Path("docker-compose.whooshd-smoke.yml")
SMOKE_LAUNCHER_PATH = Path("scripts/whooshd_docker_smoke_up.sh")

CANONICAL_BASE_URL = "http://host.docker.internal:8000/v1"
CANONICAL_HEALTH_BASE_URL = "http://host.docker.internal:8000"
MACHINE_SPECIFIC_BASE_URL = "http://100.127." "148.28:8000/v1"

CANONICAL_PROVIDER_CONTRACT = {
    "LLM_PROVIDER": "local",
    "ALLOW_CLOUD_PROVIDERS": False,
    "CODEXIFY_LOCAL_ONLY_MODE": True,
    "CODEXIFY_EGRESS_ALLOWLIST": "",
    "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
    "LOCAL_BASE_URL": CANONICAL_BASE_URL,
    "LOCAL_API_KEY": "local",
    "LOCAL_COMPAT_FIRST": True,
    "LOCAL_PROVIDER_DISPLAY_NAME": "Whoosh'd",
    "LOCAL_PROVIDER_VENDOR": "whooshd",
}

CANONICAL_SMOKE_MODELS = {
    "LOCAL_CHAT_MODEL": "gemma-4-12b-it-qat-4bit",
    "LOCAL_LLM_MODEL": "gemma-4-12b-it-qat-4bit",
    "LLM_MODEL": "gemma-4-12b-it-qat-4bit",
    "DEFAULT_LOCAL_MODEL": "gemma-4-12b-it-qat-4bit",
    "LOCAL_VISION_MODEL": "gemma-vision-mlx",
    "LOCAL_GGUF_MODEL": "qwen3-coder-30b-gguf",
}

BOOLEAN_FIELDS = {
    "ALLOW_CLOUD_PROVIDERS",
    "CODEXIFY_LOCAL_ONLY_MODE",
    "LOCAL_COMPAT_FIRST",
}
MODEL_FIELDS = set(CANONICAL_SMOKE_MODELS)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"{path} not found")
    with path.open() as handle:
        return yaml.safe_load(handle)


def _load_supported_profile() -> dict:
    return _load_yaml(SUPPORTED_PROFILE_PATH)


def _load_smoke_override() -> dict:
    return _load_yaml(SMOKE_OVERRIDE_PATH)


def _normalize_contract_value(key: str, value: object) -> str:
    normalized = str(value).strip().lower()
    if key in BOOLEAN_FIELDS:
        return normalized
    return str(value).strip()


def _assert_provider_contract(
    env: dict, expected: dict = CANONICAL_PROVIDER_CONTRACT
):
    for key, value in expected.items():
        assert key in env, f"{key} missing from provider environment"
        assert _normalize_contract_value(key, env[key]) == (
            _normalize_contract_value(key, value)
        ), f"{key} does not match the supported provider contract"


def _mock_settings(**overrides):
    """Build a mock settings object matching the supported contract fields."""

    class MockSettings:
        pass

    settings = MockSettings()
    for key, value in CANONICAL_PROVIDER_CONTRACT.items():
        setattr(settings, key, value)
    settings.WHOOSHD_HEALTH_BASE_URL = CANONICAL_HEALTH_BASE_URL
    for key, value in CANONICAL_SMOKE_MODELS.items():
        setattr(settings, key, value)

    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def _authorized_contract_paths() -> tuple[Path, ...]:
    return (
        SUPPORTED_PROFILE_PATH,
        SMOKE_OVERRIDE_PATH,
        SMOKE_LAUNCHER_PATH,
        Path("tests/test_whooshd_smoke_env_contract.py"),
        Path("tests/core/test_supported_profile.py"),
        Path("tests/core/test_supported_profile_provider.py"),
        Path("docs/local-provider-whooshd.md"),
    )


class TestSupportedProfileExists:
    def test_profile_yaml_exists(self):
        profile = _load_supported_profile()
        assert profile["name"] == "v1-local-core-web-mcp"

    def test_profile_has_canonical_provider_contract(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract == CANONICAL_PROVIDER_CONTRACT
        assert not MODEL_FIELDS.intersection(contract)


class TestSmokeComposeOverrideExists:
    def test_override_file_exists(self):
        assert SMOKE_OVERRIDE_PATH.exists()

    def test_override_is_valid_yaml(self):
        config = _load_smoke_override()
        assert config is not None
        assert "services" in config

    def test_backend_has_blessed_contract(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        _assert_provider_contract(backend_env)
        assert (
            backend_env["WHOOSHD_HEALTH_BASE_URL"] == CANONICAL_HEALTH_BASE_URL
        )
        assert backend_env["CODEXIFY_SUPPORTED_PROFILE"] == (
            "v1-local-core-web-mcp"
        )

    def test_worker_chat_has_blessed_contract(self):
        config = _load_smoke_override()
        worker_env = config["services"]["worker-chat"]["environment"]
        _assert_provider_contract(worker_env)
        assert (
            worker_env["WHOOSHD_HEALTH_BASE_URL"] == CANONICAL_HEALTH_BASE_URL
        )

    def test_override_has_canonical_model_aliases(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        for key, value in CANONICAL_SMOKE_MODELS.items():
            assert backend_env[key] == value

    def test_gemma_default_is_not_live_inventory_proof(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert not MODEL_FIELDS.intersection(contract)
        assert CANONICAL_BASE_URL == (f"{CANONICAL_HEALTH_BASE_URL}/v1")
        assert WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON == (
            "configured_model_not_advertised_by_whooshd"
        )

    def test_override_covers_worker_warmup_and_embed(self):
        config = _load_smoke_override()
        warmup_env = config["services"]["worker-warmup"]["environment"]
        _assert_provider_contract(warmup_env)
        for key, value in CANONICAL_SMOKE_MODELS.items():
            assert warmup_env[key] == value

        embed_env = config["services"]["worker-chat-embed"]["environment"]
        _assert_provider_contract(
            embed_env,
            {
                "LLM_PROVIDER": "local",
                "LOCAL_BASE_URL": CANONICAL_BASE_URL,
                "LOCAL_API_KEY": "local",
                "LOCAL_PROVIDER_VENDOR": "whooshd",
                "ALLOW_CLOUD_PROVIDERS": False,
                "CODEXIFY_EGRESS_ALLOWLIST": "",
                "CODEXIFY_LOCAL_ONLY_MODE": True,
            },
        )
        assert not MODEL_FIELDS.intersection(embed_env)
        for key in (
            "LOCAL_RUNTIME_PRESET",
            "LOCAL_COMPAT_FIRST",
            "LOCAL_PROVIDER_DISPLAY_NAME",
            "WHOOSHD_HEALTH_BASE_URL",
            "CODEXIFY_SUPPORTED_PROFILE",
        ):
            assert key not in embed_env


class TestAuthorizedSurfaces:
    def test_canonical_host_bridge_is_used_without_machine_specific_ip(self):
        for path in _authorized_contract_paths():
            content = path.read_text()
            assert "host.docker.internal:8000" in content
            assert MACHINE_SPECIFIC_BASE_URL not in content

    def test_launcher_asserts_canonical_contract_and_default_model(self):
        content = SMOKE_LAUNCHER_PATH.read_text()
        for marker in (
            "LOCAL_BASE_URL: http://host.docker.internal:8000/v1",
            "LOCAL_PROVIDER_VENDOR: whooshd",
            "LOCAL_RUNTIME_PRESET: whooshd-mlx",
            "LOCAL_COMPAT_FIRST: .true.",
            "WHOOSHD_HEALTH_BASE_URL: http://host.docker.internal:8000",
            "CODEXIFY_SUPPORTED_PROFILE: v1-local-core-web-mcp",
            "gemma-4-12b-it-qat-4bit",
        ):
            assert marker in content


class TestContractRejectsCloudProviders:
    def test_true_is_rejected(self):
        profile = _load_supported_profile()
        expected = profile["provider_contract"]["ALLOW_CLOUD_PROVIDERS"]
        assert True != expected

    def test_false_is_accepted(self):
        profile = _load_supported_profile()
        assert profile["provider_contract"]["ALLOW_CLOUD_PROVIDERS"] is False


class TestContractRejectsCloudEgress:
    def test_nonempty_is_rejected(self):
        profile = _load_supported_profile()
        expected = profile["provider_contract"]["CODEXIFY_EGRESS_ALLOWLIST"]
        assert "groq,openai,anthropic" != expected

    def test_empty_is_accepted(self):
        profile = _load_supported_profile()
        assert profile["provider_contract"]["CODEXIFY_EGRESS_ALLOWLIST"] == ""


class TestContractRequiresCorrectLocalBaseUrl:
    def test_localhost_is_rejected_in_docker(self):
        assert "http://localhost:8000/v1" != CANONICAL_BASE_URL

    def test_host_docker_internal_is_accepted(self):
        profile = _load_supported_profile()
        assert (
            profile["provider_contract"]["LOCAL_BASE_URL"] == CANONICAL_BASE_URL
        )

    def test_tailscale_ip_is_rejected(self):
        assert MACHINE_SPECIFIC_BASE_URL != CANONICAL_BASE_URL

    def test_health_url_matches_canonical_base_url(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["WHOOSHD_HEALTH_BASE_URL"] == (
            backend_env["LOCAL_BASE_URL"].removesuffix("/v1")
        )
        assert (
            backend_env["WHOOSHD_HEALTH_BASE_URL"] == CANONICAL_HEALTH_BASE_URL
        )


class TestSmokeWrapperScriptExists:
    def test_script_exists(self):
        assert SMOKE_LAUNCHER_PATH.exists()

    def test_script_is_executable(self):
        assert SMOKE_LAUNCHER_PATH.stat().st_mode & 0o111

    def test_script_references_compose_override(self):
        assert (
            "docker-compose.whooshd-smoke.yml"
            in SMOKE_LAUNCHER_PATH.read_text()
        )

    def test_launcher_script_forwards_multi_model_env(self):
        content = Path("scripts/whooshd_ensure.sh").read_text()
        assert "WHOOSHD_MODEL_REGISTRY_PATH" in content
        assert "WHOOSHD_MLX_MODEL" in content
        assert "WHOOSHD_ADAPTER" in content

    def test_script_passes_bash_syntax_check(self):
        assert SMOKE_LAUNCHER_PATH.exists()


class TestNoCloudFallback:
    def test_local_only_mode_blocks_cloud_providers(self):
        settings = _mock_settings()
        assert settings.CODEXIFY_LOCAL_ONLY_MODE is True
        assert settings.ALLOW_CLOUD_PROVIDERS is False
        assert settings.CODEXIFY_EGRESS_ALLOWLIST == ""

    def test_local_only_mode_rejects_allow_cloud_true(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract["CODEXIFY_LOCAL_ONLY_MODE"] is True
        assert contract["ALLOW_CLOUD_PROVIDERS"] is False


class TestModelPropagation:
    def test_all_smoke_models_are_propagated(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        worker_env = config["services"]["worker-chat"]["environment"]
        for key, value in CANONICAL_SMOKE_MODELS.items():
            assert backend_env[key] == value
            assert worker_env[key] == value


class TestWhooshdStaysStandalone:
    def test_no_whooshd_import_in_codexify_routes(self):
        for check_path in [
            "guardian/guardian_api.py",
            "guardian/core/config.py",
        ]:
            path = Path(check_path)
            if path.exists():
                import_lines = [
                    line.strip()
                    for line in path.read_text().splitlines()
                    if line.strip().startswith(
                        ("import whooshd", "from whooshd")
                    )
                ]
                assert (
                    not import_lines
                ), f"{check_path} imports whooshd internals: {import_lines}"

    def test_compose_override_does_not_add_whooshd_service(self):
        config = _load_smoke_override()
        for service in config["services"]:
            assert "whooshd" not in service.lower()
