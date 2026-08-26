from pathlib import Path

import yaml

from guardian.core.config import Settings
from guardian.core.provider_registry import (
    default_model_for_provider,
    provider_authorized,
    provider_availability,
)
from guardian.core.supported_profile import load_supported_profile


_TESTER_TRACKED_DEFAULT_MODEL = "qwen3.8-27b-4bit"


def test_v1_supported_profile_manifest_loads() -> None:
    manifest = load_supported_profile("v1-local-core-web-mcp")

    assert manifest.name == "v1-local-core-web-mcp"
    assert manifest.provider_contract == {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
        "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_COMPAT_FIRST": True,
        "LOCAL_PROVIDER_DISPLAY_NAME": "Whoosh'd",
        "LOCAL_PROVIDER_VENDOR": "whooshd",
    }
    assert manifest.route_status("command_bus") == "internal_only"
    assert manifest.route_status("personal_facts") == "enabled"
    assert manifest.route_status("tools") == "quarantined"
    assert manifest.route_status("media") == "enabled"
    assert manifest.route_status("obsidian") == "enabled"
    assert manifest.route_status("agent_orchestration") == "enabled"
    assert manifest.route_status("agent_orchestration_chat") == "enabled"
    assert manifest.route_status("imprint") == "enabled"
    assert manifest.route_status("system_prompt") == "enabled"
    assert manifest.route_status("system_docs") == "enabled"
    assert manifest.route_status("connections") == "enabled"
    # MiniMax OAuth provider-specific auth route is internal-only,
    # not Beta-Supported and not quarantined.
    assert manifest.route_status("minimax_oauth") == "internal_only"
    assert manifest.route_status("notion_knowledge") == "enabled"
    assert manifest.route_status("notion_setup") == "internal_only"
    assert manifest.route_status("google_drive_knowledge") == "enabled"
    assert manifest.route_status("google_drive_setup") == "internal_only"
    # The read-only catalog promotion must not expose legacy connector
    # mutation or sync routes.
    assert manifest.route_status("connectors") == "quarantined"


# ---------------------------------------------------------------------------
# v1-friends-family-web tester profile tests
# ---------------------------------------------------------------------------


def test_tester_profile_manifest_loads() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    assert manifest.name == "v1-friends-family-web"
    assert manifest.version == 1
    assert manifest.surface == "local-docker-compose-webui"


def test_tester_profile_auth_enabled() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    assert manifest.route_status("auth") == "enabled"


def test_tester_profile_chat_enabled() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    assert manifest.route_status("chat") == "enabled"
    assert manifest.route_status("api_chat") == "enabled"


def test_tester_profile_hosted_room_routes_enabled() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    assert manifest.route_status("hosted_rooms") == "enabled"
    assert manifest.route_status("hosted_room_guest") == "enabled"


def test_hosted_room_routes_remain_quarantined_outside_room_enabled_profiles() -> None:
    profiles_dir = Path("config/supported_profiles")

    # The only profiles permitted to enable the Hosted Room route families
    # are the two explicit tester/private-preview profiles below. Every other
    # supported profile must leave both labels quarantined.
    room_enabled_profiles = {
        "v1-friends-family-web",
        "v1-whooshd-deepseek-web",
    }
    for profile_path in profiles_dir.glob("*.yaml"):
        manifest = load_supported_profile(profile_path.stem)
        if manifest.name in room_enabled_profiles:
            continue
        assert manifest.route_status("hosted_rooms") == "quarantined"
        assert manifest.route_status("hosted_room_guest") == "quarantined"


def test_tester_profile_unknown_route_defaults_quarantined() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    assert manifest.route_status("__missing__") == "quarantined"
    assert manifest.route_status("") == "quarantined"


def test_tester_profile_user_profile_quarantined() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    # user_profile is not required for register/login; the auth routes
    # operate directly against the User model.  It is left quarantined
    # to keep the tester surface minimal.
    assert manifest.route_status("user_profile") == "quarantined"


