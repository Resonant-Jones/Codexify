"""
Facade for Imprint Zero

Pure re-exports so tests and callers can patch on `guardian.imprint_zero`.
Exports: ImprintZero, ImprintZeroAgent, UserManager, settings, get_memoryos_instance.
"""

# Core re-exports
try:
    from .imprint_zero_onboarding import ImprintZero, ImprintZeroAgent  # type: ignore
except Exception:
    class ImprintZero:  # type: ignore
        ...

    class ImprintZeroAgent:  # type: ignore
        ...

# Patch points expected by tests
try:
    from .imprint_zero_onboarding import UserManager, settings, get_memoryos_instance  # type: ignore
except Exception:
    class UserManager:  # type: ignore
        ...

    class _Settings:  # type: ignore
        PROMPT_DIR_PATH = None

    settings = _Settings()  # type: ignore

    def get_memoryos_instance():  # type: ignore
        return None

__all__ = [
    "ImprintZero",
    "ImprintZeroAgent",
    "UserManager",
    "settings",
    "get_memoryos_instance",
]
