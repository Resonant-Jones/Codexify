"""Persistent store for document diff history and version tracking.

Maintains per-document version history allowing nodes to resync
after periods of offline time.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict, field

from .diff_engine import DiffEntry

logger = logging.getLogger(__name__)


@dataclass
class DocumentVersion:
    """Represents a document version in the store."""

    doc_id: str
    version: int
    content: str
    content_hash: str
    created_by: str
    created_at: str  # ISO format
    diffs_applied: List[str] = field(default_factory=list)  # List of diff checksums


class DiffStore:
    """Persistent store for document diffs and version history.

    Tracks per-document versions, maintains version history, and
    enables efficient synchronization across federated nodes.
    """

    def __init__(self, store_path: Optional[str] = None):
        """Initialize the diff store.

        Args:
            store_path: Path to store directory (creates if not exists)
        """
        if store_path:
            self.store_path = Path(store_path)
        else:
            self.store_path = Path(".") / ".codexify" / "diffs"

        self.store_path.mkdir(parents=True, exist_ok=True)

        # In-memory index: doc_id -> latest version info
        self._index: Dict[str, Dict] = {}
        self._load_index()

    def _index_path(self, doc_id: str) -> Path:
        """Get path to document's index file."""
        return self.store_path / f"{doc_id}.json"

    def _load_index(self) -> None:
        """Load in-memory index from persistent storage."""
        for index_file in self.store_path.glob("*.json"):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    doc_id = data.get("doc_id")
                    if doc_id:
                        self._index[doc_id] = data
            except Exception as e:
                logger.warning(f"Failed to load index {index_file}: {e}")

    def _save_index(self, doc_id: str) -> None:
        """Save document index to persistent storage."""
        try:
            index_file = self._index_path(doc_id)
            with open(index_file, "w") as f:
                json.dump(self._index[doc_id], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index for {doc_id}: {e}")

    def record_diff(self, diff: DiffEntry, resulting_content: str) -> None:
        """Record a new diff and update document version.

        Args:
            diff: DiffEntry to record
            resulting_content: Document content after applying diff
        """
        doc_id = diff.doc_id

        # Initialize document index if needed
        if doc_id not in self._index:
            self._index[doc_id] = {
                "doc_id": doc_id,
                "latest_version": 0,
                "diffs": [],
            }

        # Record the diff
        diff_record = {
            "version": diff.version,
            "author": diff.author,
            "timestamp": diff.timestamp.isoformat(),
            "content_hash": diff.content_hash,
            "patch_checksum": hashlib.sha256(diff.patch.encode()).hexdigest()[:16],
        }

        self._index[doc_id]["diffs"].append(diff_record)
        self._index[doc_id]["latest_version"] = diff.version
        self._index[doc_id]["latest_content"] = resulting_content
        self._index[doc_id]["latest_updated"] = datetime.now(timezone.utc).isoformat()

        self._save_index(doc_id)

        logger.info(
            f"Recorded diff for {doc_id} v{diff.version} by {diff.author}"
        )

    def get_latest_version(self, doc_id: str) -> Optional[int]:
        """Get the latest version number for a document.

        Args:
            doc_id: Document ID

        Returns:
            Latest version number, or None if document not found
        """
        if doc_id in self._index:
            return self._index[doc_id].get("latest_version")
        return None

    def get_latest_content(self, doc_id: str) -> Optional[str]:
        """Get the latest content for a document.

        Args:
            doc_id: Document ID

        Returns:
            Latest document content, or None if not found
        """
        if doc_id in self._index:
            return self._index[doc_id].get("latest_content")
        return None

    def get_diffs_since(self, doc_id: str, since_version: int) -> List[DiffEntry]:
        """Get all diffs for a document since a given version.

        Used for resynchronization after offline periods.

        Args:
            doc_id: Document ID
            since_version: Get diffs with version > this

        Returns:
            List of DiffEntry objects in version order
        """
        if doc_id not in self._index:
            return []

        diffs = []
        for diff_record in self._index[doc_id].get("diffs", []):
            if diff_record["version"] > since_version:
                # Reconstruct DiffEntry from record
                # Note: We don't have the full patch stored, just metadata
                diff = DiffEntry(
                    doc_id=doc_id,
                    version=diff_record["version"],
                    patch="",  # Patch is in separate storage or reconstructed
                    author=diff_record["author"],
                    timestamp=datetime.fromisoformat(diff_record["timestamp"]),
                    content_hash=diff_record.get("content_hash"),
                    base_version=diff_record.get("base_version", 0),
                )
                diffs.append(diff)

        return sorted(diffs, key=lambda d: d.version)

    def get_all_versions(self, doc_id: str) -> List[Dict]:
        """Get all version records for a document.

        Args:
            doc_id: Document ID

        Returns:
            List of version metadata dicts
        """
        if doc_id in self._index:
            return self._index[doc_id].get("diffs", [])
        return []

    def exists(self, doc_id: str) -> bool:
        """Check if document exists in store.

        Args:
            doc_id: Document ID

        Returns:
            True if document has version history
        """
        return doc_id in self._index

    def get_statistics(self, doc_id: str) -> Dict:
        """Get statistics about a document's history.

        Args:
            doc_id: Document ID

        Returns:
            Dict with version count, authors, date range, etc.
        """
        if doc_id not in self._index:
            return {"exists": False}

        index_data = self._index[doc_id]
        diffs = index_data.get("diffs", [])

        authors = set()
        timestamps = []

        for diff in diffs:
            authors.add(diff["author"])
            ts = datetime.fromisoformat(diff["timestamp"])
            timestamps.append(ts)

        return {
            "exists": True,
            "doc_id": doc_id,
            "latest_version": index_data.get("latest_version"),
            "total_diffs": len(diffs),
            "unique_authors": len(authors),
            "authors": list(authors),
            "date_range": {
                "first": min(timestamps).isoformat() if timestamps else None,
                "last": max(timestamps).isoformat() if timestamps else None,
            },
        }


# Global store instance
import hashlib

_store: Optional[DiffStore] = None


def get_diff_store(store_path: Optional[str] = None) -> DiffStore:
    """Get or create the global diff store instance.

    Args:
        store_path: Optional path to store directory

    Returns:
        DiffStore instance
    """
    global _store
    if _store is None:
        _store = DiffStore(store_path)
    return _store
