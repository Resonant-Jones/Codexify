from pathlib import Path

import yaml

from guardian.core.supported_profile import load_supported_profile


def test_v1_supported_profile_manifest_loads() -> None:
    manifest = load_supported_profile("v1-local-core-web-mcp")

    assert manifest.name == "v1-local-core-web-mcp"
    assert manifest.provider_contract["LLM_PROVIDER"] == "local"
    assert (
        manifest.provider_contract["LOCAL_BASE_URL"]
        == "http://host.docker.internal:8000/v1"
    )
    assert manifest.provider_contract["LOCAL_API_KEY"] == "local"
    assert "LOCAL_PROVIDER_VENDOR" not in manifest.provider_contract
    assert manifest.route_status("command_bus") == "internal_only"
    assert manifest.route_status("personal_facts") == "enabled"
    assert manifest.route_status("tools") == "quarantined"
    assert manifest.route_status("media") == "enabled"
    assert manifest.route_status("obsidian") == "enabled"


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
        assert manifest.route_status(label) == "quarantined", (
            f"{label!r} must be quarantined in tester profile"
        )


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

    assert manifest.route_status("auth") == "quarantined", (
        "auth must remain quarantined in the default dev profile"
    )


def test_tester_profile_yaml_file_exists() -> None:
    profile_path = Path("config/supported_profiles/v1-friends-family-web.yaml")
    assert profile_path.exists(), f"{profile_path} is missing"

    with profile_path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    assert isinstance(payload, dict)
    assert payload.get("name") == "v1-friends-family-web"
    assert "auth" in payload.get("route_posture", {}).get("enabled", [])
