"""Concrete sandbox provider adapters.

Adapters are imported lazily by
:func:`guardian.sandbox.registry._builtin_factories` so that importing the
sandbox package does not pull in provider-specific dependencies.
"""

from __future__ import annotations

__all__: list[str] = []
