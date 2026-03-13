from guardian.core.supported_profile import load_supported_profile


def test_v1_supported_profile_manifest_loads() -> None:
    manifest = load_supported_profile("v1-local-core-web-mcp")

    assert manifest.name == "v1-local-core-web-mcp"
    assert manifest.provider_contract["LLM_PROVIDER"] == "local"
    assert (
        manifest.provider_contract["LOCAL_BASE_URL"]
        == "http://host.docker.internal:11434/v1"
    )
    assert manifest.route_status("command_bus") == "internal_only"
    assert manifest.route_status("tools") == "quarantined"
    assert manifest.route_status("media") == "enabled"
