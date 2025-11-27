"""Guardian scheduler wrapper.

Provides a resilient interface around APScheduler so system components can
schedule recurring jobs without depending on APScheduler at runtime.  When the
library is available we delegate to :class:`BackgroundScheduler`.  Otherwise we
fall back to a lightweight implementation that executes the job once
immediately so critical tasks still run during development or testing.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from apscheduler.schedulers.background import (
        BackgroundScheduler,  # type: ignore
    )
except Exception:  # pragma: no cover - gracefully degrade when missing
    BackgroundScheduler = None  # type: ignore[misc,assignment]


class _FallbackJob:
    """Minimal object that mimics the APScheduler job interface."""

    def __init__(self, job_id: str):
        self.id = job_id

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<FallbackJob id={self.id!r}>"


class _GuardianScheduler:
    """Singleton-style scheduler facade."""

    def __init__(self) -> None:
        self._scheduler: Any | None = None

        if BackgroundScheduler is not None:
            try:
                self._scheduler = BackgroundScheduler()
                self._scheduler.start()
                logger.info("[scheduler] BackgroundScheduler started")
            except Exception:  # pragma: no cover - defensive logging
                logger.exception(
                    "[scheduler] Failed to start APScheduler background scheduler"
                )
                self._scheduler = None
        else:
            logger.warning(
                "[scheduler] APScheduler not available; falling back to single-run execution"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_job(
        self, func: Callable[..., Any], trigger: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Add a job to the underlying scheduler.

        When APScheduler is available we delegate directly to the real scheduler.
        Otherwise we execute the job in a daemon thread immediately and return a
        lightweight handle so callers receive consistent logging.
        """

        job_id = kwargs.get("id") or getattr(func, "__name__", "job")

        if self._scheduler is not None:
            if trigger == "cron" and "next_run_time" not in kwargs:
                # Execute once right after startup so tests and telemetry see output.
                kwargs["next_run_time"] = datetime.now()
            job = self._scheduler.add_job(func, trigger, *args, **kwargs)
            logger.info('Added job "%s" (trigger=%s)', job_id, trigger)
            return job

        # Fallback behaviour: run job immediately on a background thread.
        def _runner() -> None:
            try:
                func()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("[scheduler] Fallback job '%s' failed", job_id)

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        logger.info(
            'Executed fallback job "%s" immediately (trigger=%s)',
            job_id,
            trigger,
        )
        return _FallbackJob(job_id)


# Module-level singleton instance
scheduler = _GuardianScheduler()

__all__ = ["scheduler"]
