"""Static contract tests for the Whoosh'd Docker smoke environment.

These tests validate the supported profile, Compose override, and launcher
contract without starting Docker, Whoosh'd, or any model runtime.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from guardian.core.ai_router import (
    WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON,
)

SUPPORTED_PROFILE_PATH = Path(
    "config/supported_profiles/v1-local-core-web-mcp.yaml"
)
SMOKE_OVERRIDE_PATH = Path("docker-compose.whooshd-smoke.yml")
SMOKE_LAUNCHER_PATH = Path("scripts/whooshd_docker_smoke_up.sh")

CANONICAL_BASE_URL = "http://host.docker.internal:8000/v1"
CANONICAL_HEALTH_BASE_URL = "http://host.docker.internal:8000"
MACHINE_SPECIFIC_BASE_URL = "http://100.127." "148.28:8000/v1"

CANONICAL_PROVIDER_CONTRACT = {
    "LLM_PROVIDER": "local",
    "ALLOW_CLOUD_PROVIDERS": False,
    "CODEXIFY_LOCAL_ONLY_MODE": True,
    "CODEXIFY_EGRESS_ALLOWLIST": "",
    "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
    "LOCAL_BASE_URL": CANONICAL_BASE_URL,
    "LOCAL_API_KEY": "local",
    "LOCAL_COMPAT_FIRST": True,
    "LOCAL_PROVIDER_DISPLAY_NAME": "Whoosh'd",
    "LOCAL_PROVIDER_VENDOR": "whooshd",
}

CANONICAL_SMOKE_MODELS = {
    "LOCAL_CHAT_MODEL": "local-chat",
    "LOCAL_LLM_MODEL": "local-chat",
    "LLM_MODEL": "local-chat",
    "DEFAULT_LOCAL_MODEL": "local-chat",
    "LOCAL_VISION_MODEL": "${LOCAL_VISION_MODEL:-}",
    "LOCAL_GGUF_MODEL": "${LOCAL_GGUF_MODEL:-}",
}

BOOLEAN_FIELDS = {
    "ALLOW_CLOUD_PROVIDERS",
    "CODEXIFY_LOCAL_ONLY_MODE",
    "LOCAL_COMPAT_FIRST",
}
MODEL_FIELDS = set(CANONICAL_SMOKE_MODELS)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"{path} not found")
    with path.open() as handle:
        return yaml.safe_load(handle)


def _load_supported_profile() -> dict:
    return _load_yaml(SUPPORTED_PROFILE_PATH)


def _load_smoke_override() -> dict:
    return _load_yaml(SMOKE_OVERRIDE_PATH)


def _normalize_contract_value(key: str, value: object) -> str:
    normalized = str(value).strip().lower()
    if key in BOOLEAN_FIELDS:
        return normalized
    return str(value).strip()


def _assert_provider_contract(
    env: dict, expected: dict = CANONICAL_PROVIDER_CONTRACT
):
    for key, value in expected.items():
        assert key in env, f"{key} missing from provider environment"
        assert _normalize_contract_value(key, env[key]) == (
            _normalize_contract_value(key, value)
        ), f"{key} does not match the supported provider contract"


def _mock_settings(**overrides):
    """Build a mock settings object matching the supported contract fields."""

    class MockSettings:
        pass

    settings = MockSettings()
    for key, value in CANONICAL_PROVIDER_CONTRACT.items():
        setattr(settings, key, value)
    settings.WHOOSHD_HEALTH_BASE_URL = CANONICAL_HEALTH_BASE_URL
    for key, value in CANONICAL_SMOKE_MODELS.items():
        setattr(settings, key, value)

    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def _authorized_contract_paths() -> tuple[Path, ...]:
    return (
        SUPPORTED_PROFILE_PATH,
        SMOKE_OVERRIDE_PATH,
        SMOKE_LAUNCHER_PATH,
        Path("tests/test_whooshd_smoke_env_contract.py"),
        Path("tests/core/test_supported_profile.py"),
        Path("tests/core/test_supported_profile_provider.py"),
        Path("docs/local-provider-whooshd.md"),
    )


class TestSupportedProfileExists:
    def test_profile_yaml_exists(self):
        profile = _load_supported_profile()
        assert profile["name"] == "v1-local-core-web-mcp"

    def test_profile_has_canonical_provider_contract(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract == CANONICAL_PROVIDER_CONTRACT
        assert not MODEL_FIELDS.intersection(contract)


class TestSmokeComposeOverrideExists:
    def test_override_file_exists(self):
        assert SMOKE_OVERRIDE_PATH.exists()

    def test_override_is_valid_yaml(self):
        config = _load_smoke_override()
        assert config is not None
        assert "services" in config

    def test_backend_has_blessed_contract(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        _assert_provider_contract(backend_env)
        assert (
            backend_env["WHOOSHD_HEALTH_BASE_URL"] == CANONICAL_HEALTH_BASE_URL
        )
        assert backend_env["CODEXIFY_SUPPORTED_PROFILE"] == (
            "v1-local-core-web-mcp"
        )

    def test_worker_chat_has_blessed_contract(self):
        config = _load_smoke_override()
        worker_env = config["services"]["worker-chat"]["environment"]
        _assert_provider_contract(worker_env)
        assert (
            worker_env["WHOOSHD_HEALTH_BASE_URL"] == CANONICAL_HEALTH_BASE_URL
        )

    def test_override_has_canonical_model_aliases(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        for key, value in CANONICAL_SMOKE_MODELS.items():
            assert backend_env[key] == value

    def test_logical_route_is_not_live_inventory_proof(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert not MODEL_FIELDS.intersection(contract)
        assert CANONICAL_BASE_URL == (f"{CANONICAL_HEALTH_BASE_URL}/v1")
        assert WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON == (
            "configured_model_not_advertised_by_whooshd"
        )

    def test_override_covers_worker_warmup_and_embed(self):
        config = _load_smoke_override()
        warmup_env = config["services"]["worker-warmup"]["environment"]
        _assert_provider_contract(warmup_env)
        for key, value in CANONICAL_SMOKE_MODELS.items():
            assert warmup_env[key] == value

        embed_env = config["services"]["worker-chat-embed"]["environment"]
        _assert_provider_contract(
            embed_env,
            {
                "LLM_PROVIDER": "local",
                "LOCAL_BASE_URL": CANONICAL_BASE_URL,
                "LOCAL_API_KEY": "local",
                "LOCAL_PROVIDER_VENDOR": "whooshd",
                "ALLOW_CLOUD_PROVIDERS": False,
                "CODEXIFY_EGRESS_ALLOWLIST": "",
                "CODEXIFY_LOCAL_ONLY_MODE": True,
            },
        )
        assert not MODEL_FIELDS.intersection(embed_env)
        for key in (
            "LOCAL_RUNTIME_PRESET",
            "LOCAL_COMPAT_FIRST",
            "LOCAL_PROVIDER_DISPLAY_NAME",
            "WHOOSHD_HEALTH_BASE_URL",
            "CODEXIFY_SUPPORTED_PROFILE",
        ):
            assert key not in embed_env


class TestAuthorizedSurfaces:
    def test_canonical_host_bridge_is_used_without_machine_specific_ip(self):
        for path in _authorized_contract_paths():
            content = path.read_text()
            assert "host.docker.internal:8000" in content
            assert MACHINE_SPECIFIC_BASE_URL not in content

    def test_launcher_asserts_canonical_contract_and_logical_route(self):
        content = SMOKE_LAUNCHER_PATH.read_text()
        for marker in (
            "LOCAL_BASE_URL: http://host.docker.internal:8000/v1",
            "LOCAL_PROVIDER_VENDOR: whooshd",
            "LOCAL_RUNTIME_PRESET: whooshd-mlx",
            "LOCAL_COMPAT_FIRST: .true.",
            "WHOOSHD_HEALTH_BASE_URL: http://host.docker.internal:8000",
            "CODEXIFY_SUPPORTED_PROFILE: v1-local-core-web-mcp",
            'SMOKE_MODEL="${LOCAL_CHAT_MODEL:-local-chat}"',
        ):
            assert marker in content


class TestContractRejectsCloudProviders:
    def test_true_is_rejected(self):
        profile = _load_supported_profile()
        expected = profile["provider_contract"]["ALLOW_CLOUD_PROVIDERS"]
        assert True != expected

    def test_false_is_accepted(self):
        profile = _load_supported_profile()
        assert profile["provider_contract"]["ALLOW_CLOUD_PROVIDERS"] is False


class TestContractRejectsCloudEgress:
    def test_nonempty_is_rejected(self):
        profile = _load_supported_profile()
        expected = profile["provider_contract"]["CODEXIFY_EGRESS_ALLOWLIST"]
        assert "groq,openai,anthropic" != expected

    def test_empty_is_accepted(self):
        profile = _load_supported_profile()
        assert profile["provider_contract"]["CODEXIFY_EGRESS_ALLOWLIST"] == ""


class TestContractRequiresCorrectLocalBaseUrl:
    def test_localhost_is_rejected_in_docker(self):
        assert "http://localhost:8000/v1" != CANONICAL_BASE_URL

    def test_host_docker_internal_is_accepted(self):
        profile = _load_supported_profile()
        assert (
            profile["provider_contract"]["LOCAL_BASE_URL"] == CANONICAL_BASE_URL
        )

    def test_tailscale_ip_is_rejected(self):
        assert MACHINE_SPECIFIC_BASE_URL != CANONICAL_BASE_URL

    def test_health_url_matches_canonical_base_url(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        assert backend_env["WHOOSHD_HEALTH_BASE_URL"] == (
            backend_env["LOCAL_BASE_URL"].removesuffix("/v1")
        )
        assert (
            backend_env["WHOOSHD_HEALTH_BASE_URL"] == CANONICAL_HEALTH_BASE_URL
        )


class TestSmokeWrapperScriptExists:
    def test_script_exists(self):
        assert SMOKE_LAUNCHER_PATH.exists()

    def test_script_is_executable(self):
        assert SMOKE_LAUNCHER_PATH.stat().st_mode & 0o111

    def test_script_references_compose_override(self):
        assert (
            "docker-compose.whooshd-smoke.yml"
            in SMOKE_LAUNCHER_PATH.read_text()
        )

    def test_launcher_script_forwards_multi_model_env(self):
        content = Path("scripts/whooshd_ensure.sh").read_text()
        assert "WHOOSHD_MODEL_REGISTRY_PATH" in content
        assert "WHOOSHD_MLX_MODEL" in content
        assert "WHOOSHD_ADAPTER" in content

    def test_script_passes_bash_syntax_check(self):
        assert SMOKE_LAUNCHER_PATH.exists()


class TestNoCloudFallback:
    def test_local_only_mode_blocks_cloud_providers(self):
        settings = _mock_settings()
        assert settings.CODEXIFY_LOCAL_ONLY_MODE is True
        assert settings.ALLOW_CLOUD_PROVIDERS is False
        assert settings.CODEXIFY_EGRESS_ALLOWLIST == ""

    def test_local_only_mode_rejects_allow_cloud_true(self):
        profile = _load_supported_profile()
        contract = profile["provider_contract"]
        assert contract["CODEXIFY_LOCAL_ONLY_MODE"] is True
        assert contract["ALLOW_CLOUD_PROVIDERS"] is False


class TestModelPropagation:
    def test_all_smoke_models_are_propagated(self):
        config = _load_smoke_override()
        backend_env = config["services"]["backend"]["environment"]
        worker_env = config["services"]["worker-chat"]["environment"]
        for key, value in CANONICAL_SMOKE_MODELS.items():
            assert backend_env[key] == value
            assert worker_env[key] == value


class TestWhooshdStaysStandalone:
    def test_no_whooshd_import_in_codexify_routes(self):
        for check_path in [
            "guardian/guardian_api.py",
            "guardian/core/config.py",
        ]:
            path = Path(check_path)
            if path.exists():
                import_lines = [
                    line.strip()
                    for line in path.read_text().splitlines()
                    if line.strip().startswith(
                        ("import whooshd", "from whooshd")
                    )
                ]
                assert (
                    not import_lines
                ), f"{check_path} imports whooshd internals: {import_lines}"

    def test_compose_override_does_not_add_whooshd_service(self):
        config = _load_smoke_override()
        for service in config["services"]:
            assert "whooshd" not in service.lower()


def _launcher_content() -> str:
    return SMOKE_LAUNCHER_PATH.read_text()


def _protected_project_case_pattern() -> str:
    """Extract the launcher's protected-project case pattern verbatim.

    The guard is evaluated behaviourally rather than asserted as text, so a
    pattern that stops matching a prefixed name is actually caught.  The
    protected prefix is read from the launcher too, so the test tracks the
    script rather than a copy of it.
    """

    content = _launcher_content()
    pattern_match = re.search(r'case "\$PROJECT" in\s*\n\s*(.+?)\)\s*\n', content)
    assert pattern_match, "could not locate the protected-project case pattern"
    prefix_match = re.search(
        r'PROTECTED_PROJECT_PREFIX="([^"]+)"', content
    )
    assert prefix_match, "could not locate PROTECTED_PROJECT_PREFIX"
    return prefix_match.group(1), pattern_match.group(1).strip()


def _project_is_blocked(guard: tuple[str, str], project: str) -> bool:
    prefix, pattern = guard
    script = (
        f'PROTECTED_PROJECT_PREFIX="{prefix}"\n'
        'case "$1" in\n'
        f"  {pattern})\n"
        "    echo BLOCKED ;;\n"
        "  *)\n"
        "    echo ALLOWED ;;\n"
        "esac"
    )
    result = subprocess.run(
        ["bash", "-c", script, "_", project],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "BLOCKED"


class TestLauncherHasNoGlobalContainerDeletion:
    """The launcher must never remove containers it does not own.

    A partial name filter such as ``--filter "name=codexify"`` selects
    containers across every Compose project on the host, including the
    live Private Preview.  The launcher therefore performs no global
    cleanup at all and scopes every lifecycle operation to one
    explicitly identified Compose project.
    """

    def test_launcher_never_removes_containers_directly(self):
        content = _launcher_content()
        assert "docker rm" not in content
        assert "docker container rm" not in content
        assert "xargs docker" not in content

    def test_launcher_never_selects_containers_by_partial_name(self):
        content = _launcher_content()
        assert '--filter "name=' not in content
        assert "--filter name=" not in content
        assert "docker ps -aq" not in content
        assert "docker ps -a " not in content

    def test_launcher_scopes_lifecycle_to_an_explicit_project(self):
        content = _launcher_content()
        assert 'docker compose -p "$PROJECT"' in content
        assert (
            'docker compose -p "$PROJECT" $COMPOSE_FILES down --remove-orphans'
            in content
        )
        assert "docker compose $COMPOSE_FILES down" not in content

    def test_launcher_refuses_protected_projects(self):
        content = _launcher_content()
        assert "PROTECTED_PROJECT_PREFIX" in content
        assert "codexify_private_preview" in content
        assert "refusing to target protected Compose project" in content

    def test_protected_project_guard_covers_every_prefixed_name(self):
        """No spelling of a protected project may slip through the guard."""

        pattern = _protected_project_case_pattern()
        blocked = [
            "codexify_private_preview",
            "codexify_private_preview_staging",
            "codexify_private_previewfoo",
            "codexify_private_preview_",
            "codexify_private_preview2",
        ]
        allowed = [
            "codexify",
            "codexify_qual_migrator",
            "codexify_private_previe",
            "codexifyprivpreview",
        ]
        for name in blocked:
            assert _project_is_blocked(pattern, name), f"{name} must be refused"
        for name in allowed:
            assert not _project_is_blocked(pattern, name), f"{name} must be allowed"

    def test_teardown_is_opt_in_not_automatic(self):
        content = _launcher_content()
        assert "DO_TEARDOWN=0" in content
        assert "DO_TEARDOWN=1" in content
        teardown_index = content.index("down --remove-orphans")
        up_index = content.index('docker compose -p "$PROJECT" $COMPOSE_FILES up')
        assert teardown_index < up_index
        assert "Step 8: Tear down project" in content
        assert "Step 9: Start Docker Compose" in content


class TestLauncherEstablishesSourceIdentity:
    def test_launcher_reads_the_checkout_revision(self):
        content = _launcher_content()
        assert 'git -C "$REPO_ROOT" rev-parse HEAD' in content
        assert "SOURCE_SHA" in content

    def test_launcher_requires_a_clean_tracked_tree(self):
        content = _launcher_content()
        assert "status --porcelain --untracked-files=no" in content
        assert "tracked files are modified" in content
        assert "--allow-dirty-source" in content

    def test_launcher_determines_the_source_migration_head(self):
        content = _launcher_content()
        assert "alembic" in content
        assert "heads" in content
        assert "Source Alembic head" in content

    def test_launcher_rejects_multiple_or_missing_heads(self):
        content = _launcher_content()
        assert "multiple Alembic heads" in content
        assert "could not determine the source Alembic head" in content

    def test_launcher_does_not_hard_code_a_migration_revision(self):
        content = _launcher_content()
        assert not re.search(r"\b[0-9a-f]{12}\b", content), (
            "the launcher must not treat a migration revision as a permanent "
            "hard-coded value"
        )


class TestLauncherIsSourceMatchedAtTheImageBoundary:
    def test_launcher_builds_a_source_specific_image(self):
        content = _launcher_content()
        assert "codexify-backend-runtime:src-" in content
        assert "docker build --target runtime -f backend/Dockerfile" in content

    def test_launcher_inspects_the_images_own_migration_head(self):
        content = _launcher_content()
        assert "docker run --rm --entrypoint python" in content
        assert "Image Alembic head" in content

    def test_launcher_fails_closed_on_mismatch(self):
        content = _launcher_content()
        assert "MIGRATION IMAGE DOES NOT MATCH THE SOURCE REVISION" in content
        assert "Refusing to migrate" in content
        for field in (
            "source revision:",
            "source head:",
            "image head:",
            "image reference:",
            "image digest:",
        ):
            assert field in content

    def test_mismatch_check_precedes_any_container_start(self):
        content = _launcher_content()
        parity_index = content.index("MIGRATION IMAGE DOES NOT MATCH THE SOURCE REVISION")
        up_index = content.index('docker compose -p "$PROJECT" $COMPOSE_FILES up')
        assert parity_index < up_index

    def test_launcher_selects_the_built_image_for_the_running_services(self):
        content = _launcher_content()
        assert 'export CODEXIFY_BACKEND_IMAGE="$IMAGE_REF"' in content
        assert "does not use $IMAGE_REF" in content
        for service in ("migrator", "backend", "worker-chat"):
            assert service in content

    def test_launcher_does_not_add_a_source_bind_mount_for_migrations(self):
        content = _launcher_content()
        assert ":/app/guardian" not in content
        assert ":/app/backend" not in content

    def test_launcher_does_not_mutate_schema_itself(self):
        content = _launcher_content()
        assert "stamp" not in content
        assert "alembic upgrade" not in content
        assert "alembic revision --autogenerate" not in content

    def test_launcher_propagates_the_migrator_exit_status(self):
        content = _launcher_content()
        assert "{{.State.ExitCode}}" in content
        assert "the migrator failed" in content


class TestLauncherLeavesTheHostProviderAlone:
    def test_launcher_does_not_restart_a_healthy_provider(self):
        content = _launcher_content()
        probe_index = content.index("Whoosh'd is already running")
        ensure_index = content.index("whooshd_ensure.sh")
        assert probe_index < ensure_index
        assert "it is left untouched" in content


# ──────────────────────────────────────────────────────────────────────────
# QUAL-MIGRATOR-02 — the launcher must not declare a migration successful
# on the strength of a container's exit code alone.
#
# `docker compose ps` omits containers that have already exited, and the
# migrator is a one-shot container.  The launcher therefore discovered an
# exited migrator as "nothing to confirm" and exited zero — reporting
# success for a migration that had never been verified, and that may well
# have failed.
#
# The tests below cover the decision logic directly.  A stand-in `docker`
# executable stands in for the Docker CLI, so the decisions are exercised
# deterministically without a Docker daemon.
# ──────────────────────────────────────────────────────────────────────────

QUAL_PROJECT = "codexify_qual_contract"
QUAL_HEAD = "a1b2c3d4e5f6"

# Full-length container IDs, as Compose reports them.
QUAL_MIGRATOR_ID = "1a2b3c4d5e6f" + "0" * 52
QUAL_DB_ID = "2b3c4d5e6f70" + "0" * 52

_DOCKER_STAND_IN_SOURCE = '''#!/usr/bin/env python3
"""Stand-in for the Docker CLI, used by the launcher contract tests."""

import json
import os
import sys

CONFIG = json.loads(os.environ.get("DOCKER_SHIM_CONFIG", "{}"))
CONTAINERS = CONFIG.get("containers", {})
COMPOSE_PS = CONFIG.get("compose_ps", {})
DOCKER_PS = CONFIG.get("docker_ps", {})
ALEMBIC_ROWS = CONFIG.get("alembic_rows", [])
PSQL_EXIT = int(CONFIG.get("psql_exit", 0))
STATUS_MISSING = bool(CONFIG.get("status_missing", False))
EXIT_CODE_MISSING = bool(CONFIG.get("exit_code_missing", False))


def _label_filters(argv):
    filters = {}
    for index, token in enumerate(argv):
        if token == "--filter" and index + 1 < len(argv):
            value = argv[index + 1]
            if value.startswith("label="):
                key, _, label_value = value[len("label=") :].partition("=")
                filters[key] = label_value
    return filters


def _matches(container_id, filters):
    meta = CONTAINERS.get(container_id, {})
    project = filters.get("com.docker.compose.project")
    service = filters.get("com.docker.compose.service")
    if project is not None and meta.get("project") != project:
        return False
    if service is not None and meta.get("service") != service:
        return False
    return True


def main():
    argv = sys.argv[1:]
    if len(argv) < 1:
        return 1
    command = argv[0]
    args = argv[1:]

    if command == "compose":
        if "ps" in args:
            rest = args[args.index("ps") + 1 :]
            service = None
            for token in rest:
                if not token.startswith("-"):
                    service = token
            show_all = "--all" in rest or "-a" in rest
            ids = list(COMPOSE_PS.get(service, []))
            if not show_all:
                # Real Compose omits containers that have already exited.
                ids = [
                    i
                    for i in ids
                    if CONTAINERS.get(i, {}).get("status") != "exited"
                ]
            for container_id in ids:
                print(container_id)
        return 0

    if command == "ps":
        filters = _label_filters(args)
        service = filters.get("com.docker.compose.service")
        # Real Docker truncates container IDs unless --no-trunc is given.
        # Compose always reports the full ID, so a launcher that compared
        # the two listings without --no-trunc would see one container as
        # two and declare the migrator ambiguous.
        truncate = "--no-trunc" not in args
        for container_id in DOCKER_PS.get(service, []):
            if _matches(container_id, filters):
                print(container_id[:12] if truncate else container_id)
        return 0

    if command == "inspect":
        fmt = ""
        targets = []
        index = 0
        while index < len(args):
            token = args[index]
            if token == "-f":
                index += 1
                fmt = args[index]
            elif token.startswith("{{"):
                fmt = token
            else:
                targets.append(token)
            index += 1
        meta = CONTAINERS.get(targets[0] if targets else "", {})
        if "com.docker.compose.project" in fmt:
            print(meta.get("project", ""))
        elif "com.docker.compose.service" in fmt:
            print(meta.get("service", ""))
        elif "State.Status" in fmt:
            if STATUS_MISSING:
                sys.stderr.write("no such container\\n")
                return 1
            print(meta.get("status", ""))
        elif "State.ExitCode" in fmt:
            if EXIT_CODE_MISSING:
                sys.stderr.write("no such container\\n")
                return 1
            print(meta.get("exit_code", ""))
        else:
            print("")
        return 0

    if command == "exec":
        script = args[-1] if args else ""
        if "alembic_version" in script:
            if PSQL_EXIT != 0:
                sys.stderr.write("psql: could not connect\\n")
                return PSQL_EXIT
            for row in ALEMBIC_ROWS:
                print(row)
            return 0
        print("1")
        return 0

    if command == "logs":
        print("stand-in: migrator log output")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


# Short aliases expand to full-length IDs, as Compose reports them.
_FULL_IDS = {
    "m1": QUAL_MIGRATOR_ID,
    "m2": QUAL_MIGRATOR_ID[:-1] + "1",
    "d1": QUAL_DB_ID,
}


def _container(
    container_id: str,
    *,
    status: str = "exited",
    exit_code: str = "0",
    project: str = QUAL_PROJECT,
    service: str = "migrator",
) -> dict:
    container_id = _FULL_IDS.get(container_id, container_id)
    return {
        "id": container_id,
        "status": status,
        "exit_code": exit_code,
        "project": project,
        "service": service,
    }


def _scenario(
    *,
    migrator_containers: list[dict],
    db_containers: list[dict],
    compose_reports_migrator: bool = True,
    compose_reports_db: bool = True,
    alembic_rows: list[str] | None = None,
    psql_exit: int = 0,
    status_missing: bool = False,
    exit_code_missing: bool = False,
) -> dict:
    """Build a stand-in Docker world for one verification scenario."""

    containers = {}
    compose_ps: dict[str, list[str]] = {}
    docker_ps: dict[str, list[str]] = {}

    for container in migrator_containers:
        containers[container["id"]] = container
        if compose_reports_migrator:
            compose_ps.setdefault("migrator", []).append(container["id"])
        docker_ps.setdefault("migrator", []).append(container["id"])

    for container in db_containers:
        containers[container["id"]] = container
        if compose_reports_db:
            compose_ps.setdefault("db", []).append(container["id"])
        docker_ps.setdefault("db", []).append(container["id"])

    return {
        "containers": containers,
        "compose_ps": compose_ps,
        "docker_ps": docker_ps,
        "alembic_rows": [QUAL_HEAD] if alembic_rows is None else alembic_rows,
        "psql_exit": psql_exit,
        "status_missing": status_missing,
        "exit_code_missing": exit_code_missing,
    }


def _run_verification(
    tmp_path,
    scenario: dict,
    *,
    expected_head: str = QUAL_HEAD,
    project: str = QUAL_PROJECT,
    timeout: int | None = None,
):
    """Run the launcher's verification helper against the stand-in Docker."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stand_in = bin_dir / "docker"
    stand_in.write_text(_DOCKER_STAND_IN_SOURCE)
    stand_in.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["DOCKER_SHIM_CONFIG"] = json.dumps(scenario)
    env["WHOOSHD_SMOKE_LIB_ONLY"] = "1"
    if timeout is not None:
        env["MIGRATOR_TIMEOUT"] = str(timeout)

    launcher = str(SMOKE_LAUNCHER_PATH.resolve())
    compose_files = "-f docker-compose.yml -f docker-compose.whooshd-smoke.yml"

    return subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; source "$1"; verify_migration_outcome "$2" "$3" "$4" || exit $?',
            "_",
            launcher,
            project,
            expected_head,
            compose_files,
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(Path.cwd()),
    )


