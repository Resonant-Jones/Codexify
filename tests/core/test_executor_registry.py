from __future__ import annotations

import pytest

from guardian.core.executors.registry import (
    ExecutorAuthMode,
    ExecutorCapability,
    ExecutorId,
    ExecutorReleasePosture,
    get_executor_entry,
    get_executor_registry,
    is_supported_executor,
)


def test_executor_registry_contains_expected_executor_ids() -> None:
    registry = get_executor_registry()

    assert isinstance(registry, tuple)
    assert [entry.executor_id.value for entry in registry] == [
        "codex",
        "claude_code",
        "opencode",
    ]


def test_executor_entry_lookup_works() -> None:
    entry = get_executor_entry(ExecutorId.CODEX)

    assert entry.install_label == "Codex CLI"
    assert entry.binary_env_var == "CODEXIFY_CODEX_BIN"
    assert entry.supported_auth_modes == (
        ExecutorAuthMode.DIRECT_PROVIDER,
        ExecutorAuthMode.GATEWAY_BASE_URL,
    )
    assert entry.capability == ExecutorCapability(
        supports_direct_provider_config=True,
        supports_local_models=False,
        supports_gateway_base_url_routing=True,
        supports_structured_escalations=True,
    )


def test_unsupported_executor_ids_fail_cleanly() -> None:
    with pytest.raises(KeyError, match="unknown executor: not_real"):
        get_executor_entry("not-real")

    assert is_supported_executor("not-real") is False


@pytest.mark.parametrize(
    "executor_id, release_posture, auth_modes, capability",
    [
        (
            ExecutorId.CODEX,
            ExecutorReleasePosture.OFFICIAL,
            (
                ExecutorAuthMode.DIRECT_PROVIDER,
                ExecutorAuthMode.GATEWAY_BASE_URL,
            ),
            ExecutorCapability(
                supports_direct_provider_config=True,
                supports_local_models=False,
                supports_gateway_base_url_routing=True,
                supports_structured_escalations=True,
            ),
        ),
        (
            ExecutorId.CLAUDE_CODE,
            ExecutorReleasePosture.OPTIONAL,
            (
                ExecutorAuthMode.DIRECT_PROVIDER,
                ExecutorAuthMode.GATEWAY_BASE_URL,
            ),
            ExecutorCapability(
                supports_direct_provider_config=True,
                supports_local_models=False,
                supports_gateway_base_url_routing=True,
                supports_structured_escalations=True,
            ),
        ),
        (
            ExecutorId.OPENCODE,
            ExecutorReleasePosture.OPTIONAL,
            (
                ExecutorAuthMode.DIRECT_PROVIDER,
                ExecutorAuthMode.LOCAL_MODEL,
                ExecutorAuthMode.GATEWAY_BASE_URL,
            ),
            ExecutorCapability(
                supports_direct_provider_config=True,
                supports_local_models=True,
                supports_gateway_base_url_routing=True,
                supports_structured_escalations=True,
            ),
        ),
    ],
)
def test_executor_capability_flags_are_stable(
    executor_id,
    release_posture,
    auth_modes,
    capability,
) -> None:
    entry = get_executor_entry(executor_id)

    assert entry.release_posture == release_posture
    assert entry.supported_auth_modes == auth_modes
    assert entry.capability == capability
    assert (
        entry.supports_direct_provider_config
        == capability.supports_direct_provider_config
    )
    assert entry.supports_local_models == capability.supports_local_models
    assert (
        entry.supports_gateway_base_url_routing
        == capability.supports_gateway_base_url_routing
    )
    assert (
        entry.supports_structured_escalations
        == capability.supports_structured_escalations
    )
