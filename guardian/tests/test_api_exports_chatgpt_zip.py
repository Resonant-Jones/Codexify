import io
import json
import zipfile

from guardian.core.auth import AuthenticatedUser
from guardian.routes import api_exports


def test_export_chatgpt_zip_includes_manifest_and_both_formats(monkeypatch):
    user = AuthenticatedUser(id="user-123", kind="api-key")

    threads = [
        {
            "id": 7,
            "user_id": "user-123",
            "title": "Project Alpha",
            "summary": "",
            "project_id": 42,
            "project_name": "Resonant Constructs",
            "metadata": {
                "import_source": "chatgpt",
                "import_profile": "chatgpt_v1_canonical",
                "source_thread_id": "abc-123-thread",
                "source_conversation_template_id": "g-p-template-01",
            },
        }
    ]
    message_map = {
        7: [
            {
                "id": 100,
                "thread_id": 7,
                "role": "user",
                "content": "Hello",
                "created_at": "2026-02-01T00:00:00+00:00",
                "extra_meta": {
                    "source_thread_id": "abc-123-thread",
                    "source_message_id": "m1",
                    "turn_index": 0,
                },
            },
            {
                "id": 101,
                "thread_id": 7,
                "role": "assistant",
                "content": "Hi there",
                "event_at": "2026-02-01T00:00:01+00:00",
                "extra_meta": {
                    "source_thread_id": "abc-123-thread",
                    "source_message_id": "m2",
                    "turn_index": 1,
                },
            },
        ]
    }

    def fake_fetch_threads(user_id, *, project_id=None, chunk_size=128):
        assert user_id == "user-123"
        assert project_id is None
        _ = chunk_size
        yield from threads

    def fake_fetch_messages(thread_id):
        return list(message_map.get(thread_id, []))

    monkeypatch.setattr(
        api_exports.db,
        "fetch_imported_chatgpt_threads_for_user",
        fake_fetch_threads,
        raising=False,
    )
    monkeypatch.setattr(
        api_exports.db,
        "fetch_imported_chatgpt_messages_for_thread",
        fake_fetch_messages,
        raising=False,
    )

    response = api_exports.export_chatgpt_zip(
        user=user, project_id=None, format="both"
    )
    assert response.status_code == 200
    assert response.media_type == "application/zip"

    archive = zipfile.ZipFile(io.BytesIO(response.body), "r")
    names = archive.namelist()
    assert "manifest.json" in names
    assert any(
        name.endswith(".json") and name != "manifest.json" for name in names
    )
    assert any(name.endswith(".md") for name in names)

    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["totals"]["threads"] == 1
    assert manifest["totals"]["messages"] == 2
    assert manifest["filters"]["format"] == "both"

    payload_name = next(
        name
        for name in names
        if name.endswith(".json") and name != "manifest.json"
    )
    payload = json.loads(archive.read(payload_name).decode("utf-8"))
    assert payload["project"]["id"] == 42
    assert payload["messages"][0]["source_message_id"] == "m1"
    assert payload["messages"][1]["role"] == "assistant"


def test_export_chatgpt_zip_honors_format_and_project_scope(monkeypatch):
    user = AuthenticatedUser(id="user-456", kind="api-key")
    captured = {}

    def fake_fetch_threads(user_id, *, project_id=None, chunk_size=128):
        captured["user_id"] = user_id
        captured["project_id"] = project_id
        _ = chunk_size
        yield {
            "id": 99,
            "user_id": user_id,
            "title": "Scoped Thread",
            "summary": "",
            "project_id": 7,
            "project_name": "Imports",
            "metadata": {
                "import_source": "chatgpt",
                "source_thread_id": "scope-source",
            },
        }

    def fake_fetch_messages(thread_id):
        assert thread_id == 99
        return [
            {
                "id": 1,
                "thread_id": 99,
                "role": "user",
                "content": "Scoped",
                "created_at": "2026-01-01T00:00:00+00:00",
                "extra_meta": {
                    "source_thread_id": "scope-source",
                    "source_message_id": "m1",
                    "turn_index": 0,
                },
            }
        ]

    monkeypatch.setattr(
        api_exports.db,
        "fetch_imported_chatgpt_threads_for_user",
        fake_fetch_threads,
        raising=False,
    )
    monkeypatch.setattr(
        api_exports.db,
        "fetch_imported_chatgpt_messages_for_thread",
        fake_fetch_messages,
        raising=False,
    )

    response = api_exports.export_chatgpt_zip(
        user=user, project_id=7, format="json"
    )
    assert response.status_code == 200

    archive = zipfile.ZipFile(io.BytesIO(response.body), "r")
    names = archive.namelist()
    assert captured["user_id"] == "user-456"
    assert captured["project_id"] == 7
    assert "manifest.json" in names
    assert any(
        name.endswith(".json") and name != "manifest.json" for name in names
    )
    assert not any(name.endswith(".md") for name in names)


def test_export_chatgpt_zip_dedupes_colliding_paths(monkeypatch):
    user = AuthenticatedUser(id="user-789", kind="api-key")

    threads = [
        {
            "id": 1,
            "user_id": "user-789",
            "title": "Duplicate Title",
            "summary": "",
            "project_id": 1,
            "project_name": "Imports",
            "metadata": {
                "import_source": "chatgpt",
                "source_thread_id": "same-source-thread",
            },
        },
        {
            "id": 2,
            "user_id": "user-789",
            "title": "Duplicate Title",
            "summary": "",
            "project_id": 1,
            "project_name": "Imports",
            "metadata": {
                "import_source": "chatgpt",
                "source_thread_id": "same-source-thread",
            },
        },
    ]

    message_map = {
        1: [
            {
                "id": 11,
                "thread_id": 1,
                "role": "user",
                "content": "A",
                "created_at": "2026-01-01T00:00:00+00:00",
                "extra_meta": {"source_thread_id": "same-source-thread"},
            }
        ],
        2: [
            {
                "id": 21,
                "thread_id": 2,
                "role": "assistant",
                "content": "B",
                "created_at": "2026-01-01T00:00:01+00:00",
                "extra_meta": {"source_thread_id": "same-source-thread"},
            }
        ],
    }

    def fake_fetch_threads(user_id, *, project_id=None, chunk_size=128):
        assert user_id == "user-789"
        assert project_id is None
        _ = chunk_size
        yield from threads

    def fake_fetch_messages(thread_id):
        return list(message_map.get(thread_id, []))

    monkeypatch.setattr(
        api_exports.db,
        "fetch_imported_chatgpt_threads_for_user",
        fake_fetch_threads,
        raising=False,
    )
    monkeypatch.setattr(
        api_exports.db,
        "fetch_imported_chatgpt_messages_for_thread",
        fake_fetch_messages,
        raising=False,
    )

    response = api_exports.export_chatgpt_zip(
        user=user, project_id=None, format="json"
    )
    assert response.status_code == 200

    archive = zipfile.ZipFile(io.BytesIO(response.body), "r")
    json_names = sorted(
        name
        for name in archive.namelist()
        if name.endswith(".json") and name != "manifest.json"
    )
    assert len(json_names) == 2
    assert json_names[0].startswith("projects/imports__1/")
    assert json_names[1].startswith("projects/imports__1/")
    assert any(" (2).json" in name for name in json_names)
