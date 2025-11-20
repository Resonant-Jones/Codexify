"""
File storage abstraction for Codexify media files.

Supports multiple backends (local filesystem, S3, GCS) with a unified API.
Follows the same provider pattern as TTS services.
"""

import os
import logging
import tempfile
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


# =========================
# Exceptions
# =========================

class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class FileNotFoundError(StorageError):
    """File not found in storage."""
    pass


class UploadError(StorageError):
    """Failed to upload file."""
    pass


class DeleteError(StorageError):
    """Failed to delete file."""
    pass


class StorageConfigError(StorageError):
    """Storage configuration error."""
    pass


# =========================
# Storage Provider Interface
# =========================

class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    def upload(self, file_data: bytes, filename: str, content_type: Optional[str] = None,
               metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Upload a file to storage.

        Args:
            file_data: Raw file bytes
            filename: Name to save file as (may include path like 'images/photo.jpg')
            content_type: MIME type (auto-detected if None)
            metadata: Optional metadata dict

        Returns:
            URL or path to the uploaded file

        Raises:
            UploadError: If upload fails
        """
        pass

    @abstractmethod
    def download(self, file_path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            file_path: Path or URL to the file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path or URL to the file

        Returns:
            True if deleted, False if file didn't exist

        Raises:
            DeleteError: If deletion fails
        """
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            file_path: Path or URL to the file

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files in storage.

        Args:
            prefix: Optional prefix to filter files (e.g., 'images/')

        Returns:
            List of file paths/URLs
        """
        pass

    @abstractmethod
    def get_url(self, file_path: str, expires_in: Optional[int] = None) -> str:
        """
        Get a public or signed URL for a file.

        Args:
            file_path: Path to the file
            expires_in: Expiration time in seconds (for signed URLs)

        Returns:
            Accessible URL for the file
        """
        pass


# =========================
# Local Filesystem Provider
# =========================

class LocalStorageProvider(StorageProvider):
    """
    Store files on local filesystem.

    Good for:
    - Local development
    - Single-server deployments
    - Docker volume-backed storage
    """

    def __init__(self, base_path: str = "/app/media", url_prefix: str = "/media"):
        """
        Initialize local storage.

        Args:
            base_path: Root directory for file storage
            url_prefix: URL prefix for accessing files (e.g., '/media' → http://host/media/file.jpg)
        """
        self.base_path = Path(base_path)
        self.url_prefix = url_prefix.rstrip('/')

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at {self.base_path}")

    def upload(self, file_data: bytes, filename: str, content_type: Optional[str] = None,
               metadata: Optional[Dict[str, str]] = None) -> str:
        """Upload file to local filesystem."""
        try:
            # Sanitize filename and create subdirectories if needed
            file_path = self.base_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_data)

            logger.info(f"Uploaded {filename} ({len(file_data)} bytes) to local storage")
            return f"{self.url_prefix}/{filename}"

        except Exception as e:
            raise UploadError(f"Failed to upload {filename}: {e}")

    def download(self, file_path: str) -> bytes:
        """Download file from local filesystem."""
        # Strip URL prefix if present
        if file_path.startswith(self.url_prefix):
            file_path = file_path[len(self.url_prefix):].lstrip('/')

        full_path = self.base_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to read {file_path}: {e}")

    def delete(self, file_path: str) -> bool:
        """Delete file from local filesystem."""
        # Strip URL prefix if present
        if file_path.startswith(self.url_prefix):
            file_path = file_path[len(self.url_prefix):].lstrip('/')

        full_path = self.base_path / file_path

        if not full_path.exists():
            return False

        try:
            full_path.unlink()
            logger.info(f"Deleted {file_path} from local storage")
            return True
        except Exception as e:
            raise DeleteError(f"Failed to delete {file_path}: {e}")

    def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        if file_path.startswith(self.url_prefix):
            file_path = file_path[len(self.url_prefix):].lstrip('/')

        return (self.base_path / file_path).exists()

    def list_files(self, prefix: str = "") -> List[str]:
        """List files in storage."""
        search_path = self.base_path / prefix if prefix else self.base_path

        if not search_path.exists():
            return []

        files = []
        for file_path in search_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.base_path)
                files.append(f"{self.url_prefix}/{relative_path}")

        return files

    def get_url(self, file_path: str, expires_in: Optional[int] = None) -> str:
        """Get URL for file (always public for local storage)."""
        if file_path.startswith(self.url_prefix):
            return file_path

        return f"{self.url_prefix}/{file_path}"


# =========================
# S3 Provider (Stub for Future)
# =========================

class S3StorageProvider(StorageProvider):
    """
    Store files in AWS S3 or compatible object storage.

    TODO: Implement when needed.
    Requires: boto3
    """

    def __init__(self, bucket: str, region: str = "us-east-1",
                 access_key: Optional[str] = None, secret_key: Optional[str] = None):
        raise NotImplementedError("S3 storage not yet implemented")

    def upload(self, file_data: bytes, filename: str, content_type: Optional[str] = None,
               metadata: Optional[Dict[str, str]] = None) -> str:
        raise NotImplementedError()

    def download(self, file_path: str) -> bytes:
        raise NotImplementedError()

    def delete(self, file_path: str) -> bool:
        raise NotImplementedError()

    def exists(self, file_path: str) -> bool:
        raise NotImplementedError()

    def list_files(self, prefix: str = "") -> List[str]:
        raise NotImplementedError()

    def get_url(self, file_path: str, expires_in: Optional[int] = None) -> str:
        raise NotImplementedError()


# =========================
# Storage Manager
# =========================

class StorageManager:
    """
    Manage storage providers and route operations.

    Follows the same pattern as TTSManager.
    """

    def __init__(self, provider_type: str = "local", **provider_config):
        """
        Initialize storage manager.

        Args:
            provider_type: 'local', 's3', or 'gcs'
            **provider_config: Configuration for the provider

        Example:
            manager = StorageManager('local', base_path='/app/media', url_prefix='/media')
            manager = StorageManager('s3', bucket='my-bucket', region='us-west-2')
        """
        self.provider_type = provider_type
        self.provider = self._create_provider(provider_type, provider_config)

    def _create_provider(self, provider_type: str, config: Dict) -> StorageProvider:
        """Create storage provider instance."""
        if provider_type == "local":
            base_path = config.get('base_path', '/app/media')
            url_prefix = config.get('url_prefix', '/media')
            return LocalStorageProvider(base_path=base_path, url_prefix=url_prefix)

        elif provider_type == "s3":
            # TODO: Implement S3
            raise NotImplementedError("S3 storage not yet implemented")

        elif provider_type == "gcs":
            # TODO: Implement GCS
            raise NotImplementedError("GCS storage not yet implemented")

        else:
            raise StorageConfigError(f"Unknown storage provider: {provider_type}")

    def upload_file(self, file_data: bytes, filename: str,
                    content_type: Optional[str] = None,
                    metadata: Optional[Dict[str, str]] = None) -> str:
        """Upload a file."""
        # Auto-detect content type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(filename)

        return self.provider.upload(file_data, filename, content_type, metadata)

    def download_file(self, file_path: str) -> bytes:
        """Download a file."""
        return self.provider.download(file_path)

    def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        return self.provider.delete(file_path)

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        return self.provider.exists(file_path)

    def list_files(self, prefix: str = "") -> List[str]:
        """List files."""
        return self.provider.list_files(prefix)

    def get_file_url(self, file_path: str, expires_in: Optional[int] = None) -> str:
        """Get URL for file."""
        return self.provider.get_url(file_path, expires_in)


# =========================
# Utility Functions
# =========================

def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a unique filename with timestamp.

    Args:
        original_filename: Original file name
        prefix: Optional prefix (e.g., 'images/', 'audio/')

    Returns:
        Unique filename with timestamp

    Example:
        generate_unique_filename('photo.jpg', 'images/')
        → 'images/2025-10-26_142530_photo.jpg'
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    name, ext = os.path.splitext(original_filename)

    # Sanitize name
    safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-'))

    filename = f"{timestamp}_{safe_name}{ext}"

    if prefix:
        prefix = prefix.rstrip('/') + '/'
        filename = f"{prefix}{filename}"

    return filename


def detect_media_type(filename: str) -> str:
    """
    Detect media type from filename.

    Returns:
        'image', 'audio', 'video', 'document', or 'unknown'
    """
    mime_type, _ = mimetypes.guess_type(filename)

    if mime_type:
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type in ('application/pdf', 'text/plain', 'text/markdown',
                           'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
            return 'document'

    return 'unknown'


# =========================
# Configuration Loading
# =========================
def create_storage_from_env() -> "StorageManager":
    """
    Create a StorageManager based on environment configuration.

    Behavior:
    - If STORAGE_BASE_PATH is set, always use that as the base path.
    - Otherwise, when running under pytest (detected via PYTEST_CURRENT_TEST or presence of pytest in sys.modules),
      use a writable temporary directory under the system temp dir.
    - For normal runtime, default to /app/media (container default).
    """
    url_prefix = os.getenv("STORAGE_URL_PREFIX", "/media")

    base_path_env = os.getenv("STORAGE_BASE_PATH")
    is_pytest = "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST")

    if base_path_env:
        base_path = Path(base_path_env)
    elif is_pytest:
        # Test environment: avoid writing to read-only /app
        base_path = Path(tempfile.gettempdir()) / "codexify_media"
    else:
        # Default container path (Docker runtime)
        base_path = Path("/app/media")

    return StorageManager("local", base_path=base_path, url_prefix=url_prefix)