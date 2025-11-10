"""Tests for CRDT-style diff engine and patch operations.

Tests cover:
- Diff computation between document versions
- Patch application and conflict handling
- Version tracking and deterministic merging
- Content verification via hashing
"""

import pytest
from datetime import datetime, timezone

from guardian.federation.diff_engine import (
    DiffEntry,
    DiffEngine,
    ConflictResolver,
)


class TestDiffEntryModel:
    """Test DiffEntry Pydantic model."""

    def test_create_diff_entry(self):
        """Test creating a DiffEntry."""
        diff = DiffEntry(
            doc_id="doc-123",
            version=2,
            patch="--- file\n+++ file\n@@ -1 +1 @@\n- old\n+ new",
            author="user-001",
            base_version=1,
        )

        assert diff.doc_id == "doc-123"
        assert diff.version == 2
        assert diff.base_version == 1
        assert diff.author == "user-001"
        assert diff.timestamp is not None

    def test_diff_entry_with_content_hash(self):
        """Test DiffEntry with content hash."""
        diff = DiffEntry(
            doc_id="doc-123",
            version=1,
            patch="",
            author="user-001",
            content_hash="abc123def456",
        )

        assert diff.content_hash == "abc123def456"

    def test_diff_entry_json_serialization(self):
        """Test DiffEntry JSON serialization."""
        diff = DiffEntry(
            doc_id="doc-123",
            version=1,
            patch="patch",
            author="user-001",
        )

        json_str = diff.model_dump_json()
        assert "doc-123" in json_str
        assert "patch" in json_str


class TestDiffComputation:
    """Test diff computation between versions."""

    def test_compute_simple_diff(self):
        """Test computing diff for simple text changes."""
        engine = DiffEngine()

        old = "Hello World\n"
        new = "Hello Universe\n"

        diff = engine.compute_diff(
            old, new, "doc-1", "user-1", version=1, base_version=0
        )

        assert diff.doc_id == "doc-1"
        assert diff.version == 1
        assert diff.base_version == 0
        assert diff.author == "user-1"
        assert "-" in diff.patch or "World" in diff.patch
        assert "+" in diff.patch or "Universe" in diff.patch

    def test_compute_multi_line_diff(self):
        """Test diff computation for multi-line changes."""
        engine = DiffEngine()

        old = "Line 1\nLine 2\nLine 3\n"
        new = "Line 1\nModified 2\nLine 3\n"

        diff = engine.compute_diff(
            old, new, "doc-2", "user-1", version=1
        )

        assert "Modified" in diff.patch or "Line 2" in diff.patch

    def test_compute_empty_diff(self):
        """Test diff computation when content is identical."""
        engine = DiffEngine()

        content = "Same content\n"

        diff = engine.compute_diff(
            content, content, "doc-3", "user-1", version=1
        )

        # Empty patch for identical content
        assert diff.patch == "" or "@@" not in diff.patch

    def test_compute_diff_sets_content_hash(self):
        """Test that content hash is computed."""
        engine = DiffEngine()

        old = "old"
        new = "new"

        diff = engine.compute_diff(old, new, "doc-4", "user-1", version=1)

        assert diff.content_hash is not None
        assert len(diff.content_hash) == 16  # SHA256 first 16 chars


class TestDiffApplication:
    """Test applying diffs to document content."""

    def test_apply_simple_diff(self):
        """Test applying a simple unified diff."""
        engine = DiffEngine()

        old_content = "Hello World\n"
        new_content = "Hello Universe\n"

        # Create diff
        diff = engine.compute_diff(
            old_content, new_content, "doc-1", "user-1", version=1
        )

        # Apply diff
        result = engine.apply_diff(old_content, diff)

        # Should be similar to new_content (whitespace may vary)
        assert "Universe" in result or result == new_content

    def test_apply_empty_diff(self):
        """Test applying empty diff (no changes)."""
        engine = DiffEngine()

        content = "Content\n"
        diff = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="",
            author="user-1",
        )

        result = engine.apply_diff(content, diff)

        assert result == content

    def test_apply_diff_with_additions(self):
        """Test applying diff with line additions."""
        engine = DiffEngine()

        old = "Line 1\nLine 3\n"
        new = "Line 1\nLine 2\nLine 3\n"

        diff = engine.compute_diff(old, new, "doc-2", "user-1", version=2)
        result = engine.apply_diff(old, diff)

        assert "Line 2" in result

    def test_apply_diff_with_deletions(self):
        """Test applying diff with line deletions."""
        engine = DiffEngine()

        old = "Line 1\nLine 2\nLine 3\n"
        new = "Line 1\nLine 3\n"

        diff = engine.compute_diff(old, new, "doc-3", "user-1", version=2)
        result = engine.apply_diff(old, diff)

        assert "Line 2" not in result
        assert "Line 1" in result
        assert "Line 3" in result

    def test_apply_invalid_diff_returns_original(self):
        """Test that applying invalid diff returns original content."""
        engine = DiffEngine()

        content = "Original\n"
        invalid_diff = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="invalid patch content not a unified diff",
            author="user-1",
        )

        # Lenient mode: returns original on invalid patch
        result = engine.apply_diff(content, invalid_diff)
        assert result == content