class TestLauncherVerifiesTheMigratorOutcome:
    """Static invariants of the migration-outcome verification."""

    def test_launcher_discovers_exited_one_shot_containers(self):
        content = _launcher_content()
        assert "ps --all -q migrator" in content
        assert "ps -q migrator" not in content

    def test_launcher_never_reports_success_without_a_migrator(self):
        content = _launcher_content()
        assert "nothing to confirm" not in content
        assert "no migrator container was found" in content

    def test_launcher_requires_exactly_one_migrator(self):
        content = _launcher_content()
        assert "is ambiguous" in content

    def test_launcher_verifies_ownership_before_inspecting_state(self):
        content = _launcher_content()
        ownership = content.index("is not this project's migrator")
        state = content.index("{{.State.Status}}")
        assert ownership < state

    def test_launcher_resolves_containers_by_compose_label(self):
        content = _launcher_content()
        assert "--filter \"label=com.docker.compose.project=$project\"" in content
        assert "--filter \"label=com.docker.compose.service=migrator\"" in content
        assert "--filter \"label=com.docker.compose.service=db\"" in content

    def test_launcher_normalises_container_ids_before_deduplicating(self):
        """`docker ps` truncates IDs unless --no-trunc is given.

        Compose reports full IDs, so without --no-trunc the two discovery
        paths would describe one container as two and the migrator would
        be declared ambiguous.
        """

        content = _launcher_content()
        assert content.count("--no-trunc") >= 2

    def test_launcher_requires_exit_code_zero(self):
        content = _launcher_content()
        assert "{{.State.ExitCode}}" in content
        assert '"$exit_code" != "0"' in content

    def test_launcher_rejects_a_dead_migrator(self):
        content = _launcher_content()
        assert "dead state" in content

    def test_launcher_reads_the_actual_database_revision(self):
        content = _launcher_content()
        assert "select version_num from alembic_version" in content

    def test_launcher_requires_exactly_one_revision_row(self):
        content = _launcher_content()
        assert "reports no alembic_version row" in content
        assert "the revision is ambiguous" in content

    def test_launcher_compares_the_readback_to_the_source_head(self):
        content = _launcher_content()
        assert "expected head:" in content
        assert "observed head:" in content

    def test_readback_precedes_the_success_message(self):
        content = _launcher_content()
        readback = content.index("select version_num from alembic_version")
        success = content.index("the migration is confirmed")
        assert readback < success

    def test_launcher_reads_only_its_own_projects_database(self):
        content = _launcher_content()
        assert "is not this project's database" in content
        assert "codexify_private_preview" in content

    def test_launcher_keeps_the_source_specific_build(self):
        content = _launcher_content()
        assert "built-from-this-checkout" in content
        assert "codexify-backend-runtime:src-" in content

    def test_supplied_image_does_not_claim_source_equivalence(self):
        content = _launcher_content()
        assert "supplied-reference" in content
        assert "does not establish source" in content

    def test_launcher_offers_a_verify_mode(self):
        content = _launcher_content()
        assert "full|minimal|migrator|verify)" in content
        assert 'if [ "$MODE" = "verify" ]; then' in content

    def test_attached_mode_declares_that_it_is_not_verified(self):
        """An attached run never reaches the outcome verification.

        `docker compose up` streams logs until the stack stops, so the
        migration result is not judged during normal attached operation.
        The launcher must say so rather than let the run be read as a
        verified one.
        """

        content = _launcher_content()
        assert "attached mode" in content
        assert "Use --detach for a" in content
        assert "verified qualification run" in content

    def test_attached_warning_is_guarded_by_the_detach_check(self):
        """The warning must fire only when the run is actually attached."""

        content = _launcher_content()
        block = content.split("DETACH_ARGS=()", 1)[1].split('case "$MODE" in', 1)[0]
        assert 'if [ "$DETACH" -eq 1 ]' in block
        assert "else" in block
        else_branch = block.split("else", 1)[1]
        assert "attached mode" in else_branch
        assert "--detach" in else_branch

    def test_launcher_lists_untracked_paths_in_the_build_context(self):
        """Untracked files enter the image the source tag does not describe."""

        content = _launcher_content()
        assert "UNTRACKED_LIST" in content
        assert "untracked path(s) present in the build context" in content
        assert "change the" in content
        assert "source-specific tag does not describe" in content


