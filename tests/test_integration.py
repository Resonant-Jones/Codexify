import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]

# ---------------------------------------------------------------------------
# Legacy‑compat shims
# ---------------------------------------------------------------------------
# Older tests expect two public symbols on `guardian.config`:
#   • Config          – a simple dictionary‑style settings object
#   • get_settings()  – a singleton accessor
# If the real settings backend hasn’t been wired yet, provide a minimal
# fallback so the test suite can import without exploding. Replace this shim
# with the full implementation when the real config module lands.
from typing import Any

class Config(dict):
    """Minimal dict‑backed settings container (legacy shim)."""

    def __getattr__(self, item: str) -> Any:  # noqa: D401
        return self[item]

    def __setattr__(self, key: str, value: Any) -> None:  # noqa: D401
        self[key] = value


_CONFIG_SINGLETON: Config | None = None


def get_settings() -> Config:  # type: ignore[valid-type]
    """Return a singleton Config instance (legacy shim)."""
    global _CONFIG_SINGLETON
    if _CONFIG_SINGLETON is None:
        _CONFIG_SINGLETON = Config()
    return _CONFIG_SINGLETON