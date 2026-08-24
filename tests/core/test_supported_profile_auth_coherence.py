from types import SimpleNamespace

from guardian.core.supported_profile import (
    load_supported_profile,
    validate_supported_profile_runtime,
)


def _settings(**overrides):
    values = {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
        "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_COMPAT_FIRST": True,
        "LOCAL_PROVIDER_DISPLAY_NAME": "Whoosh'd",
        "LOCAL_PROVIDER_VENDOR": "whooshd",
        "LOCAL_LLM_MODEL": "",
        "LOCAL_CHAT_MODEL": "",
        "DEEPSEEK_CHAT_MODEL": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_local_profile_with_local_auth_is_valid(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")

    mismatches = validate_supported_profile_runtime(
        load_supported_profile("v1-local-core-web-mcp"), settings=_settings()
    )

    assert mismatches == []


def test_local_profile_rejects_remote_auth_when_auth_is_quarantined(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")

    mismatches = validate_supported_profile_runtime(
        load_supported_profile("v1-local-core-web-mcp"), settings=_settings()
    )

    assert len(mismatches) == 1
    assert "GUARDIAN_AUTH_MODE='remote'" in mismatches[0]
    assert "v1-local-core-web-mcp" in mismatches[0]
    assert "quarantines 'auth'" in mismatches[0]


def test_tester_profile_with_remote_auth_remains_valid(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")

    mismatches = validate_supported_profile_runtime(
        load_supported_profile("v1-friends-family-web"),
        settings=_settings(
            LLM_PROVIDER="deepseek",
            ALLOW_CLOUD_PROVIDERS=True,
            CODEXIFY_LOCAL_ONLY_MODE=False,
            CODEXIFY_EGRESS_ALLOWLIST="deepseek",
            LOCAL_RUNTIME_PRESET="",
            LOCAL_COMPAT_FIRST=False,
            LOCAL_PROVIDER_DISPLAY_NAME="",
            LOCAL_PROVIDER_VENDOR="",
        ),
    )

    assert mismatches == []