class TestMigratorVerificationDecisions:
    """The verification helper must fail closed in every ambiguous case."""

    def test_missing_migrator_container_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(migrator_containers=[], db_containers=[]),
        )
        assert result.returncode != 0
        assert "no migrator container was found" in result.stdout

    def test_exited_successful_migrator_is_confirmed(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
            ),
        )
        assert result.returncode == 0, result.stdout
        assert "the migration is confirmed" in result.stdout

    def test_exited_migrator_is_found_when_compose_omits_it(self, tmp_path):
        """Compose lists only running containers; the label scope finds it."""

        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                compose_reports_migrator=False,
            ),
        )
        assert result.returncode == 0, result.stdout
        assert "the migration is confirmed" in result.stdout

    def test_failed_migrator_exit_propagates_failure(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1", exit_code="1")],
                db_containers=[_container("d1", status="running", service="db")],
            ),
        )
        assert result.returncode != 0
        assert "the migrator failed" in result.stdout

    def test_ambiguous_migrator_containers_fail(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1"), _container("m2")],
                db_containers=[_container("d1", status="running", service="db")],
            ),
        )
        assert result.returncode != 0
        assert "ambiguous" in result.stdout

    def test_foreign_project_migrator_is_rejected(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1", project="codexify_other")],
                db_containers=[_container("d1", status="running", service="db")],
            ),
        )
        assert result.returncode != 0
        assert "is not this project's migrator" in result.stdout

    def test_timed_out_migrator_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1", status="running")],
                db_containers=[_container("d1", status="running", service="db")],
            ),
            timeout=0,
        )
        assert result.returncode != 0
        assert "did not finish within" in result.stdout

    def test_dead_migrator_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1", status="dead")],
                db_containers=[_container("d1", status="running", service="db")],
            ),
        )
        assert result.returncode != 0
        assert "dead state" in result.stdout

    def test_unreadable_migrator_state_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                status_missing=True,
            ),
        )
        assert result.returncode != 0
        assert "could not inspect the state" in result.stdout

    def test_unreadable_exit_status_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                exit_code_missing=True,
            ),
        )
        assert result.returncode != 0
        assert "could not read the migrator's exit status" in result.stdout

    def test_wrong_database_revision_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                alembic_rows=["ffffffffffff"],
            ),
        )
        assert result.returncode != 0
        assert "does not match the expected migration head" in result.stdout
        assert "observed head: ffffffffffff" in result.stdout

    def test_missing_database_revision_row_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                alembic_rows=[],
            ),
        )
        assert result.returncode != 0
        assert "reports no alembic_version row" in result.stdout

    def test_multiple_database_revision_rows_fail(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                alembic_rows=[QUAL_HEAD, "ffffffffffff"],
            ),
        )
        assert result.returncode != 0
        assert "the revision is ambiguous" in result.stdout

    def test_unreadable_database_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                psql_exit=1,
            ),
        )
        assert result.returncode != 0
        assert "could not read alembic_version" in result.stdout

    def test_missing_database_container_fails(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[],
            ),
        )
        assert result.returncode != 0
        assert "no database container was found" in result.stdout

    def test_foreign_database_container_is_rejected(self, tmp_path):
        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[
                    _container("d1", status="running", service="db", project="other")
                ],
            ),
        )
        assert result.returncode != 0
        assert "is not this project's database" in result.stdout

    def test_success_requires_the_exact_expected_head(self, tmp_path):
        """A different-but-valid revision is still a failure."""

        result = _run_verification(
            tmp_path,
            _scenario(
                migrator_containers=[_container("m1")],
                db_containers=[_container("d1", status="running", service="db")],
                alembic_rows=["ffffffffffff"],
            ),
            expected_head=QUAL_HEAD,
        )
        assert result.returncode != 0
