"""Companion Foresight
====================

Ephemeral module that generates simple "what's next" suggestions
from recent narratives. Predictions are not persisted.

Usage example::

    from guardian.modules.companion_foresight import Foresight, PredictionRequest

    foresight = Foresight()
    suggestion = foresight.predict_next(PredictionRequest(recent_narratives=["Went jogging"]))
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Input schema for foresight predictions."""

    recent_narratives: List[str] = Field(..., description="Recent narrative texts")


class Foresight:
    """Simple foresight engine with ephemeral outputs."""

    def predict_next(self, request: PredictionRequest) -> str:
        """Return a naive prediction based on the last narrative."""
        if not request.recent_narratives:
            return "No recent narratives to analyse."
        last = request.recent_narratives[-1]
        # Ephemeral processing only – result is not stored
        return f"Based on '{last}', you might consider reflecting or planning ahead."
