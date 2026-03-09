from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.orm.exc import DetachedInstanceError

from guardian.voice import audio_assets


class _DetachOnCloseRow:
    def __init__(self, **data):
        self._data = data
        self._detached = False

    def detach(self):
        self._detached = True

    def _get(self, key):
        if self._detached:
            raise DetachedInstanceError(
                f"Attribute '{key}' was accessed after the session closed"
            )
        return self._data[key]

    @property
    def id(self):
        return self._get("id")

    @property
    def message_id(self):
        return self._get("message_id")

    @property
    def provider(self):
        return self._get("provider")

    @property
    def voice(self):
        return self._get("voice")

    @property
    def text_hash(self):
        return self._get("text_hash")

    @property
    def src_url(self):
        return self._get("src_url")

    @property
    def internal_format(self):
        return self._get("internal_format")

    @property
    def delivery_variants_json(self):
        return self._get("delivery_variants_json")

    @property
    def duration_seconds(self):
        return self._get("duration_seconds")

    @property
    def filesize_bytes(self):
        return self._get("filesize_bytes")

    @property
    def created_at(self):
        return self._get("created_at")


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


def test_save_message_audio_asset_updates_existing_placeholder_row(
    monkeypatch,
):
    existing_row = SimpleNamespace(
        id=9,
        message_id=55,
        provider="chatterbox",
        voice="assistant",
        text_hash="pending",
        src_url="",
        internal_format="wav",
        delivery_variants_json={
            "status": "pending",
            "source": "assistant_message_autogenerate",
        },
        duration_seconds=None,
        filesize_bytes=None,
        created_at=datetime(2026, 3, 8, 12, 0, tzinfo=timezone.utc),
    )

    class _FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

        def refresh(self, _row):
            return None

    class _FakeDB:
        def get_session(self):
            return _FakeSession()

    monkeypatch.setattr(audio_assets, "_db", lambda: _FakeDB())
    monkeypatch.setattr(
        audio_assets,
        "_latest_asset_row",
        lambda *args, **kwargs: existing_row,
    )
    monkeypatch.setattr(
        audio_assets._storage,
        "upload_file",
        lambda *_args, **_kwargs: "/media/audio/messages/55.wav",
    )

    payload = audio_assets.save_message_audio_asset(
        message_id=55,
        text="hello world",
        provider="chatterbox",
        voice="assistant",
        audio_bytes=b"RIFF....WAVE",
        audio_format="wav",
        delivery_variants_json={
            "source": "assistant_message_autogenerate",
            "thread_id": 12,
        },
    )

    assert existing_row.src_url == "/media/audio/messages/55.wav"
    assert existing_row.delivery_variants_json["status"] == "ready"
    assert existing_row.delivery_variants_json["thread_id"] == 12
    assert payload["id"] == 9
    assert payload["status"] == "ready"
    assert payload["stream_url"] == "/api/voice/audio/9"


def test_signed_asset_url_normalizes_empty_storage_path():
    signed_url, expires_at = audio_assets._signed_asset_url("")

    assert signed_url is None
    assert expires_at is None


def test_find_cached_asset_ignores_pending_placeholder_rows(monkeypatch):
    pending_row = SimpleNamespace(
        id=10,
        message_id=56,
        provider="chatterbox",
        voice="assistant",
        text_hash="abc",
        src_url="",
        internal_format="wav",
        delivery_variants_json={"status": "pending"},
        duration_seconds=None,
        filesize_bytes=None,
        created_at=datetime(2026, 3, 8, 12, 5, tzinfo=timezone.utc),
    )

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first(self):
            return pending_row

    class _FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeDB:
        def get_session(self):
            return _FakeSession()

    monkeypatch.setattr(audio_assets, "_db", lambda: _FakeDB())
    monkeypatch.setattr(
        audio_assets,
        "_base_asset_query",
        lambda *args, **kwargs: _FakeQuery(),
    )

    payload = audio_assets.find_cached_asset(
        message_id=56,
        provider="chatterbox",
        voice="assistant",
        text_hash="abc",
    )

    assert payload is None


def test_list_message_audio_assets_supports_postgres_chatlog_db_sessions(
    monkeypatch,
):
    ready_row = _DetachOnCloseRow(
        id=12,
        message_id=77,
        provider="chatterbox",
        voice="assistant",
        text_hash="abc123",
        src_url="/media/audio/messages/77.wav",
        internal_format="wav",
        delivery_variants_json={
            "status": "ready",
            "source": "assistant_message_autogenerate",
            "mime_type": "audio/wav",
        },
        duration_seconds=1.5,
        filesize_bytes=256,
        created_at=datetime(2026, 3, 8, 13, 0, tzinfo=timezone.utc),
    )

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return list(self._rows)

    class _FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            ready_row.detach()
            return False

        def query(self, _model):
            return _FakeQuery([ready_row])

    class _FakePostgresChatLogDB:
        def _sa_session(self):
            return _FakeSession()

    monkeypatch.setenv("GUARDIAN_MEDIA_URL_SECRET", "voice-test-secret")
    monkeypatch.setattr(
        audio_assets,
        "_db",
        lambda: _FakePostgresChatLogDB(),
    )

    payload = audio_assets.list_message_audio_assets(
        message_ids=[77],
        preferred_source="assistant_message_autogenerate",
    )

    assert 77 in payload
    assert payload[77]["id"] == 12
    assert payload[77]["status"] == "ready"
    assert payload[77]["stream_url"] == "/api/voice/audio/12"
    assert payload[77]["mime_type"] == "audio/wav"


def test_list_message_audio_assets_keeps_pending_and_failed_states_detached_safe(
    monkeypatch,
):
    pending_row = _DetachOnCloseRow(
        id=13,
        message_id=88,
        provider="chatterbox",
        voice="assistant",
        text_hash="pending123",
        src_url="",
        internal_format="wav",
        delivery_variants_json={
            "status": "pending",
            "source": "assistant_message_autogenerate",
            "mime_type": "audio/wav",
        },
        duration_seconds=None,
        filesize_bytes=None,
        created_at=datetime(2026, 3, 8, 13, 5, tzinfo=timezone.utc),
    )
    failed_row = _DetachOnCloseRow(
        id=14,
        message_id=89,
        provider="chatterbox",
        voice="assistant",
        text_hash="failed123",
        src_url="",
        internal_format="wav",
        delivery_variants_json={
            "status": "failed",
            "source": "assistant_message_autogenerate",
            "mime_type": "audio/wav",
            "error": {"message": "generation failed"},
        },
        duration_seconds=None,
        filesize_bytes=None,
        created_at=datetime(2026, 3, 8, 13, 10, tzinfo=timezone.utc),
    )

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return list(self._rows)

    class _FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pending_row.detach()
            failed_row.detach()
            return False

        def query(self, _model):
            return _FakeQuery([pending_row, failed_row])

    class _FakePostgresChatLogDB:
        def _sa_session(self):
            return _FakeSession()

    monkeypatch.setenv("GUARDIAN_MEDIA_URL_SECRET", "voice-test-secret")
    monkeypatch.setattr(
        audio_assets,
        "_db",
        lambda: _FakePostgresChatLogDB(),
    )

    payload = audio_assets.list_message_audio_assets(
        message_ids=[88, 89],
        preferred_source="assistant_message_autogenerate",
    )

    assert payload[88]["status"] == "pending"
    assert payload[88]["stream_url"] == "/api/voice/audio/13"
    assert payload[89]["status"] == "failed"
    assert payload[89]["error"] == {"message": "generation failed"}
