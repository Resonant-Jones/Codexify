"""
Guardian Configuration Package
--------------------------
Provides system-wide configuration and settings.
"""

from guardian.config.config import Config

__all__ = ['Config']

from .settings import get_settings  # noqa: F401
