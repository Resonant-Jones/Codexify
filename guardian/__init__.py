"""
Guardian package initializer
-----------------------------
Exposes core modules and configuration helpers.
"""

from .config.core import Config, get_settings, is_cloud_backend
from .config.system_config import system_config

# Expose Imprint Zero façade and full onboarding modules
from . import imprint_zero
#from . import imprint_zero_onboarding

__all__ = [
    "Config",
    "get_settings",
    "is_cloud_backend",
    "system_config",
    "imprint_zero",
    "imprint_zero_onboarding",
]
