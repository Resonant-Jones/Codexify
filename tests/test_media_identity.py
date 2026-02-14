"""Unit tests for the unified media identity and alias helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from guardian.services.media_identity import (
    compute_content_hash,
    compute_identity,
    ensure_asset_alias,
    resolve_asset,
)


def test_compute_identity_is_deterministic_for_same_bytes():
    file_data = b"same-bytes"
    first_seen = datetime(2026, 2, 13, 10, 15, tzinfo=timezone.utc)

    identity_a = compute_identity(
        file_data=file_data,
        media_kind="document",
        provenance="uploaded",
        human_label="Quarterly Strategy Doc",
        original_filename="Quarterly Strategy Doc.pdf",
        mime_type="application/pdf",
        first_seen_at=first_seen,
    )
    identity_b = compute_identity(
        file_data=file_data,
        media_kind="document",
        provenance="uploaded",
        human_label="Quarterly Strategy Doc",
        original_filename="Quarterly Strategy Doc.pdf",
        mime_type="application/pdf",
        first_seen_at=first_seen,
    )

    expected_hash = compute_content_hash(file_data)
    assert identity_a.content_hash == expected_hash
    assert identity_b.content_hash == expected_hash
    assert identity_a.deterministic_id == identity_b.deterministic_id
    assert identity_a.system_name == identity_b.system_name
    assert identity_a.deterministic_id.startswith("20260213-")


def test_compute_identity_uses_generated_image_storage_prefix():
    identity = compute_identity(
        file_data=b"fake-image-bytes",
        media_kind="image",
        provenance="generated",
        human_label="neon city skyline",
        original_filename=None,
        mime_type="image/png",
        first_seen_at=datetime(2026, 2, 13, tzinfo=timezone.utc),
    )

    assert identity.storage_prefix == "generated_images/"
    assert identity.system_name.endswith(".png")


def test_ensure_asset_alias_inserts_new_alias():
    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    ensure_asset_alias(
        session,
        asset_id="asset-1",
        alias="Original File Name.pdf",
        alias_type="original_name",
    )

    session.add.assert_called_once()
    alias = session.add.call_args[0][0]
    assert alias.asset_id == "asset-1"
    assert alias.alias == "Original File Name.pdf"
    assert alias.alias_type == "original_name"
    assert alias.alias_normalized == "original file name pdf"


def test_resolve_asset_prefers_exact_alias_first():
    exact_asset = SimpleNamespace(id="asset-exact")
    base_query = MagicMock()
    exact_join = MagicMock()
    base_query.join.return_value = exact_join
    exact_join.filter.return_value.order_by.return_value.first.return_value = (
        exact_asset
    )

    with patch(
        "guardian.services.media_identity._base_asset_query",
        return_value=base_query,
    ):
        resolved = resolve_asset(
            session=MagicMock(),
            project_id=1,
            query="Exact Name",
            media_kind="image",
            provenance=None,
            source_tag=None,
        )

    assert resolved is exact_asset
    assert base_query.join.call_count == 1


def test_resolve_asset_falls_back_to_partial_alias():
    partial_asset = SimpleNamespace(id="asset-partial")
    base_query = MagicMock()
    exact_join = MagicMock()
    partial_join = MagicMock()
    base_query.join.side_effect = [exact_join, partial_join]
    exact_join.filter.return_value.order_by.return_value.first.return_value = (
        None
    )
    partial_join.filter.return_value.order_by.return_value.first.return_value = (
        partial_asset
    )

    with patch(
        "guardian.services.media_identity._base_asset_query",
        return_value=base_query,
    ):
        resolved = resolve_asset(
            session=MagicMock(),
            project_id=1,
            query="partial fragment",
            media_kind=None,
            provenance="generated",
            source_tag="generated",
        )

    assert resolved is partial_asset
    assert base_query.join.call_count == 2
