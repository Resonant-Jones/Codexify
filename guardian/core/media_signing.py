"""Media URL signing helpers for non-public asset delivery."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MEDIA_SIG_QUERY_KEY = "sig"


def _media_signing_secret() -> bytes | None:
    raw = (
        (os.getenv("GUARDIAN_MEDIA_URL_SECRET") or "").strip()
        or (os.getenv("GUARDIAN_SESSION_SECRET") or "").strip()
        or (os.getenv("GUARDIAN_API_KEY") or "").strip()
    )
    if not raw:
        return None
    return raw.encode("utf-8")


def extract_media_path(url_or_path: str) -> str:
    """Return the path portion for media URLs, stripping query/fragments."""
    raw = (url_or_path or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        return parsed.path or ""
    # Relative path without scheme/netloc.
    return urlsplit(raw).path or raw


def _is_signable_media_path(path: str) -> bool:
    return path.startswith("/media/") and ".." not in path


def _signature_for_path(path: str, secret: bytes) -> str:
    digest = hmac.new(secret, path.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_media_url(url_or_path: str) -> str:
    """
    Attach a deterministic HMAC signature to /media URLs.

    Non-media URLs are returned unchanged.
    """
    raw = (url_or_path or "").strip()
    if not raw:
        return raw

    parsed = urlsplit(raw)
    path = (
        parsed.path
        if (parsed.scheme or parsed.netloc)
        else extract_media_path(raw)
    )
    if not _is_signable_media_path(path):
        return raw

    secret = _media_signing_secret()
    if secret is None:
        return raw

    sig = _signature_for_path(path, secret)
    query_items = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k != MEDIA_SIG_QUERY_KEY
    ]
    query_items.append((MEDIA_SIG_QUERY_KEY, sig))
    signed_query = urlencode(query_items, doseq=True)

    if parsed.scheme or parsed.netloc:
        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                path,
                signed_query,
                parsed.fragment,
            )
        )

    return urlunsplit(("", "", path, signed_query, ""))


def verify_media_signature(path: str, signature: str | None) -> bool:
    """Verify that a /media request path carries a valid HMAC signature."""
    provided = (signature or "").strip()
    if not provided:
        return False

    normalized_path = extract_media_path(path)
    if not _is_signable_media_path(normalized_path):
        return False

    secret = _media_signing_secret()
    if secret is None:
        return False

    expected = _signature_for_path(normalized_path, secret)
    return hmac.compare_digest(provided, expected)


__all__ = [
    "MEDIA_SIG_QUERY_KEY",
    "extract_media_path",
    "sign_media_url",
    "verify_media_signature",
]
