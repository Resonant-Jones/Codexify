import pytest

from guardian.core.config import Settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed


def test_egress_denied_when_local_only_mode_enabled() -> None:
    settings = Settings(
        CODEXIFY_LOCAL_ONLY_MODE=True,
        CODEXIFY_EGRESS_ALLOWLIST="openai",
        ALLOW_CLOUD_PROVIDERS=True,
    )
    with pytest.raises(EgressDeniedError, match="LOCAL_ONLY_MODE"):
        assert_egress_allowed("openai", settings=settings)


def test_egress_denied_when_allowlist_missing_target() -> None:
    settings = Settings(
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="webhook",
        ALLOW_CLOUD_PROVIDERS=True,
    )
    with pytest.raises(EgressDeniedError, match="ALLOWLIST"):
        assert_egress_allowed("openai", settings=settings)


def test_cloud_egress_requires_allow_cloud_providers() -> None:
    settings = Settings(
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="openai",
        ALLOW_CLOUD_PROVIDERS=False,
    )
    with pytest.raises(EgressDeniedError, match="ALLOW_CLOUD_PROVIDERS"):
        assert_egress_allowed("openai", settings=settings)


def test_minimax_egress_requires_allow_cloud_providers() -> None:
    settings = Settings(
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="minimax",
        ALLOW_CLOUD_PROVIDERS=False,
    )
    with pytest.raises(EgressDeniedError, match="ALLOW_CLOUD_PROVIDERS"):
        assert_egress_allowed("minimax", settings=settings)


def test_webhook_egress_allowed_with_explicit_opt_in() -> None:
    settings = Settings(
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="webhook",
        ALLOW_CLOUD_PROVIDERS=False,
    )
    assert_egress_allowed("webhook", settings=settings)
