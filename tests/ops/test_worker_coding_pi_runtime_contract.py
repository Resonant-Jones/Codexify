from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"
DOCKERFILE = ROOT / "backend/Dockerfile"
RUNBOOK = ROOT / "docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md"
PROFILE = ROOT / "codex_runner/src/profile.py"
RUNNER_CLI = ROOT / "codex_runner/src/runner_cli.py"
RUNTIME_PACKAGE = ROOT / "codex_runner/pi-runtime/package.json"
RUNTIME_LOCK = ROOT / "codex_runner/pi-runtime/package-lock.json"
VENDORED_PACKAGE = ROOT / "codex_runner/vendor/pi-coding-agent/package.json"
CANONICAL_ANTHROPIC_MODEL = "claude-sonnet-4-6"
OBSOLETE_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


def _load_runner_cli_for_test():
    """Load the source-only Campaign Runner modules without importing stdlib ``profile``."""
    profile_spec = importlib.util.spec_from_file_location(
        "codexify_campaign_profile_under_test", PROFILE
    )
    assert profile_spec and profile_spec.loader
    profile_module = importlib.util.module_from_spec(profile_spec)
    sys.modules[profile_spec.name] = profile_module

    previous_profile = sys.modules.get("profile")
    runner_name = "codexify_runner_cli_under_test"
    try:
        profile_spec.loader.exec_module(profile_module)
        runner_spec = importlib.util.spec_from_file_location(runner_name, RUNNER_CLI)
        assert runner_spec and runner_spec.loader
        runner_module = importlib.util.module_from_spec(runner_spec)
        sys.modules["profile"] = profile_module
        sys.modules[runner_name] = runner_module
        runner_spec.loader.exec_module(runner_module)
        return profile_module, runner_module
    finally:
        sys.modules.pop(profile_spec.name, None)
        sys.modules.pop(runner_name, None)
        if previous_profile is None:
            sys.modules.pop("profile", None)
        else:
            sys.modules["profile"] = previous_profile