def test_tester_profile_deepseek_provider_contract() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    assert manifest.provider_contract["LLM_PROVIDER"] == "deepseek"
    assert manifest.provider_contract["ALLOW_CLOUD_PROVIDERS"] is True
    assert manifest.provider_contract["CODEXIFY_LOCAL_ONLY_MODE"] is False
    assert manifest.provider_contract["CODEXIFY_EGRESS_ALLOWLIST"] == "deepseek"


def test_whooshd_deepseek_profile_pins_both_provider_lanes() -> None:
    manifest = load_supported_profile("v1-whooshd-deepseek-web")

    assert manifest.provider_contract == {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": True,
        "CODEXIFY_LOCAL_ONLY_MODE": False,
        "CODEXIFY_EGRESS_ALLOWLIST": "deepseek",
        "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_PROVIDER_VENDOR": "whooshd",
        "LOCAL_CHAT_MODEL": _TESTER_TRACKED_DEFAULT_MODEL,
        "DEEPSEEK_CHAT_MODEL": "deepseek-v4-flash",
    }


def test_whooshd_deepseek_profile_enables_bounded_preview_routes() -> None:
    manifest = load_supported_profile("v1-whooshd-deepseek-web")

    assert manifest.name == "v1-whooshd-deepseek-web"
    assert manifest.version == 1
    assert manifest.surface == "local-docker-compose-webui"
    for route in {
        "health",
        "dashboard",
        "chat",
        "api_chat",
        "threads",
        "projects",
        "api_projects",
        "documents",
        "media",
        "auth",
    }:
        assert manifest.route_status(route) == "enabled"


def test_whooshd_deepseek_profile_enables_hosted_room_routes() -> None:
    """The canonical friends/family tester profile explicitly admits the
    existing Hosted Room owner/guest route families for private-preview
    collaboration qualification."""
    manifest = load_supported_profile("v1-whooshd-deepseek-web")

    assert manifest.route_status("hosted_rooms") == "enabled"
    assert manifest.route_status("hosted_room_guest") == "enabled"


def test_whooshd_deepseek_profile_quarantines_high_blast_routes() -> None:
    manifest = load_supported_profile("v1-whooshd-deepseek-web")

    for route in {
        "admin",
        "federation",
        "collaboration",
        "connectors",
        "flows",
        "tools",
        "api_tools",
        "codex",
        "cron",
        "agent",
        "agent_orchestration",
        "agent_orchestration_chat",
        "user_profile",
    }:
        assert manifest.route_status(route) == "quarantined"


def test_whooshd_deepseek_profile_has_no_route_overlap() -> None:
    manifest = load_supported_profile("v1-whooshd-deepseek-web")

    enabled = set(manifest.enabled_routes)
    internal = set(manifest.internal_only_routes)
    quarantined = set(manifest.quarantined_routes)
    assert not enabled & internal
    assert not enabled & quarantined
    assert not internal & quarantined