class TestDiffMerging:
    """Test conflict-free merging of concurrent changes."""

    def test_merge_identical_content(self):
        """Test merging when content is identical."""
        engine = DiffEngine()

        local = "Same\n"
        remote = "Same\n"

        merged, version = engine.merge(local, remote, 1, 1)

        assert merged == "Same\n"
        assert version == 1

    def test_merge_prefers_newer_version(self):
        """Test merge prefers higher version number."""
        engine = DiffEngine()

        local = "Local version\n"
        remote = "Remote version\n"

        # Remote is version 3, local is version 2
        merged, version = engine.merge(local, remote, 2, 3)

        assert merged == "Remote version\n"
        assert version == 3

    def test_merge_local_newer(self):
        """Test merge when local is newer."""
        engine = DiffEngine()

        local = "Local v3\n"
        remote = "Remote v2\n"

        merged, version = engine.merge(local, remote, 3, 2)

        assert merged == "Local v3\n"
        assert version == 3

    def test_merge_same_version_different_content(self):
        """Test merge with same version but different content."""
        engine = DiffEngine()

        local = "Local\n"
        remote = "Remote\n"

        # Same version = conflict, uses remote as default
        merged, version = engine.merge(local, remote, 2, 2)

        assert merged == "Remote\n"
        assert version == 2

    def test_merge_preserves_version_order(self):
        """Test that merge returns max version."""
        engine = DiffEngine()

        merged1, v1 = engine.merge("a", "b", 5, 10)
        assert v1 == 10

        merged2, v2 = engine.merge("a", "b", 10, 5)
        assert v2 == 10


class TestDiffVerification:
    """Test diff verification and checksums."""

    def test_verify_diff_with_matching_hash(self):
        """Test verification with correct content hash."""
        engine = DiffEngine()

        content = "Test content\n"
        diff = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="",
            author="user-1",
            content_hash="a1b2c3d4e5f6g7h8",  # Placeholder
        )

        # Compute actual hash
        import hashlib
        actual_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        diff.content_hash = actual_hash

        assert engine.verify_diff(diff, content) is True

    def test_verify_diff_with_mismatched_hash(self):
        """Test verification fails with wrong hash."""
        engine = DiffEngine()

        content = "Test content\n"
        diff = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="",
            author="user-1",
            content_hash="wronghash123456",
        )

        assert engine.verify_diff(diff, content) is False

    def test_get_diff_checksum(self):
        """Test computing diff checksum."""
        engine = DiffEngine()

        diff = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="test patch",
            author="user-1",
        )

        checksum = engine.get_diff_checksum(diff)

        assert checksum is not None
        assert len(checksum) == 16
        assert isinstance(checksum, str)

    def test_diff_checksum_deterministic(self):
        """Test that same diff produces same checksum."""
        engine = DiffEngine()

        diff1 = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="content",
            author="user-1",
        )

        diff2 = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="content",
            author="user-1",
        )

        checksum1 = engine.get_diff_checksum(diff1)
        checksum2 = engine.get_diff_checksum(diff2)

        assert checksum1 == checksum2


class TestConflictResolver:
    """Test conflict resolution strategies."""

    def test_prefer_newer_strategy(self):
        """Test resolver that prefers newer timestamp."""
        local = "old version\n"
        remote = "new version\n"

        ts_old = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        ts_new = datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        result = ConflictResolver.prefer_newer(local, remote, ts_old, ts_new)

        assert result == "new version\n"

    def test_prefer_longer_strategy(self):
        """Test resolver that prefers longer content."""
        local = "short\n"
        remote = "much longer content\n"

        result = ConflictResolver.prefer_longer(local, remote)

        assert result == "much longer content\n"

    def test_concatenate_strategy(self):
        """Test resolver that concatenates versions."""
        local = "Local content\n"
        remote = "Remote content\n"

        result = ConflictResolver.concatenate(local, remote)

        assert "Local content" in result
        assert "Remote content" in result
        assert "---" in result  # Default separator


class TestDiffVersionTracking:
    """Test version tracking through diffs."""

    def test_sequential_diffs_increment_version(self):
        """Test that sequential diffs increment version."""
        engine = DiffEngine()

        v1 = "Version 1\n"
        v2 = "Version 2\n"
        v3 = "Version 3\n"

        diff1 = engine.compute_diff(
            "", v1, "doc-1", "user-1", version=1, base_version=0
        )
        diff2 = engine.compute_diff(
            v1, v2, "doc-1", "user-1", version=2, base_version=1
        )
        diff3 = engine.compute_diff(
            v2, v3, "doc-1", "user-1", version=3, base_version=2
        )

        assert diff1.version == 1
        assert diff2.version == 2
        assert diff3.version == 3

    def test_base_version_tracking(self):
        """Test that base_version is tracked correctly."""
        engine = DiffEngine()

        diff = DiffEntry(
            doc_id="doc-1",
            version=5,
            patch="some patch",
            author="user-1",
            base_version=4,
        )

        assert diff.base_version == 4
        assert diff.version == 5
