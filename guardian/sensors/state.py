from __future__ import annotations

import os
import threading
from typing import Any, Dict, List


class Sensors:
    """Lightweight sensor snapshot provider (no psutil dependency)."""

    def __init__(self, chatlog_db=None):
        self.chatlog = chatlog_db

    def _cpu_percent(self) -> float:
        try:
            avg1, _avg5, _avg15 = os.getloadavg()
            cpus = os.cpu_count() or 1
            return float(min(100.0, max(0.0, (avg1 / max(1, cpus)) * 100.0)))
        except Exception:
            return 0.0

    def _mem_percent(self) -> float:
        try:
            import resource  # type: ignore

            r = resource.getrusage(resource.RUSAGE_SELF)
            rss_mb = float(getattr(r, "ru_maxrss", 0)) / 1024.0
            return min(100.0, max(0.0, rss_mb))
        except Exception:
            return 0.0

    def _connectors(self) -> List[str]:
        try:
            if self.chatlog is None:
                return []
            rows = self.chatlog.list_connector_configs()
            return [str(r.get("name") or r.get("id")) for r in rows]
        except Exception:
            return []

    def snapshot(self) -> Dict[str, Any]:
        try:
            threads_open = threading.active_count()
        except Exception:
            threads_open = 0

        return {
            "cpu": self._cpu_percent(),
            "memory": self._mem_percent(),
            "connectors": self._connectors(),
            "threads_open": threads_open,
            "last_event": None,
        }