def _run_guardian_authorized_readiness(
    model_id: str,
) -> subprocess.CompletedProcess[str]:
    """Run the real source-vendored wrapper with an isolated, empty Pi home."""
    home = Path(tempfile.mkdtemp(prefix="codexify-pi-anthropic-readiness-"))
    pi_agent_dir = home / "pi-agent"
    pi_agent_dir.mkdir()
    try:
        result = subprocess.run(
            [
                "node",
                str(ROOT / "codex_runner/src/agent-wrapper.js"),
                "guardian-authorized-readiness",
            ],
            cwd=str(home),
            env={
                "HOME": str(home),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "PI_CODING_AGENT_DIR": str(pi_agent_dir),
                "PI_OFFLINE": "1",
                "PI_PROVIDER": "anthropic",
                "PI_MODEL": model_id,
                "PI_GUARDIAN_AUTHORIZED": "1",
                "PI_GUARDIAN_HARNESS_ID": "pi-coding-agent",
                "PI_GUARDIAN_HARNESS_VERSION": "0.82.1",
                "PI_DISABLE_TOOLS": "1",
            },
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        shutil.rmtree(home, ignore_errors=True)
    return result


def _service_block(text: str, service: str) -> str:
    marker = f"  {service}:\n"
    start = text.index(marker) + len(marker)
    lines: list[str] = []
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("  ") and not line.startswith("    "):
            break
        lines.append(line)
    return "".join(lines)


def test_worker_coding_uses_dedicated_image_and_narrow_pi_auth_mount() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    worker = _service_block(text, "worker-coding")

    assert "image: codexify-worker-coding-runtime:latest" in worker
    assert "target: worker-coding-runtime" in worker
    assert "codexify_pi_auth:/home/codexify/.pi" in worker
    assert "codexify_cli_home:/home/codexify" not in worker
    assert "PI_PROVIDER:" in worker
    assert "PI_MODEL:" in worker
    assert "ANTHROPIC_API_KEY:" in worker
    assert "check_worker_coding_readiness.py" in worker


def test_worker_image_installs_exact_declared_pi_runtime_without_credentials() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    runtime_package = json.loads(RUNTIME_PACKAGE.read_text(encoding="utf-8"))
    runtime_lock = json.loads(RUNTIME_LOCK.read_text(encoding="utf-8"))
    vendored_package = json.loads(VENDORED_PACKAGE.read_text(encoding="utf-8"))

    declared_version = runtime_package["dependencies"]["@earendil-works/pi-coding-agent"]
    assert declared_version == vendored_package["version"] == "0.82.1"
    assert (
        runtime_lock["packages"][""]["dependencies"]["@earendil-works/pi-coding-agent"]
        == "0.82.1"
    )
    assert (
        runtime_lock["packages"][""]["dependencies"]["@earendil-works/pi-ai"] == "0.82.1"
    )
    assert "FROM node:22.19.0-bookworm-slim AS pi-sdk-runtime" in dockerfile
    assert "npm ci --omit=dev --ignore-scripts --no-audit --no-fund" in dockerfile
    assert "FROM runtime AS worker-coding-runtime" in dockerfile
    assert "ANTHROPIC_API_KEY" not in dockerfile
    assert "auth.json" not in dockerfile


def test_active_runtime_loader_targets_maintained_pi_ai() -> None:
    """The wrapper loader must not import the deprecated Pi AI namespace."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    assert "@mariozechner/pi-ai" not in loader


def test_active_runtime_loader_delegates_model_resolution_to_modelruntime() -> None:
    """Model resolution must be delegated to the maintained Pi 0.82.1 ModelRuntime
    surface, not to a deprecated compat layer."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    assert "@earendil-works/pi-ai/dist/compat.js" not in loader
    assert "getModel: piAiCompat.getModel" not in loader
    assert "getProviders: piAiCompat.getProviders" not in loader
    assert "OPENAI_CODEX_MODELS" not in loader


def test_active_runtime_loader_imports_maintained_coding_agent() -> None:
    """The wrapper loader must read coding-agent from the maintained package
    metadata; the deprecated upstream namespace must not appear in active
    loader paths."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    assert "@earendil-works/pi-coding-agent" in loader
    assert "@mariozechner" not in loader


def test_active_runtime_loader_uses_canonical_model_runtime() -> None:
    """The 0.82.1 wrapper must use the unified async model/auth facade."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    # Maintained Pi 0.82.1 ModelRuntime factory, with network refresh disabled.
    assert "await codingAgent.ModelRuntime.create({" in loader
    assert "allowModelNetwork: false" in loader
    assert "modelRuntime.getModel.bind(modelRuntime)" in loader
    assert "modelRuntime.getProviders.bind(modelRuntime)" in loader
    assert "modelRuntime," in loader
    # No stale Pi 0.72-era auth/model-registry APIs.
    assert "piAi.AuthStorage" not in loader
    assert "AuthStorage.create()" not in loader
    assert "authStorage.hasAuth(" not in loader
    assert "ModelRegistry.create(" not in loader
    assert "OPENAI_CODEX_MODELS" not in loader


def test_active_coding_worker_defaults_are_coherent() -> None:
    """The six active default surfaces must share the reconciled model."""
    from guardian.agents.adapters.pi_codex_runner import (
        DEFAULT_PI_MODEL as ADAPTER_DEFAULT_PI_MODEL,
    )
    from guardian.agents.pi_readiness import (
        DEFAULT_PI_MODEL,
        DEFAULT_PI_PROVIDER,
    )

    profile_module, runner_module = _load_runner_cli_for_test()
    assert profile_module.DEFAULT_MODEL == CANONICAL_ANTHROPIC_MODEL
    assert runner_module.DEFAULT_MODEL == profile_module.DEFAULT_MODEL
    assert profile_module.Profile(name="default").model == CANONICAL_ANTHROPIC_MODEL
    assert (
        profile_module.Profile.from_dict("default", {}).model
        == CANONICAL_ANTHROPIC_MODEL
    )
    for name in ("default", "fast", "review"):
        assert (
            profile_module.DEFAULT_PROFILES[name]["model"]
            == CANONICAL_ANTHROPIC_MODEL
        )
    assert profile_module.DEFAULT_PROFILES["thorough"]["model"] == "claude-opus-4-5"

    assert DEFAULT_PI_PROVIDER == "anthropic"
    assert DEFAULT_PI_MODEL == CANONICAL_ANTHROPIC_MODEL
    assert ADAPTER_DEFAULT_PI_MODEL == DEFAULT_PI_MODEL

    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")
    assert 'const DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6";' in loader
    assert "model: process.env.PI_MODEL || DEFAULT_ANTHROPIC_MODEL" in loader
    for alias in ('"sonnet":', '"sonnet4":', '"sonnet-4":'):
        assert f"{alias} DEFAULT_ANTHROPIC_MODEL" in loader
    assert OBSOLETE_ANTHROPIC_MODEL not in loader

    compose = COMPOSE.read_text(encoding="utf-8")
    assert 'PI_PROVIDER: "${PI_PROVIDER:-anthropic}"' in compose
    assert f'PI_MODEL: "${{PI_MODEL:-{CANONICAL_ANTHROPIC_MODEL}}}"' in compose


def test_runner_cli_uses_canonical_default_for_agent_and_command_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Behaviorally cover run_pi_agent, audit, and run default fallbacks."""
    _profile_module, runner_module = _load_runner_cli_for_test()

    subprocess_calls: list[dict[str, object]] = []

    def fake_subprocess_run(*args, **kwargs):
        subprocess_calls.append(kwargs)
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_subprocess_run)
    direct_result = runner_module.run_pi_agent(
        "readiness", "probe", {"cwd": str(tmp_path)}
    )
    assert direct_result.success is True
    assert subprocess_calls[-1]["env"]["PI_MODEL"] == CANONICAL_ANTHROPIC_MODEL

    class EmptyProfileManager:
        active_profile = "default"

        def load(self):
            return self

        def get(self, _name):
            return None

    command_options: list[dict[str, object]] = []

    def fake_agent(_mode: str, _prompt: str, options: dict[str, object]):
        command_options.append(options)
        return runner_module.CommandResult(success=True)

    monkeypatch.setattr(runner_module, "ProfileManager", EmptyProfileManager)
    monkeypatch.setattr(runner_module, "run_pi_agent", fake_agent)

    assert runner_module.cmd_audit(["default probe"], {"cwd": str(ROOT)}).success
    assert runner_module.cmd_run(["default probe"], {"cwd": str(ROOT)}).success
    assert [options["model"] for options in command_options] == [
        CANONICAL_ANTHROPIC_MODEL,
        CANONICAL_ANTHROPIC_MODEL,
    ]


def test_runbook_uses_compose_owned_environment_and_canonical_readiness() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")

    assert "source .env" not in runbook
    assert "docker compose config --quiet" in runbook
    assert "docker compose build worker-coding" in runbook
    assert "docker compose up -d worker-coding" in runbook
    assert "check_worker_coding_readiness.py --format human" in runbook
    assert "LOCAL_PROVIDER_DISPLAY_NAME" in runbook
    assert "apostrophe" in runbook.lower()


def test_canonical_pi_source_vendor_runtime_bundle_is_complete() -> None:
    """The source-vendored Pi runtime must ship its executable payload so the
    wrapper's source-relative fallback can load it without external SDK
    overrides.

    A metadata-only vendor tree (e.g. only ``package.json``, docs, and
    examples) lets CI pass without actually providing the runtime the
    wrapper imports.  This regression contract fails closed when those
    runtime artifacts are absent.
    """
    coding_agent_dist_index = (
        ROOT / "codex_runner/vendor/pi-coding-agent/dist/index.js"
    )
    nested_pi_ai_dist_index = (
        ROOT
        / "codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js"
    )
    nested_pi_ai_openai_codex_models = (
        ROOT
        / "codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js"
    )

    assert coding_agent_dist_index.is_file(), (
        "Canonical source-vendored coding-agent dist/index.js is missing; "
        "the wrapper's source-relative default cannot load the Pi runtime."
    )
    assert nested_pi_ai_dist_index.is_file(), (
        "Canonical source-vendored nested @earendil-works/pi-ai/dist/index.js "
        "is missing; the wrapper's source-relative default cannot load the "
        "maintained Pi AI runtime."
    )
    assert nested_pi_ai_openai_codex_models.is_file(), (
        "Canonical source-vendored nested openai-codex.models.js is missing; "
        "openai-codex provider/model catalog cannot be resolved from the "
        "source-vendor fallback."
    )

    vendored_coding_agent = json.loads(VENDORED_PACKAGE.read_text(encoding="utf-8"))
    assert vendored_coding_agent["name"] == "@earendil-works/pi-coding-agent"
    assert vendored_coding_agent["version"] == "0.82.1"

    nested_pi_ai_pkg = json.loads(
        (ROOT / "codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/package.json").read_text(
            encoding="utf-8"
        )
    )
    assert nested_pi_ai_pkg["name"] == "@earendil-works/pi-ai"
    assert nested_pi_ai_pkg["version"] == "0.82.1"


def test_source_relative_wrapper_loads_pi_runtime_with_full_locked_closure() -> None:
    """Source-relative empty-HOME wrapper smoke proves the source-vendor
    fallback contains the full locked runtime dependency closure.

    This non-inference regression invokes the wrapper subprocess with no
    package-root overrides and an intentionally empty HOME.  The expected
    bounded result is ``oauth_auth_unavailable`` at ``oauth_readiness``,
    with exact runtime identity attestation.  The result proves the wrapper
    loaded the maintained Pi runtime through ``runtime_load``,
    ``model_resolution``, and ``identity_verification`` using only the
    source-vendored runtime closure.

    If any transitive package disappears from the source-vendor closure and
    the wrapper can no longer load, this test fails CI.
    """
    wrapper_path = ROOT / "codex_runner/src/agent-wrapper.js"
    if not wrapper_path.is_file():
        pytest.skip("wrapper not present in this checkout")

    # Build an empty disposable HOME that contains no Pi credentials.
    empty_home = Path(tempfile.mkdtemp(prefix="codexify-pi-empty-home-"))
    try:
        # Force a clean subprocess environment without operator credential
        # access.  No PATH inheritance from parent shell.
        env = {
            "HOME": str(empty_home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PI_PROVIDER": "openai-codex",
            "PI_MODEL": "gpt-5.6-sol",
            "PI_GUARDIAN_AUTHORIZED": "1",
            "PI_GUARDIAN_HARNESS_ID": "pi-coding-agent",
            "PI_GUARDIAN_HARNESS_VERSION": "0.82.1",
            # PI_DISABLE_TOOLS=1 by default; the wrapper reads it.
            "PI_DISABLE_TOOLS": "1",
        }
        result = subprocess.run(
            ["node", str(wrapper_path), "guardian-authorized-readiness"],
            cwd=str(empty_home),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        shutil.rmtree(empty_home, ignore_errors=True)

    assert result.returncode == 0, (
        f"wrapper subprocess failed with exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )

    payload = json.loads(result.stdout)

    assert payload["failure_class"] == "oauth_auth_unavailable", (
        f"expected failure_class=oauth_auth_unavailable, got {payload.get('failure_class')!r}; "
        f"payload={payload}"
    )
    assert payload["failure_stage"] == "oauth_readiness", (
        f"expected failure_stage=oauth_readiness, got {payload.get('failure_stage')!r}"
    )
    assert payload["runtime_identity_established"] is True, (
        f"runtime identity not established; payload={payload}"
    )

    identity = payload["actual_runtime_identity"]
    assert identity["actual_provider_id"] == "openai-codex"
    assert identity["actual_model_id"] == "gpt-5.6-sol"
    assert identity["actual_harness_id"] == "pi-coding-agent"
    assert identity["actual_harness_version"] == "0.82.1"

    assert payload["session_initialized"] is False
    assert payload["provider_request_started"] is False


def test_reconciled_anthropic_model_supports_canonical_session_provider_free() -> None:
    """Prove the replacement model accepts the wrapper's session posture."""
    home = Path(tempfile.mkdtemp(prefix="codexify-pi-anthropic-session-"))
    pi_agent_dir = home / "pi-agent"
    pi_agent_dir.mkdir()
    script = r'''
import { ModelRuntime } from "./codex_runner/vendor/pi-coding-agent/dist/core/model-runtime.js";
import { createAgentSession } from "./codex_runner/vendor/pi-coding-agent/dist/core/sdk.js";
import { SessionManager } from "./codex_runner/vendor/pi-coding-agent/dist/core/session-manager.js";

const runtime = await ModelRuntime.create({ allowModelNetwork: false });
const model = runtime.getModel("anthropic", "claude-sonnet-4-6");
if (!model) throw new Error("model_unresolved");
const { session } = await createAgentSession({
    cwd: process.cwd(),
    model,
    modelRuntime: runtime,
    tools: ["read", "bash", "edit", "write"],
    thinkingLevel: "medium",
    sessionManager: SessionManager.inMemory(),
});
const activeToolNames = session.getActiveToolNames();
const thinkingLevels = session.getAvailableThinkingLevels();
if (JSON.stringify(activeToolNames) !== JSON.stringify(["read", "bash", "edit", "write"])) {
    throw new Error(`unexpected_tools:${JSON.stringify(activeToolNames)}`);
}
if (!thinkingLevels.includes("medium") || session.thinkingLevel !== "medium") {
    throw new Error(`unexpected_thinking:${JSON.stringify({ thinkingLevels, effective: session.thinkingLevel })}`);
}
console.log(JSON.stringify({
    provider: model.provider,
    id: model.id,
    api: model.api,
    activeToolNames,
    effectiveThinkingLevel: session.thinkingLevel,
}));
'''
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=str(ROOT),
            env={
                "HOME": str(home),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "PI_CODING_AGENT_DIR": str(pi_agent_dir),
                "PI_OFFLINE": "1",
            },
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        shutil.rmtree(home, ignore_errors=True)

    assert result.returncode == 0, (
        f"provider-free Anthropic session probe failed: exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {
        "provider": "anthropic",
        "id": CANONICAL_ANTHROPIC_MODEL,
        "api": "anthropic-messages",
        "activeToolNames": ["read", "bash", "edit", "write"],
        "effectiveThinkingLevel": "medium",
    }


def test_anthropic_replacement_resolves_through_authorized_readiness_provider_free(
) -> None:
    """Exact Guardian-authorized replacement resolution must precede auth use."""
    result = _run_guardian_authorized_readiness(CANONICAL_ANTHROPIC_MODEL)

    assert result.returncode == 0, (
        f"authorized replacement readiness failed: exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["failure_class"] == "oauth_auth_unavailable"
    assert payload["failure_stage"] == "oauth_readiness"
    assert payload["runtime_identity_established"] is True
    assert payload["actual_runtime_identity"] == {
        "actual_provider_id": "anthropic",
        "actual_model_id": CANONICAL_ANTHROPIC_MODEL,
        "actual_harness_id": "pi-coding-agent",
        "actual_harness_version": "0.82.1",
    }
    assert payload["session_initialized"] is False
    assert payload["provider_request_started"] is False


def test_obsolete_anthropic_identity_fails_closed_without_silent_remap() -> None:
    """The obsolete exact ID must remain an unresolved identity, not an alias."""
    result = _run_guardian_authorized_readiness(OBSOLETE_ANTHROPIC_MODEL)

    assert result.returncode == 0, (
        f"obsolete identity readiness probe failed: exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["failure_class"] == "model_unresolved"
    assert payload["failure_stage"] == "model_resolution"
    assert payload["runtime_identity_established"] is False
    assert payload["actual_runtime_identity"] is None
    assert payload["session_initialized"] is False
    assert payload["provider_request_started"] is False


def test_synthetic_oauth_credential_readiness_returns_oauth_available() -> None:
    """Decisive regression proving Codexify uses the maintained Pi 0.82.1
    credential API end-to-end.

    A disposable HOME is created containing only a synthetic
    0.82.1-compatible ``auth.json`` for ``openai-codex``.  No network
    request is made.  No operator credential is accessed.

    The wrapper must observe:

    * ``status = "ok"``
    * ``oauth_available = true``
    * ``runtime_identity_established = true``
    * exact identity
      ``openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1``
    * ``session_initialized = false``
    * ``provider_request_started = false``
    """
    wrapper_path = ROOT / "codex_runner/src/agent-wrapper.js"
    if not wrapper_path.is_file():
        pytest.skip("wrapper not present in this checkout")

    home = Path(tempfile.mkdtemp(prefix="codexify-pi-synthetic-oauth-"))
    try:
        auth_dir = home / ".pi" / "agent"
        auth_dir.mkdir(parents=True, mode=0o700)
        # Synthetic, fixture-only credentials.  These values must NOT be
        # derived from any real operator credential.  ``checkAuth`` reads
        # ``credential.type === "oauth"`` and returns the structural
        # descriptor without contacting a remote provider.
        auth_payload = {
            "openai-codex": {
                "type": "oauth",
                "access": "synthetic-access-token-fixture-not-real",
                "refresh": "synthetic-refresh-token-fixture-not-real",
                "expires": 9999999999999,
                "accountId": "acct-syn-fixture",
            }
        }
        (auth_dir / "auth.json").write_text(
            json.dumps(auth_payload, indent=2), encoding="utf-8"
        )
        # Ensure the file is only readable by the current user.
        try:
            (auth_dir / "auth.json").chmod(0o600)
        except OSError:
            pass

        env = {
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PI_PROVIDER": "openai-codex",
            "PI_MODEL": "gpt-5.6-sol",
            "PI_GUARDIAN_AUTHORIZED": "1",
            "PI_GUARDIAN_HARNESS_ID": "pi-coding-agent",
            "PI_GUARDIAN_HARNESS_VERSION": "0.82.1",
            "PI_DISABLE_TOOLS": "1",
        }
        result = subprocess.run(
            ["node", str(wrapper_path), "guardian-authorized-readiness"],
            cwd=str(home),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        shutil.rmtree(home, ignore_errors=True)

    assert result.returncode == 0, (
        f"wrapper subprocess failed with exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "ok", (
        f"expected status=ok, got {payload.get('status')!r}; payload={payload}"
    )
    assert payload["oauth_available"] is True, (
        f"expected oauth_available=true, got {payload.get('oauth_available')!r}; "
        f"payload={payload}"
    )
    assert payload["runtime_identity_established"] is True, (
        f"runtime identity not established; payload={payload}"
    )

    identity = payload["actual_runtime_identity"]
    assert identity["actual_provider_id"] == "openai-codex"
    assert identity["actual_model_id"] == "gpt-5.6-sol"
    assert identity["actual_harness_id"] == "pi-coding-agent"
    assert identity["actual_harness_version"] == "0.82.1"

    assert payload["session_initialized"] is False
    assert payload["provider_request_started"] is False


def test_missing_runtime_api_classifies_as_wrapper_protocol_failure() -> None:
    """A broken maintained-SDK API shape must not collapse to
    ``oauth_auth_unavailable``.  It must report a non-credential
    runtime/wrapper failure so operator truth is preserved.

    The wrapper is ESM and its ``loadPiSdk`` is internal; this regression
    uses a deterministic source-grep contract that fails closed if the
    fail-closed guard for the maintained Pi 0.82.1 runtime API is absent
    from the active wrapper source.  Together with the runtime smoke and
    stale-API regression, this contract proves the wrapper refuses to
    collapse a missing-runtime error into an OAuth availability signal.
    """
    wrapper_path = ROOT / "codex_runner/src/agent-wrapper.js"
    if not wrapper_path.is_file():
        pytest.skip("wrapper not present in this checkout")

    loader = wrapper_path.read_text(encoding="utf-8")

    # Fail-closed guard for ModelRuntime.create.
    assert (
        'if (typeof codingAgent.ModelRuntime?.create !== "function")' in loader
    ), "wrapper missing ModelRuntime.create fail-closed guard"
    assert (
        "Pi coding-agent package is missing the ModelRuntime.create factory"
        in loader
    ), "wrapper missing ModelRuntime.create fail-closed message"

    # Fail-closed guard for createAgentSession.
    assert (
        'if (typeof codingAgent.createAgentSession !== "function")' in loader
    ), "wrapper missing createAgentSession fail-closed guard"

    # The fail-closed path must throw, NOT return a degraded surface that
    # the readiness rail would silently reclassify as oauth_auth_unavailable.
    assert "throw new Error(" in loader, (
        "wrapper must throw on missing maintained runtime API; "
        "the readiness rail depends on a thrown error to classify it as "
        "runtime_load / wrapper_unavailable, not oauth_auth_unavailable."
    )


def test_stale_api_regression_source_omits_pi_72_auth_surfaces() -> None:
    """The active wrapper source must not reference Pi 0.72-era auth surfaces
    that are no longer the maintained Pi 0.82.1 contract."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    forbidden_substrings = (
        "piAi.AuthStorage",
        "AuthStorage.create(",
        "authStorage.hasAuth(",
        "ModelRegistry.create(",
        "@earendil-works/pi-ai/dist/compat.js",
    )
    for forbidden in forbidden_substrings:
        assert forbidden not in loader, (
            f"active wrapper source still references forbidden stale API {forbidden!r}; "
            "wrapper must use the maintained Pi 0.82.1 ModelRuntime surface."
        )


def test_session_can_be_initialized_without_prompt_via_modelruntime() -> None:
    """Non-inference regression proving the maintained Pi 0.82.1
    ``createAgentSession`` call accepts the canonical ``modelRuntime``
    instance.

    The wrapper is ESM and does not export its internals, so this
    regression exercises the wrapper's session-construction call path
    through an isolated subprocess invocation with a synthetic OAuth
    credential.  A disposable ``auth.json`` bearing synthetic OAuth fields
    is placed under a disposable HOME; the wrapper must reach
    ``runtime_load`` through ``model_resolution`` and ``identity_verification``
    against the synthetic credential without initializing a real session
    or issuing a provider request.

    The readiness invocation itself does not call ``createAgentSession``
    — the synthetic credential proves the maintained ``ModelRuntime``
    auth surface works end-to-end.  Together with the
    ``test_active_runtime_loader_uses_canonical_model_runtime`` source-grep
    regression (which asserts the wrapper passes ``modelRuntime`` into
    ``createAgentSession({...modelRuntime, ...})``), this test establishes
    that the maintained contract is wired correctly.

    No operator credential is accessed.  No network request is made.
    No model prompt is issued.
    """
    wrapper_path = ROOT / "codex_runner/src/agent-wrapper.js"
    if not wrapper_path.is_file():
        pytest.skip("wrapper not present in this checkout")

    home = Path(tempfile.mkdtemp(prefix="codexify-pi-session-init-"))
    try:
        auth_dir = home / ".pi" / "agent"
        auth_dir.mkdir(parents=True, mode=0o700)
        (auth_dir / "auth.json").write_text(
            json.dumps({
                "openai-codex": {
                    "type": "oauth",
                    "access": "synthetic",
                    "refresh": "synthetic",
                    "expires": 9999999999999,
                    "accountId": "acct-syn-fixture",
                }
            }, indent=2),
            encoding="utf-8",
        )
        try:
            (auth_dir / "auth.json").chmod(0o600)
        except OSError:
            pass

        env = {
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PI_PROVIDER": "openai-codex",
            "PI_MODEL": "gpt-5.6-sol",
            "PI_GUARDIAN_AUTHORIZED": "1",
            "PI_GUARDIAN_HARNESS_ID": "pi-coding-agent",
            "PI_GUARDIAN_HARNESS_VERSION": "0.82.1",
            "PI_DISABLE_TOOLS": "1",
        }
        result = subprocess.run(
            ["node", str(wrapper_path), "guardian-authorized-readiness"],
            cwd=str(home),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        shutil.rmtree(home, ignore_errors=True)

    assert result.returncode == 0, (
        f"wrapper subprocess failed with exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )

    payload = json.loads(result.stdout)
    # The wrapper reaches ModelRuntime-based auth under a synthetic OAuth
    # credential; readiness itself is non-inference (session_initialized=false).
    assert payload["status"] == "ok", (
        f"expected status=ok under synthetic OAuth, got payload={payload}"
    )
    assert payload["oauth_available"] is True
    assert payload["runtime_identity_established"] is True
    assert payload["session_initialized"] is False
    assert payload["provider_request_started"] is False
    identity = payload["actual_runtime_identity"]
    assert identity["actual_provider_id"] == "openai-codex"
    assert identity["actual_model_id"] == "gpt-5.6-sol"
    assert identity["actual_harness_id"] == "pi-coding-agent"
    assert identity["actual_harness_version"] == "0.82.1"
    # No session.prompt() call was issued during this readiness probe.


# --- Pi 0.82.1 tool-name compatibility regression ---
#
# Proves the maintained source-vendored Pi 0.82.1 SDK treats
# `createAgentSession({ tools })` as a collection of tool-NAME strings.
# Uses disposable HOME / auth.json — no prompt, no network, no operator
# credentials.  This regression must fail if a future upgrade reintroduces
# object-array `tools` and produces an empty effective tool set.

def test_maintained_pi_0821_treats_tools_as_name_strings() -> None:
    """Reproduce the Pi 0.82.1 name-only effective-tool-set contract."""
    from pathlib import Path

    home = Path(tempfile.mkdtemp(prefix="codexify-pi-0821-tool-name-regression-"))
    driver_path = None
    try:
        auth_dir = home / ".pi" / "agent"
        auth_dir.mkdir(parents=True, mode=0o700)
        (auth_dir / "auth.json").write_text(
            json.dumps(
                {
                    "openai-codex": {
                        "type": "oauth",
                        "expires": 9999999999999,
                    }
                }
            ),
            encoding="utf-8",
        )

        driver_text = """
const path = require("path");
const fs = require("fs");
const home = process.argv[2];
const target = process.argv[3];

process.env.HOME = home;

(async () => {
    const vendorRoot = path.resolve(
        process.argv[4],
        "codex_runner/vendor/pi-coding-agent",
    );
    const codingAgent = await import(
        require("url").pathToFileURL(
            path.join(vendorRoot, "dist/index.js"),
        ).href
    );

    const modelRuntime = await codingAgent.ModelRuntime.create({
        allowModelNetwork: false,
    });
    const model = modelRuntime.getModel("openai-codex", "gpt-5.6-sol");
    if (!model) {
        console.log(JSON.stringify({ error: "model_not_resolved" }));
        process.exit(1);
    }

    const { session: writable } = await codingAgent.createAgentSession({
        cwd: target,
        model,
        modelRuntime,
        tools: ["read", "bash", "edit", "write"],
        sessionManager: codingAgent.SessionManager.inMemory(target),
    });
    const writableActive = writable.getActiveToolNames();

    const { session: disabled } = await codingAgent.createAgentSession({
        cwd: target,
        model,
        modelRuntime,
        tools: [],
        sessionManager: codingAgent.SessionManager.inMemory(target),
    });
    const disabledActive = disabled.getActiveToolNames();

    console.log(JSON.stringify({
        writable_active_tool_names: writableActive,
        disabled_active_tool_names: disabledActive,
    }));
})();
"""
        driver_path = Path(tempfile.mkstemp(suffix=".cjs")[1])
        driver_path.write_text(driver_text, encoding="utf-8")

        target = Path(tempfile.mkdtemp(prefix="codexify-pi-0821-tool-regression-target-"))
        result = subprocess.run(
            ["node", str(driver_path), str(home), str(target), str(ROOT)],
            cwd=str(ROOT),
            env={
                **os.environ,
                "HOME": str(home),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
            },
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        shutil.rmtree(home, ignore_errors=True)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if driver_path is not None:
            try:
                driver_path.unlink()
            except OSError:
                pass

    assert result.returncode == 0, (
        f"Pi 0.82.1 tool-name SDK probe failed: exit {result.returncode}; "
        f"stderr={result.stderr[:500]!r}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload.get("writable_active_tool_names") == [
        "read", "bash", "edit", "write",
    ], (
        f"Pi 0.82.1 must report writable tool-name session as "
        f"['read','bash','edit','write']; got {payload.get('writable_active_tool_names')!r}"
    )
    assert payload.get("disabled_active_tool_names") == [], (
        f"Pi 0.82.1 must report empty effective tool set when tools=[]; "
        f"got {payload.get('disabled_active_tool_names')!r}"
    )


def test_active_runtime_passes_tool_name_strings_not_agenttool_objects() -> None:
    """Wrapper source must pass tool-NAME strings into createAgentSession.

    This regression enforces the Pi 0.82.1 contract at the source level.
    The wrapper must not pass AgentTool objects (the legacy Pi 0.72
    assumption) into `createAgentSession({ tools })`.
    """
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")
    # Reject any ACTIVE use of `createCodingTools(OPTIONS.cwd)` whose return
    # value is passed (or could be passed) into createAgentSession.  An
    # explanatory comment referencing the legacy path is allowed.
    import re
    # Match an executable call to `createCodingTools(OPTIONS.cwd)` that is
    # not inside a comment line.
    non_comment_lines = [
        line for line in loader.splitlines()
        if not line.lstrip().startswith("//")
    ]
    non_comment_source = "\n".join(non_comment_lines)
    assert not re.search(r"createCodingTools\s*\(\s*OPTIONS\.cwd", non_comment_source), (
        "wrapper must not call createCodingTools(OPTIONS.cwd) and pass its "
        "return value into createAgentSession({ tools }) — that path returns "
        "AgentTool objects which Pi 0.82.1 silently rejects"
    )
    # The wrapper must pass an explicit canonical writable tool-name set.
    assert (
        '["read", "bash", "edit", "write"]' in loader
    ), "wrapper must pass the exact writable tool-name set ['read','bash','edit','write']"
    # The wrapper must read effective tool names from the session itself.
    assert "getActiveToolNames" in loader, (
        "wrapper must read the effective tool surface from the session, "
        "not from the configured value"
    )


# --- Pi 0.82.1 assistant-response telemetry source-level regressions
# (CE-L1 post-tool-repair observability).  These tests prove the wrapper
# source observes the maintained Pi `message_update` event vocabulary and
# the final `session.agent.state.messages` surface WITHOUT retaining
# text, reasoning, deltas, arguments, IDs, or provider payloads.


def test_active_runtime_observes_assistant_message_update_events() -> None:
    """The wrapper must subscribe to assistant `message_update` events to
    capture the maintained Pi 0.82.1 event vocabulary (`text_start`,
    `text_delta`, `toolcall_start`, etc.) without retaining deltas.
    """
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")
    # The wrapper must subscribe to session events.
    assert "session.subscribe" in loader, (
        "wrapper must use session.subscribe() to capture the maintained "
        "Pi 0.82.1 event vocabulary"
    )
    # The wrapper must listen to message_update events.
    assert "message_update" in loader, (
        "wrapper must observe message_update events to capture the "
        "maintained Pi 0.82.1 assistant message event vocabulary"
    )
    # The wrapper must record only event-type names; deltas must never
    # be appended to a telemetry accumulator.
    forbidden = [
        "assistantMessageEvent.textDelta",
        "assistantMessageEvent.thinkingDelta",
        "assistantMessageEvent.content",
        "assistantMessageEvent.toolCall.arguments",
        "assistantMessageEvent.toolCall.id",
    ]
    for marker in forbidden:
        assert marker not in loader, (
            f"wrapper must not retain delta/content/args/IDs; found {marker!r}"
        )


def test_active_runtime_reads_final_assistant_messages_block_kinds() -> None:
    """The wrapper must walk `session.agent.state.messages` to capture
    the maintained Pi 0.82.1 final assistant content-block kinds
    (`text`, `thinking`, `toolCall`) without retaining the blocks.
    """
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")
    helper = (ROOT / "codex_runner/src/assistant-telemetry.js").read_text(encoding="utf-8")
    # The wrapper must read final messages from the session state.
    assert "session.agent.state.messages" in loader or "agent.state.messages" in loader, (
        "wrapper must read final assistant messages from "
        "session.agent.state.messages to capture content-block kinds"
    )
    # The wrapper must record only content-block type names.
    assert "toolCall" in helper, (
        "helper must recognize the maintained Pi 0.82.1 'toolCall' "
        "content-block type"
    )
    # The wrapper/helper must NOT serialize full content blocks (no
    # arguments, IDs, or provider payloads).  Text accumulation for the
    # bounded `summary` is allowed (used by the wrapper for the
    # run summary field, not persisted to telemetry).
    forbidden_substrings = (
        "block.arguments",
        "block.id",
    )
    for source_name, source_text in (("agent-wrapper", loader), ("helper", helper)):
        for marker in forbidden_substrings:
            assert marker not in source_text, (
                f"{source_name} must not retain block args/IDs; "
                f"found {marker!r}"
            )


def test_active_runtime_tool_call_event_count_uses_maintained_vocabulary() -> None:
    """The wrapper must count only assistant message-update events whose
    Pi-native event type unambiguously denotes a tool-call lifecycle
    event, using the maintained Pi 0.82.1 vocabulary.
    """
    helper = (ROOT / "codex_runner/src/assistant-telemetry.js").read_text(encoding="utf-8")
    # The maintained Pi 0.82.1 tool-call event names appear in the
    # vendored types (AssistantMessageEvent union): "toolcall_start",
    # "toolcall_delta", "toolcall_end".  The helper must recognize
    # all three to count tool-call lifecycle events.
    for event_name in ("toolcall_start", "toolcall_delta", "toolcall_end"):
        assert event_name in helper, (
            f"helper must recognize maintained Pi 0.82.1 assistant "
            f"event {event_name!r}"
        )


def test_active_runtime_serializes_no_assistant_text_or_arguments() -> None:
    """The wrapper output must contain no assistant text, reasoning,
    deltas, tool arguments, tool IDs, or provider payloads.
    """
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")
    forbidden_substrings = (
        # Assistant text/reasoning prose must never appear in the wrapper
        # output JSON.
        "I cannot", "I will not", "as an AI",
        "as a language model", "thinking text",
        # Tool-arg/ID echoes that would leak schema structure.
        "tool_args", "toolCallArgs", "toolCallId",
        # Provider payload fragments.
        '"choices":', '"delta":', '"usage":',
        # Credentials.
        "api_key", "openai_api_key", "PI_API_KEY",
    )
    for marker in forbidden_substrings:
        assert marker not in loader, (
            f"wrapper must not serialize {marker!r}"
        )


def test_active_runtime_preserves_canonical_writable_tool_set() -> None:
    """The wrapper must preserve the canonical writable tool-name set
    exactly: `["read", "bash", "edit", "write"]`.
    """
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")
    assert '["read", "bash", "edit", "write"]' in loader, (
        "wrapper must preserve CONFIGURED_WRITABLE_TOOL_NAMES exactly"
    )
