"""Tests for media routes (image upload, document upload, image generation)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set environment variables early
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GUARDIAN_API_KEY", "test")


@pytest.fixture
def app():
    """Create test FastAPI app with media routes."""
    from fastapi import FastAPI

    app = FastAPI()

    # Import and include router
    from guardian.routes.media import router

    app.include_router(router, prefix="/api/media")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(
        app, headers={"X-API-Key": os.environ["GUARDIAN_API_KEY"]}
    )


def _mock_db_with_session() -> tuple[MagicMock, MagicMock]:
    db = MagicMock()
    session = MagicMock()
    db.get_session.return_value.__enter__ = MagicMock(return_value=session)
    db.get_session.return_value.__exit__ = MagicMock(return_value=False)
    return db, session


class TestImageGeneration:
    """Tests for image generation endpoint."""

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media._create_media_asset")
    @patch("guardian.routes.media._find_generated_image_for_asset")
    @patch("guardian.routes.media._compute_identity_with_existing_asset")
    @patch("guardian.routes.media.ensure_asset_alias")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_success(
        self,
        mock_gen,
        mock_ensure_alias,
        mock_compute_identity,
        mock_find_generated,
        mock_create_asset,
        mock_get_db,
        mock_storage,
        client,
    ):
        """Image generation uses canonical generated-image path naming."""
        fake_image_bytes = b"fake PNG data"
        mock_gen.return_value = fake_image_bytes
        mock_storage.upload_file.return_value = "/media/generated/test.png"
        mock_find_generated.return_value = None
        mock_create_asset.return_value = SimpleNamespace(id="asset-1")
        identity = SimpleNamespace(
            storage_prefix="generated_images/",
            system_name="20260213-deadbeef--a-beautiful-landscape.png",
        )
        mock_compute_identity.side_effect = [
            (identity, None),
            (identity, None),
        ]

        mock_db, mock_session = _mock_db_with_session()
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/generate/image",
            json={
                "prompt": "a beautiful landscape",
                "model": "dall-e-3",
                "user_id": "test_user",
                "project_id": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["src_url"].startswith("/media/generated/test.png")
        assert "sig=" in data["src_url"]
        assert data["prompt"] == "a beautiful landscape"
        assert data["model"] == "dall-e-3"
        assert "created_at" in data

        mock_gen.assert_called_once_with(
            prompt="a beautiful landscape",
            model="dall-e-3",
        )

        mock_storage.upload_file.assert_called_once()
        upload_args, upload_kwargs = mock_storage.upload_file.call_args
        assert upload_args[0] == fake_image_bytes
        assert upload_args[1].startswith("generated_images/")
        assert "--" in upload_args[1]
        assert upload_kwargs["content_type"] == "image/png"

        generated_image = mock_session.add.call_args[0][0]
        assert generated_image.asset_id == "asset-1"
        mock_ensure_alias.assert_called_once()

    @patch("guardian.routes.media.ImageGenRouter.generate")
    @patch("guardian.routes.media.verify_api_key")
    @patch("guardian.routes.media._is_pytest", return_value=False)
    def test_generate_image_requires_api_key(
        self, _mock_is_pytest, mock_verify_api_key, mock_generate, app
    ):
        """Image generation is fail-closed when API key headers are absent."""
        from fastapi import HTTPException

        mock_verify_api_key.side_effect = HTTPException(
            status_code=401, detail="Unauthorized"
        )
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.post(
            "/api/media/generate/image",
            json={"prompt": "no key request", "model": "dall-e-3"},
        )

        assert response.status_code == 401
        mock_generate.assert_not_called()

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_provider_not_configured(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Error is preserved when provider config is missing."""
        from fastapi import HTTPException

        mock_gen.side_effect = HTTPException(
            status_code=400,
            detail="IMAGE_GEN_PROVIDER is not configured",
        )

        response = client.post(
            "/api/media/generate/image",
            json={"prompt": "test image", "model": "dall-e-3"},
        )

        assert response.status_code == 400
        assert "IMAGE_GEN_PROVIDER" in response.json()["detail"]

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_provider_error(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Provider failures surface as 500 responses."""
        mock_gen.side_effect = RuntimeError("API connection failed")

        response = client.post(
            "/api/media/generate/image",
            json={"prompt": "test image", "model": "dall-e-3"},
        )

        assert response.status_code == 500
        assert "Image generation failed" in response.json()["detail"]

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media._create_media_asset")
    @patch("guardian.routes.media._find_generated_image_for_asset")
    @patch("guardian.routes.media._compute_identity_with_existing_asset")
    @patch("guardian.routes.media.ensure_asset_alias")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_with_optional_context(
        self,
        mock_gen,
        mock_ensure_alias,
        mock_compute_identity,
        mock_find_generated,
        mock_create_asset,
        mock_get_db,
        mock_storage,
        client,
    ):
        """Project/thread context is carried into generated image records."""
        mock_gen.return_value = b"fake PNG data"
        mock_storage.upload_file.return_value = "/media/test.png"
        mock_find_generated.return_value = None
        mock_create_asset.return_value = SimpleNamespace(id="asset-ctx")
        identity = SimpleNamespace(
            storage_prefix="generated_images/",
            system_name="20260213-1234abcd--test-image.png",
        )
        mock_compute_identity.side_effect = [
            (identity, None),
            (identity, None),
        ]

        mock_db, mock_session = _mock_db_with_session()
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/generate/image",
            json={
                "prompt": "test image",
                "model": "dall-e-3",
                "user_id": "user123",
                "project_id": 42,
                "thread_id": 99,
            },
        )

        assert response.status_code == 200
        generated_image = mock_session.add.call_args[0][0]
        assert generated_image.project_id == 42
        assert generated_image.thread_id == 99
        assert generated_image.user_id == "user123"
        assert generated_image.asset_id == "asset-ctx"
        mock_ensure_alias.assert_called_once()


class TestUploadDedupeAndResolve:
    """Tests for media dedupe and resolver routes."""

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media._find_uploaded_image_for_asset")
    @patch("guardian.routes.media._compute_identity_with_existing_asset")
    @patch("guardian.routes.media.ensure_asset_alias")
    def test_upload_image_dedupe_returns_existing_by_asset_identity(
        self,
        mock_ensure_alias,
        mock_compute_identity,
        mock_find_uploaded,
        mock_get_db,
        mock_storage,
        client,
    ):
        """Upload dedupe returns existing row via canonical asset identity."""
        existing_asset = SimpleNamespace(id="asset-1")
        identity = SimpleNamespace(
            storage_prefix="images/",
            system_name="20260213-deadbeef--existing.png",
        )
        mock_compute_identity.return_value = (identity, existing_asset)

        existing = MagicMock()
        existing.id = "img-123"
        existing.src_url = "/media/images/existing.png"
        existing.filename = "existing.png"
        existing.filesize = 8
        existing.mime_type = "image/png"
        existing.source_tag = "uploaded"
        existing.created_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
        mock_find_uploaded.return_value = existing

        mock_db, _mock_session = _mock_db_with_session()
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/upload/image",
            data={"project_id": 1, "thread_id": 1},
            files={"file": ("new-name.png", b"12345678", "image/png")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == "img-123"
        assert payload["filename"] == "existing.png"
        assert payload["source_tag"] == "uploaded"
        mock_storage.upload_file.assert_not_called()
        mock_ensure_alias.assert_called_once()

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media.enqueue_document_embed")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media._create_media_asset")
    @patch("guardian.routes.media._find_uploaded_document_for_asset")
    @patch("guardian.routes.media._compute_identity_with_existing_asset")
    @patch("guardian.routes.media.ensure_asset_alias")
    def test_upload_document_enqueues_embedding_with_asset_metadata(
        self,
        mock_ensure_alias,
        mock_compute_identity,
        mock_find_uploaded_doc,
        mock_create_asset,
        mock_get_db,
        mock_enqueue_embed,
        mock_storage,
        client,
    ):
        """Document enqueue metadata keeps old keys and adds identity keys."""
        identity = SimpleNamespace(
            storage_prefix="documents/",
            system_name="20260213-deadbeef--project-plan.txt",
        )
        mock_compute_identity.side_effect = [
            (identity, None),
            (identity, None),
        ]
        mock_find_uploaded_doc.return_value = None
        mock_create_asset.return_value = SimpleNamespace(
            id="asset-doc-1",
            deterministic_id="20260213-deadbeef",
            system_name="20260213-deadbeef--project-plan.txt",
            normalized_slug="project-plan",
            media_kind="document",
            provenance="uploaded",
            source_tag="uploaded",
            content_hash="deadbeefcafebabe",
        )
        mock_storage.upload_file.return_value = (
            "/media/documents/20260213-deadbeef--project-plan.txt"
        )

        mock_db, _mock_session = _mock_db_with_session()
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/upload/document",
            data={"project_id": 1, "thread_id": 2, "user_id": "u-1"},
            files={"file": ("project-plan.txt", b"hello world", "text/plain")},
        )

        assert response.status_code == 200
        mock_enqueue_embed.assert_called_once()
        _, enqueue_kwargs = mock_enqueue_embed.call_args
        metadata = enqueue_kwargs["metadata"]
        assert metadata["filename"] == "project-plan.txt"
        assert metadata["mime_type"] == "text/plain"
        assert metadata["user_id"] == "u-1"
        assert metadata["project_id"] == 1
        assert metadata["thread_id"] == 2
        assert metadata["asset_id"] == "asset-doc-1"
        assert metadata["deterministic_id"] == "20260213-deadbeef"
        assert metadata["system_name"] == "20260213-deadbeef--project-plan.txt"
        assert metadata["normalized_slug"] == "project-plan"
        assert metadata["media_kind"] == "document"
        assert metadata["provenance"] == "uploaded"
        assert metadata["source_tag"] == "uploaded"
        assert metadata["content_hash"] == "deadbeefcafebabe"

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media.enqueue_document_embed")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media._create_media_asset")
    @patch("guardian.routes.media._find_uploaded_document_for_asset")
    @patch("guardian.routes.media._compute_identity_with_existing_asset")
    @patch("guardian.routes.media.ensure_asset_alias")
    def test_upload_document_with_project_only_sets_nullable_thread(
        self,
        mock_ensure_alias,
        mock_compute_identity,
        mock_find_uploaded_doc,
        mock_create_asset,
        mock_get_db,
        mock_enqueue_embed,
        mock_storage,
        client,
    ):
        identity = SimpleNamespace(
            storage_prefix="documents/",
            system_name="20260213-feedbeef--notes.txt",
        )
        mock_compute_identity.side_effect = [
            (identity, None),
            (identity, None),
        ]
        mock_find_uploaded_doc.return_value = None
        mock_create_asset.return_value = SimpleNamespace(
            id="asset-doc-project-only",
            deterministic_id="20260213-feedbeef",
            system_name="20260213-feedbeef--notes.txt",
            normalized_slug="notes",
            media_kind="document",
            provenance="uploaded",
            source_tag="uploaded",
            content_hash="feedbeefcafebabe",
        )
        mock_storage.upload_file.return_value = (
            "/media/documents/20260213-feedbeef--notes.txt"
        )

        mock_db, _mock_session = _mock_db_with_session()
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/upload/document",
            data={"project_id": 7, "user_id": "u-1"},
            files={"file": ("notes.txt", b"hello world", "text/plain")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["project_id"] == 7
        assert payload["thread_id"] is None
        _, enqueue_kwargs = mock_enqueue_embed.call_args
        metadata = enqueue_kwargs["metadata"]
        assert metadata["project_id"] == 7
        assert metadata["thread_id"] is None

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media.enqueue_document_embed")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media._create_media_asset")
    @patch("guardian.routes.media._find_uploaded_document_for_asset")
    @patch("guardian.routes.media._compute_identity_with_existing_asset")
    @patch("guardian.routes.media.ensure_asset_alias")
    def test_upload_document_without_project_falls_back_to_default_project(
        self,
        mock_ensure_alias,
        mock_compute_identity,
        mock_find_uploaded_doc,
        mock_create_asset,
        mock_get_db,
        mock_enqueue_embed,
        mock_storage,
        client,
    ):
        identity = SimpleNamespace(
            storage_prefix="documents/",
            system_name="20260213-cafed00d--fallback.txt",
        )
        mock_compute_identity.side_effect = [
            (identity, None),
            (identity, None),
        ]
        mock_find_uploaded_doc.return_value = None
        mock_create_asset.return_value = SimpleNamespace(
            id="asset-doc-fallback",
            deterministic_id="20260213-cafed00d",
            system_name="20260213-cafed00d--fallback.txt",
            normalized_slug="fallback",
            media_kind="document",
            provenance="uploaded",
            source_tag="uploaded",
            content_hash="cafed00ddeadbeef",
        )
        mock_storage.upload_file.return_value = (
            "/media/documents/20260213-cafed00d--fallback.txt"
        )

        mock_db, _mock_session = _mock_db_with_session()
        mock_db.list_projects.return_value = [{"id": 42, "name": "General"}]
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/upload/document",
            data={"user_id": "u-1"},
            files={"file": ("fallback.txt", b"hello world", "text/plain")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["project_id"] == 42
        assert payload["thread_id"] is None
        _, enqueue_kwargs = mock_enqueue_embed.call_args
        metadata = enqueue_kwargs["metadata"]
        assert metadata["project_id"] == 42
        assert metadata["thread_id"] is None

    @patch("guardian.routes.media.display_title_for_asset")
    @patch("guardian.routes.media.resolve_asset_from_aliases")
    @patch("guardian.routes.media._get_db")
    def test_media_resolve_returns_canonical_asset(
        self,
        mock_get_db,
        mock_resolve_asset,
        mock_display_title,
        client,
    ):
        """Resolver endpoint returns canonical asset identity payload."""
        fake_asset = SimpleNamespace(
            id="asset-42",
            src_url="/media/generated_images/20260213-1234abcd--city.png",
            media_kind="image",
            provenance="generated",
            source_tag="generated",
            ingested_at=datetime(2026, 2, 13, tzinfo=timezone.utc),
        )
        mock_resolve_asset.return_value = fake_asset
        mock_display_title.return_value = "city skyline at sunset"

        mock_db, _mock_session = _mock_db_with_session()
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/media/resolve",
            params={"project_id": 1, "q": "city skyline", "kind": "image"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["asset_id"] == "asset-42"
        assert payload["src_url"].startswith(fake_asset.src_url)
        assert "sig=" in payload["src_url"]
        assert payload["display_title"] == "city skyline at sunset"
        assert payload["media_kind"] == "image"
        assert payload["provenance"] == "generated"
        assert payload["source_tag"] == "generated"
        assert payload["created_at"] == payload["ingested_at"]

    @patch("guardian.routes.media._get_db")
    def test_list_images_generated_tag_returns_generated(
        self, mock_get_db, client
    ):
        """List generated images when tag=generated is provided."""
        generated = MagicMock()
        generated.id = "gen-1"
        generated.src_url = "/media/generated/gen-1.png"
        generated.prompt = "A test prompt"
        generated.created_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

        mock_session = MagicMock()
        query = mock_session.query.return_value
        query.filter.return_value = query
        query.filter_by.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = [generated]

        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_get_db.return_value = mock_db

        response = client.get("/api/media/images?tag=generated")
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["images"][0]["source_tag"] == "generated"
