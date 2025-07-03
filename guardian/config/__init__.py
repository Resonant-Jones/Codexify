"""
Guardian Configuration Package
--------------------------
Provides system-wide configuration and settings.
"""
from .config import Config
from .settings import get_settings

__all__ = [
    'Config',
    'get_settings',
    'get_active_model',
    'get_backend_capabilities',
    'get_model_and_host',
    'is_backend_capable',
]

def get_active_model():
    """
    Returns the active model name from settings, or 'default_model' if not set.
    """
    return get_settings().get('active_model', 'default_model')

def get_backend_capabilities():
    """
    Returns the backend capabilities dict from settings, or empty dict if not set.
    """
    return get_settings().get('backend_capabilities', {})

def get_model_and_host():
    """
    Returns a tuple of (active_model, backend_host) from settings,
    with defaults if not set.
    """
    settings = get_settings()
    return (
        settings.get('active_model', 'default_model'),
        settings.get('backend_host', 'default_host'),
    )

def is_backend_capable(capability):
    """
    Check if the backend supports a given capability.
    """
    return bool(get_backend_capabilities().get(capability, False))