from guardian.core.local_runtime_presets import (
    default_local_runtime_preset_id,
    local_runtime_env_defaults,
    normalize_local_runtime_preset,
)


def test_default_local_runtime_preset_prefers_whooshd_on_apple_silicon() -> None:
    assert (
        default_local_runtime_preset_id(
            system_name="Darwin",
            machine="arm64",
        )
        == "whooshd-mlx"
    )


def test_default_local_runtime_preset_prefers_ollama_off_mac() -> None:
    assert (
        default_local_runtime_preset_id(
            system_name="Linux",
            machine="x86_64",
        )
        == "ollama"
    )


def test_lmstudio_preset_supplies_docker_openai_compatible_defaults() -> None:
    defaults = local_runtime_env_defaults("lmstudio", docker=True)

    assert defaults["LOCAL_RUNTIME_PRESET"] == "lmstudio"
    assert defaults["LOCAL_BASE_URL"] == "http://host.docker.internal:1234/v1"
    assert defaults["LOCAL_PROVIDER_DISPLAY_NAME"] == "LM Studio"
    assert defaults["LOCAL_PROVIDER_VENDOR"] == "lmstudio"
    assert defaults["LOCAL_CHAT_MODEL"] == "local-model"
    assert defaults["VAULTNODE_BASE_URL"] == "http://host.docker.internal:1234"


def test_common_preset_aliases_normalize_to_canonical_ids() -> None:
    assert normalize_local_runtime_preset("lm-studio") == "lmstudio"
    assert normalize_local_runtime_preset("whooshd") == "whooshd-mlx"


def test_whooshd_preset_configures_llama_without_claiming_live_inventory() -> None:
    defaults = local_runtime_env_defaults("whooshd-mlx", docker=True)

    assert defaults["LOCAL_RUNTIME_PRESET"] == "whooshd-mlx"
    assert defaults["LOCAL_PROVIDER_VENDOR"] == "whooshd"
    assert defaults["LOCAL_BASE_URL"] == "http://host.docker.internal:8000/v1"
    assert defaults["LOCAL_CHAT_MODEL"] == (
        "mlx-community/Llama-3.2-3B-Instruct-4bit"
    )
    assert "/v1/models" in defaults["VAULTNODE_HEALTH_ENDPOINTS"]
    assert "/api/tags" in defaults["VAULTNODE_HEALTH_ENDPOINTS"]


def test_unknown_preset_normalizes_to_supported_default() -> None:
    assert normalize_local_runtime_preset("not-a-runtime") == "whooshd-mlx"
