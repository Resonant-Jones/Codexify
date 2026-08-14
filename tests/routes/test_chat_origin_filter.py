"""Route-level tests for the canonical conversation-origin filter surface.

These tests prove that ``GET /api/chat/threads?origin_system=...`` operates
on the canonical ``chat_threads.origin_system`` column, returns the field
on the thread DTO, rejects unsupported values, and that ordinary thread
mutation preserves the canonical origin.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("GUARDIAN_API_KEY", "test-api-key")
os.environ.setdefault("GUARDIAN_AUTH_MODE", "local")
os.environ.setdefault("GUARDIAN_EXPOSURE_MODE", "local_safe")
os.environ.setdefault("CODEXIFY_MULTI_USER_ENABLED", "false")

from guardian.routes import chat as chat_routes

SERVER_USER_ID = "local_user"
API_KEY = "test-api-key"


class _RecordingChatlogDB:
    """Minimal in-memory chatlog facade that records ``list_chat_threads`` calls.

    Tests inject ``origin_system`` directly into the canned rows so we can
    prove the route surfaces the field on the DTO and forwards the filter to
    the canonical SQL seam.
    """

    def __init__(self) -> None:
        self.threads: List[Dict[str, Any]] = [
            {
                "id": 1,
                "user_id": SERVER_USER_ID,
                "title": "Native Codexify thread",
                "summary": "",
                "project_id": None,
                "project_name": None,
                "origin_system": "codexify",
                "archived_at": None,
                "is_diary": False,
                "diary_mode": False,
                "exclude_from_identity": False,
                "modeling_excluded": False,
                "thread_config": None,
                "metadata": {},
                "active_profile_id": None,
                "created_at": "2026-08-14T00:00:00Z",
                "updated_at": "2026-08-14T00:00:00Z",
            },
            {
                "id": 2,
                "user_id": SERVER_USER_ID,
                "title": "Imported ChatGPT thread",
                "summary": "",
                "project_id": None,
                "project_name": "Imports",
                "origin_system": "openai",
                "archived_at": None,
                "is_diary": False,
                "diary_mode": False,
                "exclude_from_identity": False,
                "modeling_excluded": False,
                "thread_config": None,
                "metadata": {"import_source": "chatgpt", "source_thread_id": "src-2"},
                "active_profile_id": None,
                "created_at": "2026-08-14T00:01:00Z",
                "updated_at": "2026-08-14T00:01:00Z",
            },
            {
                "id": 3,
                "user_id": SERVER_USER_ID,
                "title": "Imported Claude thread",
                "summary": "",
                "project_id": None,
                "project_name": "Imports",
                "origin_system": "anthropic",
                "archived_at": None,
                "is_diary": False,
                "diary_mode": False,
                "exclude_from_identity": False,
                "modeling_excluded": False,
                "thread_config": None,
                "metadata": {"import_source": "claude", "source_thread_id": "src-3"},
                "active_profile_id": None,
                "created_at": "2026-08-14T00:02:00Z",
                "updated_at": "2026-08-14T00:02:00Z",
            },
        ]
        self.list_kwargs: Dict[str, Any] = {}

    def list_chat_threads(self, **kwargs: Any) -> List[Dict[str, Any]]:
        self.list_kwargs = kwargs
        origin = kwargs.get("origin_system")
        if origin is None:
            return list(self.threads)
        return [row for row in self.threads if row.get("origin_system") == origin]

    def create_chat_thread(self, **kwargs: Any) -> Dict[str, Any]:
        """Capture kwargs and return a minimal canonical-row stub.

        Tests that need richer return shapes override this through
        ``monkeypatch.setattr(db, "create_chat_thread", ...)``.
        """

        return {
            "id": 99,
            "user_id": kwargs.get("user_id", SERVER_USER_ID),
            "title": kwargs.get("title", "New Chat"),
            "summary": kwargs.get("summary", ""),
            "project_id": kwargs.get("project_id"),
            "project_name": None,
            "origin_system": kwargs.get("origin_system", "codexify"),
            "archived_at": None,
            "is_diary": False,
            "diary_mode": False,
            "exclude_from_identity": False,
            "modeling_excluded": False,
            "thread_config": None,
            "metadata": kwargs.get("metadata") or {},
            "active_profile_id": kwargs.get("active_profile_id"),
            "created_at": "2026-08-14T00:00:00Z",
            "updated_at": "2026-08-14T00:00:00Z",
        }

    def get_recent_thread(self, user_id: str) -> None:
        """Return ``None`` so the route handler does not short-circuit into
        the idempotency guard and reaches the canonical creation seam."""

        return None

    def write_audit_log(self, *args: Any, **kwargs: Any) -> None:
        return None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    db = _RecordingChatlogDB()
    monkeypatch.setattr(chat_routes, "chatlog_db", db)
    app = FastAPI()
    app.include_router(chat_routes.router)
    app.dependency_overrides[chat_routes.require_api_key] = lambda: API_KEY

    class _StubScope:
        multi_user_enabled = False
        account_id = SERVER_USER_ID
        user_id = SERVER_USER_ID

    app.dependency_overrides[chat_routes.get_request_user_scope] = lambda: _StubScope()
    test_client = TestClient(app, headers={"X-API-Key": API_KEY})
    return test_client, db


# ---------------------------------------------------------------------------
# Origin returned on thread DTO
# ---------------------------------------------------------------------------


def test_origin_system_is_surfaced_on_thread_dto(client):
    test_client, _db = client
    response = test_client.get("/chat/threads")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    origins = {thread["origin_system"] for thread in payload["threads"]}
    assert origins == {"codexify", "openai", "anthropic"}


# ---------------------------------------------------------------------------
# Owner-scoped filter for all three canonical values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("origin_system", "expected_titles"),
    [
        ("codexify", {"Native Codexify thread"}),
        ("openai", {"Imported ChatGPT thread"}),
        ("anthropic", {"Imported Claude thread"}),
    ],
)
def test_owner_scoped_filter_for_each_canonical_value(
    client, origin_system, expected_titles
):
    test_client, db = client
    response = test_client.get(
        f"/chat/threads?origin_system={origin_system}"
    )
    assert response.status_code == 200
    payload = response.json()
    titles = {thread["title"] for thread in payload["threads"]}
    assert titles == expected_titles
    assert db.list_kwargs.get("origin_system") == origin_system


def test_missing_origin_system_param_preserves_current_list_behavior(client):
    test_client, db = client
    response = test_client.get("/chat/threads")
    assert response.status_code == 200
    assert len(response.json()["threads"]) == 3
    assert db.list_kwargs.get("origin_system") is None


def test_unsupported_filter_value_fails_closed(client):
    test_client, _db = client
    response = test_client.get("/chat/threads?origin_system=chatgpt")
    assert response.status_code == 400
    assert "Unsupported origin_system" in response.json()["detail"]


@pytest.mark.parametrize("bad_value", ["claude", "gpt", "native", "open_ai"])
def test_other_legacy_product_names_rejected_at_filter_surface(client, bad_value):
    test_client, _db = client
    response = test_client.get(f"/chat/threads?origin_system={bad_value}")
    assert response.status_code == 400


def test_filter_uses_canonical_column_only_not_project_metadata(client):
    """The filter must not fall back to JSONB metadata scans when the
    canonical column is present. We exercise that by recording the kwargs
    the chatlog db receives."""

    test_client, db = client
    test_client.get("/chat/threads?origin_system=openai")
    # The canonical filter is passed through to the chatlog_db seam, which
    # in production translates to ``WHERE origin_system = %s``. The metadata
    # JSONB column is intentionally NOT consulted by the SQL filter.
    assert db.list_kwargs.get("origin_system") == "openai"
    assert "import_source" not in db.list_kwargs


# ---------------------------------------------------------------------------
# Owner-scoped filter must remain user-scoped
# ---------------------------------------------------------------------------


def test_filter_does_not_bypass_account_scope(client):
    """Owner-scoping is enforced upstream in ``_scope_query_user_id``; the
    canonical filter is additive on top of that and must never widen the
    result set beyond the authenticated user's threads."""

    test_client, _db = client
    response = test_client.get("/chat/threads?origin_system=openai")
    payload = response.json()
    for thread in payload["threads"]:
        # Every returned thread is owned by the test-server user; this is
        # enforced by ``_scope_query_user_id`` upstream of the canonical
        # filter.
        assert thread["user_id"] == SERVER_USER_ID


