# guardian/config/settings.py
from typing import Any

class Config(dict):
    """Minimal dict‑backed settings container."""

    def __getattr__(self, item: str) -> Any:
        return self[item]

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

_CONFIG_SINGLETON: Config | None = None

def get_settings() -> Config:
    global _CONFIG_SINGLETON
    if _CONFIG_SINGLETON is None:
        _CONFIG_SINGLETON = Config()
    return _CONFIG_SINGLETON