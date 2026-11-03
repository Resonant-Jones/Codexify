"""Catalog projection for the qualified AeroLeads provider (Gate B Slice 6).

Covers the canonical identity, ADR-075 classification, truthful partial /
unavailable states, the existing runtime binding, the absence of any setup
or credential surface, construction without gateway contact, the
`/api/connections` projection, and the exact before/after delta against the
pre-slice baseline.
"""

from __future__ import annotations

import inspect
import json
import socket

from guardian.connections import catalog as catalog_module
from guardian.connections.catalog import (
    _build_catalog,
    get_catalog,
    get_connection,
)

# Pre-slice baseline: every catalog id at the parent commit. The only
# permitted delta is the addition of "aeroleads".
BASELINE_IDS = frozenset({
    "alibaba_dashscope", "anthropic_api", "anthropic_subscription",
    "api_server", "aws_bedrock", "azure", "bluebubbles_imessage", "brave",
    "codex_chatgpt", "custom_openai_compatible", "ddgs", "deepseek",
    "dingtalk", "discord", "email", "exa", "feishu_lark", "firecrawl",
    "gemini_api", "gemini_oauth", "github_copilot", "google_chat",
    "google_drive", "groq", "home_assistant", "huggingface", "kimi_moonshot",
    "line", "lm_studio", "matrix", "mattermost", "microsoft_teams",
    "minimax_api", "minimax_oauth", "notion", "nous_portal", "ntfy",
    "nvidia", "ollama_cloud", "openai_api", "openrouter", "parallel",
    "qq_bot", "qwen_oauth", "searxng", "signal", "slack", "sms_twilio",
    "stepfun", "tavily", "telegram", "webhooks", "wecom", "weixin_wechat",
    "whatsapp", "xai_api", "xai_grok", "xai_oauth", "yuanbao",
})


def test_exactly_one_aeroleads_identity_and_no_custodian_identity() -> None:
    ids = [entry.id for entry in get_catalog()]
    assert ids.count("aeroleads") == 1
    assert get_connection("openconnector") is None
    assert get_connection("aeroleads_action") is None


def test_aeroleads_category_and_capability_semantics() -> None:
    entry = get_connection("aeroleads")
    assert entry is not None
    assert entry.display_name == "AeroLeads"
    # ADR-075: retrieval about a Web resource through a Web-provider
    # surface is web; AeroLeads is not a user-scoped content repository,
    # so the knowledge vocabulary must not be repurposed here.
    assert entry.category == "web"
    assert set(entry.capabilities) == {"extract"}
    assert "content_read" not in entry.capabilities
    assert "content_search" not in entry.capabilities
    assert "search" not in entry.capabilities


def test_aeroleads_is_partial_with_unavailable_setup() -> None:
    entry = get_connection("aeroleads")
    assert entry is not None
    assert entry.implementation_state == "partial"
    assert entry.default_setup_state == "unavailable"
    assert entry.auth_methods == ("api_key",)


def test_aeroleads_binds_the_existing_openconnector_adapter() -> None:
    entry = get_connection("aeroleads")
    assert entry is not None
    binding = entry.runtime_binding
    assert binding.subsystem == "guardian.connections.openconnector"
    assert binding.adapter == (
        "guardian.connections.openconnector.adapter.OpenConnectorAdapter"
    )
    assert binding.setup_route is None
    assert binding.oauth_backend_handler_exists is False
    assert binding.registry_provider_id is None


def test_aeroleads_advertises_no_setup_surface() -> None:
    entry = get_connection("aeroleads")
    assert entry is not None
    assert entry.required_fields == ()
    assert entry.scopes == ()
    assert entry.oauth_provider_key is None


def test_aeroleads_description_states_present_limits() -> None:
    entry = get_connection("aeroleads")
    assert entry is not None
    text = f"{entry.description} {entry.setup_help}"
    assert "internal-only" in text or "internal only" in text
    assert "not available" in text
    assert "external evidence" in text
    assert "Beta" not in text


def test_aeroleads_serializes_no_credential_material() -> None:
    entry = get_connection("aeroleads")
    assert entry is not None
    corpus = json.dumps(entry.as_dict(), default=str)
    for marker in ("oct_", "Bearer ", "api_key_value", "FAKE_GATEB5",
                   "admin_token", "encryption_key"):
        assert marker not in corpus
    for f in entry.required_fields:
        assert f.secret is False


def test_catalog_construction_makes_no_network_calls(monkeypatch) -> None:
    source = inspect.getsource(catalog_module)
    for client in ("httpx", "aiohttp", "urllib", "requests", "websocket"):
        assert client not in source

    def _refused(*args, **kwargs):
        raise AssertionError("catalog construction attempted network I/O")

    monkeypatch.setattr(socket, "create_connection", _refused)
    monkeypatch.setattr(socket, "socket", _refused)
    fresh = _build_catalog()
    assert {entry.id for entry in fresh} == (
        set(BASELINE_IDS) | {"aeroleads"}
    )
    for entry in fresh:
        entry.as_dict()


def test_catalog_delta_is_exactly_the_aeroleads_entry() -> None:
    current = {entry.id for entry in get_catalog()}
    assert current - set(BASELINE_IDS) == {"aeroleads"}
    assert set(BASELINE_IDS) - current == set()


def test_connections_projection_lists_aeroleads_without_authority() -> None:
    """`GET /api/connections` shows the entry but grants nothing.

    Catalog visibility, not execution promotion: the projected item carries
    the partial/unavailable states, no setup route, no OAuth affordance,
    and no per-account connection material.
    """
    import os

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from guardian.routes import connections as connections_routes

    connections_routes.configure_db(None)
    app = FastAPI(title="slice6-projection", version="1.0.0")
    app.include_router(connections_routes.router)
    api_key = os.environ.get("GUARDIAN_API_KEY", "test-api-key")
    client = TestClient(app, raise_server_exceptions=False)
    with client:
        response = client.get(
            "/api/connections",
            headers={"X-API-Key": api_key, "X-User-Id": "slice6-user"},
        )
    assert response.status_code == 200, response.text
    items = {item["id"]: item for item in response.json()["items"]}
    assert set(BASELINE_IDS) - set(items) == set()
    item = items["aeroleads"]
    assert item["implementation_state"] == "partial"
    assert item["setup_state"] == "unavailable"
    assert item["runtime_binding"]["setup_route"] is None
    assert item["runtime_binding"]["adapter"] == (
        "guardian.connections.openconnector.adapter.OpenConnectorAdapter"
    )
    assert item["oauth"] is None
    assert item["validation"] is None
    corpus = json.dumps(item, default=str)
    for marker in ("oct_", "Bearer ", "connection_id", "allowedConnections",
                   "runtime_token"):
        assert marker not in corpus


def test_notion_and_drive_projections_are_preserved() -> None:
    notion = get_connection("notion")
    assert notion is not None
    assert notion.implementation_state == "implemented"
    assert notion.capabilities == {"content_search", "content_read"}
    assert notion.runtime_binding.setup_route == "/api/connect/notion/configure"
    drive = get_connection("google_drive")
    assert drive is not None
    assert drive.implementation_state == "implemented"
    assert drive.capabilities == {"content_search", "content_read"}
    assert drive.runtime_binding.setup_route == "/api/connect/google-drive/start"
