"""Resumable import checkpointing for archive-scale OpenAI exports.

Provides file-based checkpoint state so an interrupted import can
continue from the last completed conversation without duplicating data.

Checkpoints are persisted as newline-delimited JSON records in a single
log file under the diagnostic output directory.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CHECKPOINT_FILE_NAME = "import_checkpoint.ndjson"


@dataclass
class CheckpointRecord:
    """One checkpoint entry for a single imported conversation."""

    import_run_id: str
    archive_path: str
    source_file: str
    conversation_id: str
    status: str  # pending | imported | failed | skipped
    started_at: str = ""
    updated_at: str = ""
    error: str = ""
    messages_imported: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "import_run_id": self.import_run_id,
            "archive_path": self.archive_path,
            "source_file": self.source_file,
            "conversation_id": self.conversation_id,
            "status": self.status,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "messages_imported": self.messages_imported,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CheckpointRecord":
        return CheckpointRecord(
            import_run_id=str(data.get("import_run_id", "")),
            archive_path=str(data.get("archive_path", "")),
            source_file=str(data.get("source_file", "")),
            conversation_id=str(data.get("conversation_id", "")),
            status=str(data.get("status", "pending")),
            started_at=str(data.get("started_at", "")),
            updated_at=str(data.get("updated_at", "")),
            error=str(data.get("error", "")),
            messages_imported=int(data.get("messages_imported", 0)),
        )


class ImportCheckpointManager:
    """File-based checkpoint log for resumable imports."""

    def __init__(self, checkpoint_dir: str | Path) -> None:
        self._dir = Path(checkpoint_dir).expanduser().resolve()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / _CHECKPOINT_FILE_NAME
        self._run_id: str = ""
        self._completed: set[str] = set()

    @property
    def run_id(self) -> str:
        return self._run_id

    def start_run(self, archive_path: str) -> str:
        """Start a new import run. Returns the run id."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        # Use the archive path stem as a stable run label.
        label = Path(archive_path).name.replace(" ", "_")[:40]
        self._run_id = f"{ts}-{label}"
        self._completed = set()
        logger.info("Import checkpoint run started: %s", self._run_id)
        return self._run_id

    def load_completed(self) -> set[str]:
        """Load conversation_ids already imported in this run."""
        if self._completed:
            return self._completed

        if not self._path.exists():
            return self._completed

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = CheckpointRecord.from_dict(json.loads(line))
                    except Exception:
                        continue
                    if (
                        record.import_run_id == self._run_id
                        and record.status == "imported"
                    ):
                        self._completed.add(record.conversation_id)
        except Exception as exc:
            logger.warning(
                "Failed to load checkpoint file: %s", exc
            )
        return self._completed

    def mark_imported(
        self,
        conversation_id: str,
        source_file: str = "",
        messages_imported: int = 0,
    ) -> None:
        """Record a successfully imported conversation."""
        self._write(
            CheckpointRecord(
                import_run_id=self._run_id,
                archive_path="",
                source_file=source_file,
                conversation_id=conversation_id,
                status="imported",
                started_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                messages_imported=messages_imported,
            )
        )
        self._completed.add(conversation_id)

    def mark_failed(
        self, conversation_id: str, source_file: str = "", error: str = ""
    ) -> None:
        """Record a conversation that failed during import."""
        self._write(
            CheckpointRecord(
                import_run_id=self._run_id,
                archive_path="",
                source_file=source_file,
                conversation_id=conversation_id,
                status="failed",
                started_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                error=error[:500] if error else "",
            )
        )

    def mark_skipped(
        self, conversation_id: str, source_file: str = "", reason: str = ""
    ) -> None:
        """Record a conversation skipped (e.g., empty, duplicate)."""
        self._write(
            CheckpointRecord(
                import_run_id=self._run_id,
                archive_path="",
                source_file=source_file,
                conversation_id=conversation_id,
                status="skipped",
                started_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                error=reason[:500] if reason else "",
            )
        )

    def is_completed(self, conversation_id: str) -> bool:
        """Check if a conversation has already been imported."""
        return conversation_id in self._completed

    def summary(self) -> dict[str, int]:
        """Return a quick summary of checkpoint state."""
        if not self._path.exists():
            return {"imported": 0, "failed": 0, "skipped": 0, "total": 0}

        imported = 0
        failed = 0
        skipped = 0
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue
                    if record.get("import_run_id") != self._run_id:
                        continue
                    status = record.get("status")
                    if status == "imported":
                        imported += 1
                    elif status == "failed":
                        failed += 1
                    elif status == "skipped":
                        skipped += 1
        except Exception:
            pass

        return {
            "imported": imported,
            "failed": failed,
            "skipped": skipped,
            "total": imported + failed + skipped,
        }

    def _write(self, record: CheckpointRecord) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(record.to_dict(), sort_keys=True) + "\n"
                )
        except Exception as exc:
            logger.error("Failed to write checkpoint: %s", exc)


def resolve_checkpoint_path(
    cli_path: str | None = None,
    diagnostic_dir: str | Path | None = None,
) -> Path:
    """Resolve the checkpoint directory from CLI flag or diagnostic dir."""
    if cli_path:
        return Path(cli_path).expanduser().resolve()
    if diagnostic_dir:
        return Path(diagnostic_dir).expanduser().resolve()
    return Path("logs/openai_import").expanduser().resolve()
