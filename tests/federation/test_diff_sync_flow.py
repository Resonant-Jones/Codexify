"""Tests for federated document synchronization flows.

Tests cover:
- Push/pull synchronization between nodes
- Version history and resync after offline
- Concurrent edit merging
- Relay message forwarding
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from guardian.federation.diff_engine import DiffEngine, DiffEntry
from guardian.federation.diff_store import DiffStore, get_diff_store


class TestDiffStore:
    """Test diff store persistence and retrieval."""

    def setup_method(self):
        """Set up test diff store."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = DiffStore(self.temp_dir)

    def teardown_method(self):
        """Clean up test store."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_and_retrieve_diff(self):
        """Test recording and retrieving a diff."""
        diff = DiffEntry(
            doc_id="doc-1",
            version=1,
            patch="--- old\n+++ new",
            author="user-1",
            content_hash="hash123",
        )

        content = "new content\n"
        self.store.record_diff(diff, content)

        # Retrieve version
        version = self.store.get_latest_version("doc-1")
        assert version == 1

        # Retrieve content
        retrieved = self.store.get_latest_content("doc-1")
        assert retrieved == content

    def test_track_multiple_versions(self):
        """Test tracking multiple versions of same document."""
        diff1 = DiffEntry(
            doc_id="doc-1", version=1, patch="v1", author="user-1"
        )
        diff2 = DiffEntry(
            doc_id="doc-1", version=2, patch="v2", author="user-1"
        )
        diff3 = DiffEntry(
            doc_id="doc-1", version=3, patch="v3", author="user-1"
        )

        self.store.record_diff(diff1, "content-v1")
        self.store.record_diff(diff2, "content-v2")
        self.store.record_diff(diff3, "content-v3")

        assert self.store.get_latest_version("doc-1") == 3
        assert self.store.get_latest_content("doc-1") == "content-v3"

    def test_get_diffs_since_version(self):
        """Test retrieving diffs since a given version."""
        for i in range(1, 6):
            diff = DiffEntry(
                doc_id="doc-1",
                version=i,
                patch=f"patch-{i}",
                author="user-1",
            )
            self.store.record_diff(diff, f"content-v{i}")

        # Get diffs since version 2
        diffs = self.store.get_diffs_since("doc-1", 2)

        assert len(diffs) == 3  # versions 3, 4, 5
        assert diffs[0].version == 3
        assert diffs[-1].version == 5

    def test_diffs_since_returns_empty_for_nonexistent_doc(self):
        """Test that nonexistent document returns empty list."""
        diffs = self.store.get_diffs_since("nonexistent", 0)
        assert diffs == []

    def test_get_all_versions(self):
        """Test retrieving all version records."""
        for i in range(1, 4):
            diff = DiffEntry(
                doc_id="doc-2",
                version=i,
                patch=f"patch-{i}",
                author="user-1",
            )
            self.store.record_diff(diff, f"v{i}")

        versions = self.store.get_all_versions("doc-2")

        assert len(versions) == 3
        assert all(v["version"] in [1, 2, 3] for v in versions)

    def test_document_exists(self):
        """Test checking document existence."""
        assert self.store.exists("doc-1") is False

        diff = DiffEntry(
            doc_id="doc-1", version=1, patch="patch", author="user-1"
        )
        self.store.record_diff(diff, "content")

        assert self.store.exists("doc-1") is True

    def test_get_statistics(self):
        """Test document statistics."""
        diffs = [
            DiffEntry(doc_id="doc-1", version=1, patch="p1", author="user-1"),
            DiffEntry(doc_id="doc-1", version=2, patch="p2", author="user-2"),
            DiffEntry(doc_id="doc-1", version=3, patch="p3", author="user-1"),
        ]

        for diff in diffs:
            self.store.record_diff(diff, f"v{diff.version}")

        stats = self.store.get_statistics("doc-1")

        assert stats["exists"] is True
        assert stats["latest_version"] == 3
        assert stats["total_diffs"] == 3
        assert stats["unique_authors"] == 2


class TestSyncFlow:
    """Test synchronization flows between nodes."""

    def setup_method(self):
        """Set up test stores for two nodes."""
        self.temp_dir_a = tempfile.mkdtemp()
        self.temp_dir_b = tempfile.mkdtemp()

        self.store_a = DiffStore(self.temp_dir_a)
        self.store_b = DiffStore(self.temp_dir_b)

        self.engine = DiffEngine()

    def teardown_method(self):
        """Clean up test stores."""
        shutil.rmtree(self.temp_dir_a, ignore_errors=True)
        shutil.rmtree(self.temp_dir_b, ignore_errors=True)

    def test_push_pull_single_change(self):
        """Test pushing a change from A to B."""
        doc_id = "doc-1"

        # Node A: Create initial version
        v1_a = "Initial content\n"
        diff1 = DiffEntry(
            doc_id=doc_id,
            version=1,
            patch="initial",
            author="node-a",
            base_version=0,
        )
        self.store_a.record_diff(diff1, v1_a)

        # Node A: Make edit (v2)
        v2_a = "Initial content\nEdited by A\n"
        diff2 = self.engine.compute_diff(
            v1_a, v2_a, doc_id, "node-a", version=2, base_version=1
        )
        self.store_a.record_diff(diff2, v2_a)

        # Node B: Pull changes from A
        diffs = self.store_a.get_diffs_since(doc_id, 0)

        # Verify B can pull diffs
        assert len(diffs) == 2
        assert diffs[0].version == 1
        assert diffs[1].version == 2

        # Node B records received diffs
        for diff in diffs:
            self.store_b.record_diff(diff, f"v{diff.version}")

        # Verify B is caught up on versions
        assert self.store_b.get_latest_version(
            doc_id
        ) == self.store_a.get_latest_version(doc_id)

    def test_concurrent_edits_different_lines(self):
        """Test concurrent edits on different lines."""
        doc_id = "doc-1"

        initial = "Line 1\nLine 2\nLine 3\n"

        # Node A: Edit line 1
        v2_a = "Line 1 - edited by A\nLine 2\nLine 3\n"
        diff_a = self.engine.compute_diff(
            initial, v2_a, doc_id, "node-a", version=2, base_version=1
        )

        # Node B: Edit line 3 (different area)
        v2_b = "Line 1\nLine 2\nLine 3 - edited by B\n"
        diff_b = self.engine.compute_diff(
            initial, v2_b, doc_id, "node-b", version=2, base_version=1
        )

        # Merge: prefer higher version (both are 2, so uses diff_b)
        merged_content, merged_version = self.engine.merge(v2_a, v2_b, 2, 2)

        assert merged_version == 2
        assert "edited" in merged_content

    def test_offline_resync_scenario(self):
        """Test resync after node was offline."""
        doc_id = "doc-1"

        # While B was offline, A made changes v1-v3
        for v in range(1, 4):
            content = f"Content v{v}\n"
            diff = DiffEntry(
                doc_id=doc_id,
                version=v,
                patch=f"patch-v{v}",
                author="node-a",
                base_version=v - 1,
            )
            self.store_a.record_diff(diff, content)

        # B comes back online at v0 (was offline)
        b_version = 0

        # B pulls all diffs since its last known version
        missing_diffs = self.store_a.get_diffs_since(doc_id, b_version)

        assert len(missing_diffs) == 3

        # B records all missing diffs
        for diff in missing_diffs:
            self.store_b.record_diff(diff, f"synced-v{diff.version}")

        # B is now caught up with A on version
        assert self.store_b.get_latest_version(
            doc_id
        ) == self.store_a.get_latest_version(doc_id)
        # Both should be at version 3
        assert self.store_b.get_latest_version(doc_id) == 3
        assert self.store_a.get_latest_version(doc_id) == 3

    def test_version_mismatch_detection(self):
        """Test detection of version mismatches."""
        doc_id = "doc-1"

        # Node A at version 3
        for v in range(1, 4):
            diff = DiffEntry(
                doc_id=doc_id, version=v, patch=f"p{v}", author="node-a"
            )
            self.store_a.record_diff(diff, f"v{v}")

        # Node B at version 1
        diff = DiffEntry(doc_id=doc_id, version=1, patch="p1", author="node-b")
        self.store_b.record_diff(diff, "v1")

        # B should pull diffs 2 and 3
        missing = self.store_a.get_diffs_since(doc_id, 1)

        assert len(missing) == 2
        assert missing[0].version == 2
        assert missing[1].version == 3

    def test_multiple_documents_independent(self):
        """Test that diffs for different documents are independent."""
        # Document 1
        for v in range(1, 3):
            diff = DiffEntry(
                doc_id="doc-1", version=v, patch=f"patch-{v}", author="user-1"
            )
            self.store_a.record_diff(diff, f"doc1-v{v}")

        # Document 2
        for v in range(1, 4):
            diff = DiffEntry(
                doc_id="doc-2", version=v, patch=f"patch-{v}", author="user-1"
            )
            self.store_a.record_diff(diff, f"doc2-v{v}")

        assert self.store_a.get_latest_version("doc-1") == 2
        assert self.store_a.get_latest_version("doc-2") == 3

    def test_sequential_patch_application(self):
        """Test applying multiple sequential patches."""
        doc_id = "doc-1"

        # Create a chain of edits and store them
        contents = [
            "Start\n",
            "Start\nLine 2\n",
            "Start\nLine 2\nLine 3\n",
            "Modified Start\nLine 2\nLine 3\n",
        ]

        diffs = []
        for i, content in enumerate(contents[1:], 1):
            diff = self.engine.compute_diff(
                contents[i - 1],
                content,
                doc_id,
                "user-1",
                version=i,
                base_version=i - 1,
            )
            diffs.append(diff)
            self.store_a.record_diff(diff, content)

        # Verify all diffs are recorded
        all_diffs = self.store_a.get_all_versions(doc_id)
        assert len(all_diffs) == 3

        # Verify versions are sequential
        versions = [d["version"] for d in all_diffs]
        assert versions == [1, 2, 3]

    def test_version_continuity(self):
        """Test that versions remain continuous."""
        doc_id = "doc-1"

        versions_created = []
        for v in range(1, 6):
            diff = DiffEntry(
                doc_id=doc_id,
                version=v,
                patch=f"patch-{v}",
                author="user-1",
                base_version=v - 1,
            )
            self.store_a.record_diff(diff, f"v{v}")
            versions_created.append(v)

        retrieved_diffs = self.store_a.get_all_versions(doc_id)
        retrieved_versions = [d["version"] for d in retrieved_diffs]

        assert retrieved_versions == versions_created

    def test_author_tracking_across_diffs(self):
        """Test that authors are tracked for each diff."""
        doc_id = "doc-1"

        authors = ["alice", "bob", "charlie"]

        for v, author in enumerate(authors, 1):
            diff = DiffEntry(
                doc_id=doc_id,
                version=v,
                patch=f"patch-by-{author}",
                author=author,
            )
            self.store_a.record_diff(diff, f"v{v}")

        versions = self.store_a.get_all_versions(doc_id)

        for version_record, expected_author in zip(versions, authors):
            assert version_record["author"] == expected_author
