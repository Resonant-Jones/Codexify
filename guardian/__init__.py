"""
Guardian package initializer
-----------------------------
Exposes core modules and configuration helpers.
"""

from .utils.log_safety import install_safe_logging

install_safe_logging()

# Expose Imprint Zero façade and full onboarding modules
from . import imprint_zero  # noqa: E402
from .config.core import Config, get_settings, is_cloud_backend  # noqa: E402
from .config.system_config import system_config  # noqa: E402

# from . import imprint_zero_onboarding

__all__ = [
    "Config",
    "get_settings",
    "is_cloud_backend",
    "system_config",
    "imprint_zero",
    "imprint_zero_onboarding",
]
