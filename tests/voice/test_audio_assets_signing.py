from __future__ import annotations

from guardian.voice import audio_assets


def test_signed_asset_url_signs_local_media_path(monkeypatch):
    monkeypatch.setenv("GUARDIAN_MEDIA_URL_SECRET", "voice-test-secret")

    signed_url, expires_at = audio_assets._signed_asset_url(
        "/media/audio/messages/123.wav"
    )

    assert signed_url.startswith("/media/audio/messages/123.wav?sig=")
    assert expires_at is None


def test_signed_asset_url_signs_local_storage_key(monkeypatch):
    monkeypatch.setenv("GUARDIAN_MEDIA_URL_SECRET", "voice-test-secret")

    signed_url, expires_at = audio_assets._signed_asset_url(
        "audio/messages/abc.wav"
    )

    assert signed_url.startswith("/media/audio/messages/abc.wav?sig=")
    assert expires_at is None


def test_signed_asset_url_uses_storage_signer_for_remote(monkeypatch):
    class _DummyStorage:
        def sign_url(self, url: str):
            return {"url": f"{url}?token=signed", "expires_at": 1700000000000}

    monkeypatch.setattr(audio_assets, "_storage", _DummyStorage())

    signed_url, expires_at = audio_assets._signed_asset_url(
        "https://example.com/audio/1.wav"
    )

    assert signed_url == "https://example.com/audio/1.wav?token=signed"
    assert expires_at == 1700000000000
