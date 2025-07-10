# guardian/config/settings.py
from typing import Any


class RuntimeConfig(dict):
    """Minimal dict‑backed settings container for dynamic runtime tweaks."""

    def __getattr__(self, item: str) -> Any:
        return self[item]

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


_RuntimeConfig_SINGLETON: RuntimeConfig | None = None


def get_settings() -> RuntimeConfig:
    global _RuntimeConfig_SINGLETON
    if _RuntimeConfig_SINGLETON is None:
        _RuntimeConfig_SINGLETON = RuntimeConfig()
    return _RuntimeConfig_SINGLETON
