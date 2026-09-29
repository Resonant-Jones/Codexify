"""Compatibility import for the canonical Guardian model-override router.

Runtime registration belongs to ``guardian.routes.llm_overrides``.
"""

from guardian.routes.llm_overrides import router

__all__ = ["router"]