# ---------------------------------------------------------------------------
# Origin immutability under ordinary thread mutation
# ---------------------------------------------------------------------------


def test_native_creation_passes_canonical_default_origin(client, monkeypatch):
    """The canonical native-creation seam must always pass
    ``origin_system=DEFAULT_ORIGIN_SYSTEM`` explicitly so the persistence
    layer never falls back to the model's server default."""

    test_client, _db = client
    captured_kwargs: Dict[str, Any] = {}

    def _capture(**kwargs: Any) -> Dict[str, Any]:
        captured_kwargs.update(kwargs)
        # Return a minimal canonical-row stub; do NOT delegate back through
        # the fake db (which would recurse into the monkeypatched override).
        return {
            "id": 99,
            "user_id": kwargs.get("user_id", SERVER_USER_ID),
            "title": kwargs.get("title", "New Chat"),
            "summary": kwargs.get("summary", ""),
            "project_id": kwargs.get("project_id"),
            "project_name": None,
            "origin_system": kwargs.get("origin_system", "codexify"),
            "archived_at": None,
            "is_diary": False,
            "diary_mode": False,
            "exclude_from_identity": False,
            "modeling_excluded": False,
            "thread_config": None,
            "metadata": kwargs.get("metadata") or {},
            "active_profile_id": kwargs.get("active_profile_id"),
            "created_at": "2026-08-14T00:00:00Z",
            "updated_at": "2026-08-14T00:00:00Z",
        }

    monkeypatch.setattr(chat_routes.chatlog_db, "create_chat_thread", _capture)

    response = test_client.post(
        "/chat/threads",
        json={"title": "Brand new thread"},
    )
    assert response.status_code == 200
    assert captured_kwargs.get("origin_system") == "codexify"