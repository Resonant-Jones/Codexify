from guardian.core.config import Settings
from guardian.core.provider_truth import (
    _cloud_capable_configuration_present,
    provider_configured,
)


def _settings(**overrides) -> Settings:
    defaults = {
        "OPENAI_API_KEY": None,
        "GROQ_API_KEY": None,
        "ALIBABA_API_KEY": None,
        "MINIMAX_API_KEY": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_cloud_capable_configuration_ignores_bundled_cloud_base_defaults():
    settings = _settings()

    assert provider_configured("alibaba", settings) is False
    assert provider_configured("minimax", settings) is False
    assert _cloud_capable_configuration_present(settings) is False


def test_cloud_capable_configuration_detects_explicit_cloud_credentials():
    settings = _settings(
        MINIMAX_API_KEY="minimax-key",
        MINIMAX_API_BASE="https://api.minimax.local/v1",
    )

    assert provider_configured("minimax", settings) is True
    assert _cloud_capable_configuration_present(settings) is True
