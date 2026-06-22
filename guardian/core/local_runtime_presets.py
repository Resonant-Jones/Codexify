from __future__ import annotations

import platform
from dataclasses import dataclass


WHOOSHD_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"
WHOOSHD_ALIAS_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"
WHOOSHD_GGUF_MODEL = "qwen2.5-0.5b-gguf"
WHOOSHD_VISION_MODEL = "qwen2-vl-2b-mlx"
OLLAMA_MODEL = "llama3.2:latest"
CUSTOM_LOCAL_MODEL = "local-model"


@dataclass(frozen=True)
class LocalRuntimePreset:
    id: str
    display_name: str
    vendor: str
    base_url: str
    docker_base_url: str
    vaultnode_base_url: str
    default_model: str
    compat_first: bool = True
    health_endpoints: str = "/v1/models,/api/tags"


LOCAL_RUNTIME_PRESETS: dict[str, LocalRuntimePreset] = {
    "whooshd-mlx": LocalRuntimePreset(
        id="whooshd-mlx",
        display_name="Whoosh'd",
        vendor="whooshd",
        base_url="http://127.0.0.1:8000/v1",
        docker_base_url="http://host.docker.internal:8000/v1",
        vaultnode_base_url="http://host.docker.internal:8000",
        default_model=WHOOSHD_ALIAS_MODEL,
        health_endpoints="/health,/health/runtime,/ready,/v1/models,/api/tags",
    ),
    "ollama": LocalRuntimePreset(
        id="ollama",
        display_name="Ollama",
        vendor="ollama",
        base_url="http://127.0.0.1:11434/v1",
        docker_base_url="http://host.docker.internal:11434/v1",
        vaultnode_base_url="http://host.docker.internal:11434",
        default_model=OLLAMA_MODEL,
    ),
    "lmstudio": LocalRuntimePreset(
        id="lmstudio",
        display_name="LM Studio",
        vendor="lmstudio",
        base_url="http://127.0.0.1:1234/v1",
        docker_base_url="http://host.docker.internal:1234/v1",
        vaultnode_base_url="http://host.docker.internal:1234",
        default_model=CUSTOM_LOCAL_MODEL,
    ),
    "custom-openai-compatible": LocalRuntimePreset(
        id="custom-openai-compatible",
        display_name="Custom Local",
        vendor="custom-openai-compatible",
        base_url="http://127.0.0.1:8000/v1",
        docker_base_url="http://host.docker.internal:8000/v1",
        vaultnode_base_url="http://host.docker.internal:8000",
        default_model=CUSTOM_LOCAL_MODEL,
    ),
}

LOCAL_RUNTIME_PRESET_ALIASES: dict[str, str] = {
    "whooshd": "whooshd-mlx",
    "whooshd_mlx": "whooshd-mlx",
    "whooshd mlx": "whooshd-mlx",
    "lm-studio": "lmstudio",
    "lm_studio": "lmstudio",
    "lm studio": "lmstudio",
    "custom": "custom-openai-compatible",
    "openai-compatible": "custom-openai-compatible",
    "custom-openai": "custom-openai-compatible",
}


DEFAULT_LOCAL_RUNTIME_PRESET = "whooshd-mlx"
NON_MAC_LOCAL_RUNTIME_PRESET = "ollama"


def normalize_local_runtime_preset(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in LOCAL_RUNTIME_PRESETS:
        return normalized
    if normalized in LOCAL_RUNTIME_PRESET_ALIASES:
        return LOCAL_RUNTIME_PRESET_ALIASES[normalized]
    return DEFAULT_LOCAL_RUNTIME_PRESET


def default_local_runtime_preset_id(
    *,
    system_name: str | None = None,
    machine: str | None = None,
) -> str:
    system = (system_name or platform.system()).strip().lower()
    arch = (machine or platform.machine()).strip().lower()
    if system == "darwin" and arch in {"arm64", "aarch64"}:
        return DEFAULT_LOCAL_RUNTIME_PRESET
    return NON_MAC_LOCAL_RUNTIME_PRESET


def local_runtime_preset(value: str | None) -> LocalRuntimePreset:
    return LOCAL_RUNTIME_PRESETS[normalize_local_runtime_preset(value)]


def local_runtime_env_defaults(
    preset_id: str | None,
    *,
    docker: bool = True,
) -> dict[str, str]:
    preset = local_runtime_preset(preset_id)
    base_url = preset.docker_base_url if docker else preset.base_url
    return {
        "LOCAL_RUNTIME_PRESET": preset.id,
        "LOCAL_BASE_URL": base_url,
        "LOCAL_DOCKER_FALLBACK_BASE_URL": preset.docker_base_url,
        "LOCAL_PROVIDER_DISPLAY_NAME": preset.display_name,
        "LOCAL_PROVIDER_VENDOR": preset.vendor,
        "LOCAL_LLM_MODEL": preset.default_model,
        "LOCAL_CHAT_MODEL": preset.default_model,
        "LLM_MODEL": preset.default_model,
        "LOCAL_COMPAT_FIRST": "1" if preset.compat_first else "0",
        "LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK": "0",
        "VAULTNODE_BASE_URL": preset.vaultnode_base_url,
        "VAULTNODE_HEALTH_ENDPOINTS": preset.health_endpoints,
    }
