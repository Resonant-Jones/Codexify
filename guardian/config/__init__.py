"""
Guardian Configuration Package
--------------------------
Provides system-wide configuration and settings.
"""

from guardian.config.core import get_settings

from .core import Settings as Config
from .core import (
    get_active_model,
    get_backend_capabilities,
    get_model_and_host,
    is_backend_capable,
    is_cloud_backend,
)
from .system_config import SystemConfig, system_config

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
