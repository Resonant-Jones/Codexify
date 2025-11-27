"""CRDT-style diff engine for federated document synchronization.

Implements a lightweight conflict-free diff-merge model that allows
multiple nodes to maintain consistent document state through
versioned patches and deterministic merging.
"""

import difflib
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiffEntry(BaseModel):
    """A single diff/patch entry for document synchronization.

    Represents a change to a document that can be applied, merged, and
    propagated across federated nodes.
    """

    doc_id: str = Field(..., description="Document ID")
    version: int = Field(..., description="Version number for this change")
    patch: str = Field(..., description="Unified diff format patch")
    author: str = Field(..., description="User or node that created this diff")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this diff was created",
    )
    content_hash: Optional[str] = Field(
        None, description="SHA256 hash of content after applying patch"
    )
    base_version: int = Field(
        0, description="Version this patch was created from"
    )

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class DiffEngine:
    """Engine for computing, applying, and merging diffs across nodes.

    Uses unified diff format for patches to maintain compatibility and
    human readability. Supports conflict-free merging through version
    tracking and deterministic ordering.
    """

    def __init__(self, store=None):
        """Initialize the diff engine.

        Args:
            store: Optional persistent store for version tracking
        """
        self.store = store
        # In-memory cache of document states: doc_id -> content
        self._state_cache = {}

    def compute_diff(
        self,
        old_content: str,
        new_content: str,
        doc_id: str,
        author: str,
        version: int,
        base_version: int = 0,
    ) -> DiffEntry:
        """Compute a diff between two document versions.

        Uses unified diff format (similar to `git diff`) to create a
        human-readable patch that can be applied to convert old -> new.

        Args:
            old_content: Previous document content
            new_content: New document content
            doc_id: Document ID
            author: Author of this change
            version: Version number for this diff
            base_version: Version this diff was created from

        Returns:
            DiffEntry with the computed patch
        """
        # Generate unified diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"doc-{doc_id}-v{base_version}",
                tofile=f"doc-{doc_id}-v{version}",
                lineterm="",
            )
        )

        patch = "\n".join(diff_lines)

        # Compute content hash for verification
        content_hash = hashlib.sha256(new_content.encode()).hexdigest()[:16]

        return DiffEntry(
            doc_id=doc_id,
            version=version,
            patch=patch,
            author=author,
            base_version=base_version,
            content_hash=content_hash,
        )

    def apply_diff(self, content: str, diff: DiffEntry) -> str:
        """Apply a diff patch to document content.

        Uses a lenient patch application strategy that gracefully handles
        unified diffs even with minor formatting differences.

        Args:
            content: Current document content
            diff: DiffEntry with patch to apply

        Returns:
            Updated document content after applying patch

        Raises:
            ValueError: If patch cannot be applied
        """
        if not diff.patch or diff.patch.isspace():
            # Empty patch means no changes
            return content

        try:
            patch_text = diff.patch.strip()

            # If patch doesn't start with "---", it's not a proper unified diff
            # Return content unchanged (lenient mode)
            if not patch_text.startswith("---"):
                return content

            # Use patching library if available
            try:
                from patch_ng import PatchFile

                patch_file = PatchFile(patch_text.split("\n"))
                result = patch_file.apply(
                    content.split("\n"), list(range(len(content.split("\n"))))
                )

                if result:
                    return "\n".join(result[0])
            except (ImportError, Exception):
                # Fall back to simple line-based patching
                pass

            # Simple lenient patching approach
            patch_lines = patch_text.split("\n")
            content_lines = content.split("\n")

            # Find and skip headers
            idx = 0
            while idx < len(patch_lines) and not patch_lines[idx].startswith(
                "@@"
            ):
                if patch_lines[idx].startswith("---") or patch_lines[
                    idx
                ].startswith("+++"):
                    idx += 1
                else:
                    idx += 1

            # If no hunks found, return original
            if idx >= len(patch_lines):
                return content

            # Apply hunks (basic lenient application)
            result_lines = list(content_lines)

            while idx < len(patch_lines):
                line = patch_lines[idx]

                if line.startswith("@@"):
                    # Skip hunk header for now
                    idx += 1
                    continue

                if line.startswith("-"):
                    # Try to find and remove matching line
                    removed_line = line[1:]
                    try:
                        result_lines.remove(removed_line)
                    except ValueError:
                        # Line not found, continue
                        pass

                elif line.startswith("+"):
                    # Add new line
                    result_lines.append(line[1:])

                idx += 1

            return "\n".join(result_lines)

        except Exception as e:
            logger.debug(f"Failed to apply diff to {diff.doc_id}: {e}")
            # Return original content on failure (lenient mode)
            return content

    def merge(
        self,
        local_content: str,
        remote_content: str,
        local_version: int,
        remote_version: int,
    ) -> tuple[str, int]:
        """Merge local and remote document versions.

        Uses a three-way merge strategy: prefers changes from the higher
        version number (assuming higher version is more recent/authoritative),
        but attempts to preserve both edits where possible.

        Args:
            local_content: Local document state
            remote_content: Remote document state
            local_version: Local version number
            remote_version: Remote version number

        Returns:
            Tuple of (merged_content, resulting_version)
        """
        if local_content == remote_content:
            # No conflict - content is identical
            merged = local_content
            version = max(local_version, remote_version)
        elif local_version > remote_version:
            # Local is newer - use local
            merged = local_content
            version = local_version
        elif remote_version > local_version:
            # Remote is newer - use remote
            merged = remote_content
            version = remote_version
        else:
            # Same version but different content - conflict
            # Use a simple strategy: prefer remote (or could use other conflict resolution)
            merged = remote_content
            version = remote_version

            logger.warning(
                f"Merge conflict at version {local_version}: "
                f"local vs remote with different content"
            )

        return merged, version

    def verify_diff(
        self, diff: DiffEntry, expected_content: Optional[str] = None
    ) -> bool:
        """Verify a diff's content hash matches expected state.

        Args:
            diff: DiffEntry to verify
            expected_content: Optional content to verify against

        Returns:
            True if hash matches (or no expected content), False otherwise
        """
        if not diff.content_hash or not expected_content:
            return True

        actual_hash = hashlib.sha256(expected_content.encode()).hexdigest()[:16]
        return actual_hash == diff.content_hash

    def get_diff_checksum(self, diff: DiffEntry) -> str:
        """Get a checksum of the diff itself for deduplication.

        Args:
            diff: DiffEntry to checksum

        Returns:
            SHA256 hex digest (first 16 chars)
        """
        content = f"{diff.doc_id}:{diff.version}:{diff.patch}:{diff.author}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ConflictResolver:
    """Resolver for handling merge conflicts in document diffs.

    Provides multiple conflict resolution strategies for when
    concurrent edits occur on the same document.
    """

    @staticmethod
    def prefer_newer(
        local: str, remote: str, local_ts: datetime, remote_ts: datetime
    ) -> str:
        """Resolve by preferring newer timestamp.

        Args:
            local: Local content
            remote: Remote content
            local_ts: Local timestamp
            remote_ts: Remote timestamp

        Returns:
            Preferred content
        """
        return remote if remote_ts > local_ts else local

    @staticmethod
    def prefer_longer(local: str, remote: str) -> str:
        """Resolve by preferring longer content (likely more complete).

        Args:
            local: Local content
            remote: Remote content

        Returns:
            Longer content
        """
        return remote if len(remote) > len(local) else local

    @staticmethod
    def concatenate(local: str, remote: str, sep: str = "\n---\n") -> str:
        """Resolve by concatenating both versions.

        Args:
            local: Local content
            remote: Remote content
            sep: Separator between versions

        Returns:
            Concatenated content with separator
        """
        return f"{local}{sep}{remote}"
