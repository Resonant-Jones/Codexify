"""
Guardian Configuration Package
--------------------------
Provides system-wide configuration and settings.
"""

from .core import (
    Settings as Config,
    get_active_model,
    get_backend_capabilities,
    get_model_and_host,
    is_backend_capable,
    is_cloud_backend,
)
from .system_config import system_config, SystemConfig
from guardian.config.core import get_settings

__all__ = [
    "Config",
    "system_config",
    "SystemConfig",
    "get_settings",
    "get_active_model",
    "get_backend_capabilities",
    "get_model_and_host",
    "is_backend_capable",
    "is_cloud_backend",
]