def test_whooshd_deepseek_registry_authorizes_only_bounded_cloud_lane(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    settings = Settings(
        _env_file=None,
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_API_KEY="local",
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_CHAT_MODEL=_TESTER_TRACKED_DEFAULT_MODEL,
        DEEPSEEK_API_KEY="inert-deepseek-test-key",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
        OPENAI_API_KEY=None,
        GROQ_API_KEY=None,
        MINIMAX_API_KEY=None,
        ALIBABA_API_KEY=None,
        ANTHROPIC_API_KEY=None,
        GEMINI_API_KEY=None,
    )

    assert provider_authorized("local", settings) is True
    assert provider_authorized("deepseek", settings) is True
    assert provider_availability("deepseek", settings) == (True, None)
    assert (
        default_model_for_provider("deepseek", settings) == "deepseek-v4-flash"
    )
    for provider in {
        "openai",
        "groq",
        "minimax",
        "alibaba",
        "anthropic",
        "gemini",
    }:
        assert provider_authorized(provider, settings) is False
        assert provider_availability(provider, settings)[0] is False


def test_tester_profile_high_blast_routes_quarantined() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    quarantined_labels = {
        "federation",
        "collaboration",
        "connectors",
        "google_connect",
        "flows",
        "tools",
        "api_tools",
        "exports",
        "codex",
        "devtools",
        "websocket",
        "cron",
        "agent_orchestration",
        "agent_orchestration_chat",
        "agent",
        "voice",
        "share",
        "graph",
    }
    for label in quarantined_labels:
        assert (
            manifest.route_status(label) == "quarantined"
        ), f"{label!r} must be quarantined in tester profile"


def test_tester_profile_no_overlapping_route_labels() -> None:
    manifest = load_supported_profile("v1-friends-family-web")

    enabled = set(manifest.enabled_routes)
    internal = set(manifest.internal_only_routes)
    quarantined = set(manifest.quarantined_routes)

    assert not (enabled & internal), f"overlap: {enabled & internal}"
    assert not (enabled & quarantined), f"overlap: {enabled & quarantined}"
    assert not (internal & quarantined), f"overlap: {internal & quarantined}"


def test_dev_profile_auth_still_quarantined() -> None:
    manifest = load_supported_profile("v1-local-core-web-mcp")

    assert (
        manifest.route_status("auth") == "quarantined"
    ), "auth must remain quarantined in the default dev profile"


def test_tester_profile_yaml_file_exists() -> None:
    profile_path = Path("config/supported_profiles/v1-friends-family-web.yaml")
    assert profile_path.exists(), f"{profile_path} is missing"

    with profile_path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    assert isinstance(payload, dict)
    assert payload.get("name") == "v1-friends-family-web"
    assert "auth" in payload.get("route_posture", {}).get("enabled", [])


# ---------------------------------------------------------------------------
# Agent orchestration (Coding Loop) route posture in v1-local-core-web-mcp
# ---------------------------------------------------------------------------


def test_local_profile_agent_orchestration_is_enabled() -> None:
    """Coding Loop execute and readback routes must be reachable
    in the supported local operator profile."""
    manifest = load_supported_profile("v1-local-core-web-mcp")

    assert manifest.route_status("agent_orchestration") == "enabled"
    assert manifest.route_status("agent_orchestration_chat") == "enabled"


def test_local_profile_unrelated_orchestration_remains_quarantined() -> None:
    """Do not expose general agent, delegation, or autonomous-execution
    routes while enabling the bounded Coding Loop family."""
    manifest = load_supported_profile("v1-local-core-web-mcp")

    unrelated_quarantined = {
        "agent",  # general agent routes
        "federation",
        "collaboration",
        "tools",
        "api_tools",
        "codex",
        "cron",
        "flows",
        "voice",
        "hosted_rooms",
        "hosted_room_guest",
    }
    for label in unrelated_quarantined:
        assert (
            manifest.route_status(label) == "quarantined"
        ), f"{label!r} must remain quarantined in the local profile"


def test_local_profile_agent_orchestration_does_not_leak_internal_only() -> None:
    """Coding work orders remain internal-only; Coding Loop routes
    are enabled but must not widen the internal surface."""
    manifest = load_supported_profile("v1-local-core-web-mcp")

    assert manifest.route_status("coding_work_orders") == "internal_only"
    assert manifest.route_status("command_bus") == "internal_only"


def test_local_profile_no_overlapping_route_labels() -> None:
    manifest = load_supported_profile("v1-local-core-web-mcp")

    enabled = set(manifest.enabled_routes)
    internal = set(manifest.internal_only_routes)
    quarantined = set(manifest.quarantined_routes)

    assert not (enabled & internal), f"overlap: {enabled & internal}"
    assert not (enabled & quarantined), f"overlap: {enabled & quarantined}"
    assert not (internal & quarantined), f"overlap: {internal & quarantined}"
