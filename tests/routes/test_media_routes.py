"""Tests for media routes (image upload, document upload, image generation)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set environment variables early
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


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
    return TestClient(app)


@pytest.fixture
def mock_storage():
    """Mock storage manager."""
    mock = MagicMock()
    mock.upload_file.return_value = "/media/generated_images/test_image.png"
    return mock


@pytest.fixture
def mock_db():
    """Mock database."""
    mock = MagicMock()
    mock.get_session = MagicMock()
    mock.get_session.return_value.__enter__ = MagicMock()
    mock.get_session.return_value.__exit__ = MagicMock()
    return mock


@pytest.fixture
def mock_image_gen_router():
    """Mock image generation router."""
    mock = MagicMock()
    # Return mock image bytes
    mock.return_value = b"PNG fake image data"
    return mock


class TestImageGeneration:
    """Tests for image generation endpoint."""

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_success(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Test successful image generation."""
        # Setup mocks
        fake_image_bytes = b"fake PNG data"
        mock_gen.return_value = fake_image_bytes

        mock_storage.upload_file.return_value = "/media/generated/test.png"

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_get_db.return_value = mock_db

        # Make request
        response = client.post(
            "/api/media/generate/image",
            json={
                "prompt": "a beautiful landscape",
                "model": "dall-e-3",
                "user_id": "test_user",
                "project_id": 1,
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["src_url"] == "/media/generated/test.png"
        assert data["prompt"] == "a beautiful landscape"
        assert data["model"] == "dall-e-3"
        assert "created_at" in data

        # Verify provider was called
        mock_gen.assert_called_once_with(
            prompt="a beautiful landscape",
            model="dall-e-3",
        )

        # Verify storage save was called
        mock_storage.upload_file.assert_called_once()
        call_args = mock_storage.upload_file.call_args
        assert call_args[0][0] == fake_image_bytes  # image bytes
        assert "generated_images/gen_" in call_args[0][1]  # filename pattern
        assert call_args[1]["content_type"] == "image/png"

        # Verify database save was called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_provider_not_configured(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Test error when IMAGE_GEN_PROVIDER not configured."""
        from fastapi import HTTPException

        # Provider raises error for missing config
        mock_gen.side_effect = HTTPException(
            status_code=400,
            detail="IMAGE_GEN_PROVIDER is not configured",
        )

        # Make request
        response = client.post(
            "/api/media/generate/image",
            json={
                "prompt": "test image",
                "model": "dall-e-3",
            },
        )

        # Verify error response
        assert response.status_code == 400
        assert "IMAGE_GEN_PROVIDER" in response.json()["detail"]

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_provider_error(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Test error handling when provider fails."""
        # Provider raises error
        mock_gen.side_effect = RuntimeError("API connection failed")

        # Make request
        response = client.post(
            "/api/media/generate/image",
            json={
                "prompt": "test image",
                "model": "dall-e-3",
            },
        )

        # Verify error response
        assert response.status_code == 500
        assert "Image generation failed" in response.json()["detail"]

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_saves_to_storage_with_real_url(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Test that generated image is saved to storage with real URL."""
        # Setup mocks
        fake_image_bytes = b"fake PNG data"
        mock_gen.return_value = fake_image_bytes

        # Simulate real storage URL (not /media/generated/{id}.png)
        real_url = (
            "https://cdn.example.com/images/gen_abc123_2025-01-13_123456.png"
        )
        mock_storage.upload_file.return_value = real_url

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_get_db.return_value = mock_db

        # Make request
        response = client.post(
            "/api/media/generate/image",
            json={
                "prompt": "test image",
                "model": "dall-e-3",
            },
        )

        # Verify response has real URL
        assert response.status_code == 200
        data = response.json()
        assert data["src_url"] == real_url
        assert not data["src_url"].startswith("/media/generated/")

        # Verify storage was called and URL comes from storage
        generated_image = mock_session.add.call_args[0][0]
        assert generated_image.src_url == real_url

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    @patch("guardian.routes.media.ImageGenRouter.generate")
    def test_generate_image_with_optional_context(
        self, mock_gen, mock_get_db, mock_storage, client
    ):
        """Test image generation with project_id and thread_id."""
        # Setup mocks
        mock_gen.return_value = b"fake PNG data"
        mock_storage.upload_file.return_value = "/media/test.png"

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_get_db.return_value = mock_db

        # Make request with context
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

        # Verify context was saved to database
        assert response.status_code == 200
        generated_image = mock_session.add.call_args[0][0]
        assert generated_image.project_id == 42
        assert generated_image.thread_id == 99
        assert generated_image.user_id == "user123"


class TestUploadDedupeAndTagging:
    """Tests for media upload dedupe and tag filtering."""

    @patch("guardian.routes.media.storage")
    @patch("guardian.routes.media._get_db")
    def test_upload_image_dedupe_returns_existing(
        self, mock_get_db, mock_storage, client
    ):
        """Return existing DB row when filename + filesize match."""
        existing = MagicMock()
        existing.id = "img-123"
        existing.src_url = "/media/images/existing.png"
        existing.filename = "existing.png"
        existing.filesize = 8
        existing.mime_type = "image/png"
        existing.source_tag = "uploaded"
        existing.created_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

        mock_session = MagicMock()
        query = mock_session.query.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.first.return_value = existing

        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/media/upload/image",
            data={"project_id": 1, "thread_id": 1},
            files={"file": ("existing.png", b"12345678", "image/png")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == "img-123"
        assert payload["source_tag"] == "uploaded"
        mock_storage.upload_file.assert_not_called()

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
