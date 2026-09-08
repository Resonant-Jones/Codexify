"""Deterministic tests for the compatibility-named Pi model delegation skill.

The tests use fake ``pi`` executables and temporary directories. They never make
network calls or invoke a real model.
"""

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
WRAPPER = SCRIPTS_DIR / "pi_deepseek_delegate.sh"
INSTALLER = SCRIPTS_DIR / "install.sh"

CONTROL_ENV = {
    "PI_DELEGATION_PROVIDER",
    "PI_DELEGATION_MODEL",
    "PI_DELEGATION_THINKING",
    "PI_DELEGATION_TIMEOUT",
    "PI_DEEPSEEK_PROVIDER",
    "PI_DEEPSEEK_MODEL",
    "PI_DEEPSEEK_THINKING",
    "PI_DEEPSEEK_TIMEOUT",
    "CODEX_PI_DELEGATION_ACK",
    "CODEX_PI_WRITE_DELEGATION",
    "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK",
    "CODEX_DEEPSEEK_WRITE_DELEGATION",
    "DEEPSEEK_API_KEY",
    "FAKE_PI_WORKER_LOG",
    "FAKE_PI_WORKER_STDERR",
    "PI_DEEPSEEK_SKILL_TARGET",
}

MODEL_LIST = """provider  model              context  max-out  thinking  images
alpha     alpha-reasoner      128K     16K      yes       no
beta      beta-vision         256K     32K      no        yes
deepseek  deepseek-legacy     1M       64K      yes       no
"""


def make_fake_pi(
    tmp_path: Path,
    model_list_output: str = MODEL_LIST,
    exit_code: int = 0,
    worker_output: str = "FAKE_WORKER_RESULT",
    worker_stderr: str = "",
    empty_output: bool = False,
) -> Path:
    """Create a fake ``pi`` that distinguishes catalog from worker calls."""
    pi_path = tmp_path / "bin" / "pi"
    pi_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""#!/usr/bin/env bash
if [[ "$*" == *"--list-models"* ]]; then
    cat <<'EOF'
{model_list_output}
EOF
    exit 0
fi
if [[ -n "${{FAKE_PI_WORKER_LOG:-}}" ]]; then
    printf '%s\\n' "$*" >> "$FAKE_PI_WORKER_LOG"
fi
if [[ -n "${{FAKE_PI_WORKER_STDERR:-}}" ]]; then
    printf '%s\\n' "$FAKE_PI_WORKER_STDERR" >&2
fi
if [[ "{int(empty_output)}" == "1" ]]; then
    exit {exit_code}
fi
cat <<'EOF'
{worker_output}
EOF
exit {exit_code}
"""
    pi_path.write_text(script)
    pi_path.chmod(0o755)
    return pi_path


def make_auth_json(tmp_path: Path) -> Path:
    """Create a secret-bearing auth file to prove the wrapper ignores it."""
    auth_dir = tmp_path / ".pi" / "agent"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_path = auth_dir / "auth.json"
    auth_path.write_text(json.dumps({"deepseek": {"key": "SECRET_SENTINEL"}}))
    return auth_path


def base_env(overrides: dict | None = None) -> dict:
    """Avoid ambient selection/consent variables changing deterministic tests."""
    env = {key: value for key, value in os.environ.items() if key not in CONTROL_ENV}
    env.update({key: str(value) for key, value in (overrides or {}).items()})
    return env


def run_wrapper(
    args: list[str],
    env: dict | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    cmd = ["bash", str(WRAPPER), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else str(SKILL_DIR),
        env=base_env(env),
    )


def run_installer(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    cmd = ["bash", str(INSTALLER), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(SKILL_DIR),
        env=base_env(env),
    )


def worker_log(tmp_path: Path) -> Path:
    return tmp_path / "worker.log"


def env_for_pi(pi: Path, tmp_path: Path, **extra: str) -> dict:
    values = {
        "PATH": f"{pi.parent}:{os.environ['PATH']}",
        "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        "FAKE_PI_WORKER_LOG": str(worker_log(tmp_path)),
    }
    values.update(extra)
    return values


def assert_worker_not_called(tmp_path: Path) -> None:
    log = worker_log(tmp_path)
    assert not log.exists() or not log.read_text()


def tools_from_dry_run(stdout: str) -> str:
    command_line = next((line for line in stdout.splitlines() if "--tools" in line), "")
    match = re.search(r"--tools\s+(\S+)", command_line)
    assert match, f"Could not find --tools in output: {stdout[:800]}"
    return match.group(1)


def metadata_path(stdout: str) -> Path:
    line = next(line for line in stdout.splitlines() if line.startswith("delegation_metadata="))
    return Path(line.split("=", 1)[1])


class TestCatalogAndSelection:
    def test_catalog_surfaces_multiple_providers_without_inference(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        auth_path = make_auth_json(tmp_path)
        result = run_wrapper(["--catalog"], env=env_for_pi(pi, tmp_path), cwd=tmp_path)

        assert result.returncode == 0
        assert "available_model_entries=3" in result.stdout
        assert "alpha     alpha-reasoner" in result.stdout
        assert "beta      beta-vision" in result.stdout
        assert "deepseek  deepseek-legacy" in result.stdout
        assert "SECRET_SENTINEL" not in result.stdout
        assert auth_path.read_text() not in result.stdout
        assert_worker_not_called(tmp_path)

    def test_catalog_json_is_machine_readable_and_table_only(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--catalog", "--json"],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["available_model_entries"] == 3
        assert "beta      beta-vision" in payload["listing"]
        assert_worker_not_called(tmp_path)

    def test_explicit_provider_model_pair_is_used(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "provider=beta" in result.stdout
        assert "model=beta-vision" in result.stdout
        assert "selection_source=explicit-task" in result.stdout
        assert_worker_not_called(tmp_path)

    def test_explicit_pair_wins_over_generic_defaults(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check", "--provider", "alpha", "--model", "alpha-reasoner"],
            env=env_for_pi(
                pi,
                tmp_path,
                PI_DELEGATION_PROVIDER="beta",
                PI_DELEGATION_MODEL="beta-vision",
            ),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "provider=alpha" in result.stdout
        assert "model=alpha-reasoner" in result.stdout
        assert "selection_source=explicit-task" in result.stdout

    def test_generic_environment_selection_and_settings(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check"],
            env=env_for_pi(
                pi,
                tmp_path,
                PI_DELEGATION_PROVIDER="beta",
                PI_DELEGATION_MODEL="beta-vision",
                PI_DELEGATION_THINKING="low",
                PI_DELEGATION_TIMEOUT="77",
            ),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "provider=beta" in result.stdout
        assert "model=beta-vision" in result.stdout
        assert "thinking=low" in result.stdout
        assert "timeout_seconds=77" in result.stdout
        assert "selection_source=generic-environment" in result.stdout

    def test_legacy_deepseek_model_is_bounded_compatibility(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check"],
            env=env_for_pi(
                pi,
                tmp_path,
                PI_DEEPSEEK_PROVIDER="deepseek",
                PI_DEEPSEEK_MODEL="deepseek-legacy",
                PI_DEEPSEEK_THINKING="minimal",
                PI_DEEPSEEK_TIMEOUT="42",
            ),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "provider=deepseek" in result.stdout
        assert "model=deepseek-legacy" in result.stdout
        assert "thinking=minimal" in result.stdout
        assert "timeout_seconds=42" in result.stdout
        assert "selection_source=legacy-deepseek" in result.stdout

    @pytest.mark.parametrize(
        ("args", "env", "needle"),
        [
            (["--check"], {}, "no provider/model selected"),
            (["--check", "--provider", "beta"], {}, "requires both --provider and --model"),
            (["--check", "--model", "beta-vision"], {}, "requires both --provider and --model"),
            (["--check"], {"PI_DELEGATION_PROVIDER": "beta"}, "configured together"),
            (["--check"], {"PI_DELEGATION_MODEL": "beta-vision"}, "configured together"),
        ],
    )
    def test_missing_or_partial_selection_fails_closed(self, tmp_path, args, env, needle):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(args, env=env_for_pi(pi, tmp_path, **env), cwd=tmp_path)

        assert result.returncode != 0
        assert needle in result.stderr
        assert_worker_not_called(tmp_path)

    def test_legacy_provider_only_fails_closed(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check"],
            env=env_for_pi(pi, tmp_path, PI_DEEPSEEK_PROVIDER="deepseek"),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "missing PI_DEEPSEEK_MODEL" in result.stderr

    def test_no_implicit_router_or_first_model_fallback_remains(self):
        source = WRAPPER.read_text()
        assert "deepseek-v4-pro" not in source
        assert "deepseek-v4-flash" not in source
        assert "preferred_order" not in source
        assert "first listed" not in source.lower()

    def test_nonexistent_pair_fails_before_worker_inference(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check", "--provider", "beta", "--model", "not-registered"],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "not available in Pi's current catalog" in result.stderr
        assert_worker_not_called(tmp_path)


class TestConsentAndExecution:
    def test_check_requires_no_consent_for_non_deepseek_pair(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--check", "--provider", "alpha", "--model", "alpha-reasoner"],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode == 0

    def test_dry_run_requires_no_consent_and_does_not_create_artifacts(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--provider",
                "beta",
                "--model",
                "beta-vision",
                "--task",
                "bounded task",
                "--dry-run",
            ],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "provider=beta" in result.stdout
        assert "model=beta-vision" in result.stdout
        assert "--provider beta --model beta-vision" in result.stdout
        assert not (tmp_path / ".codex").exists()
        assert_worker_not_called(tmp_path)

    def test_real_delegation_requires_generic_ack(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--task", "bounded task", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "CODEX_PI_DELEGATION_ACK=1" in result.stderr
        assert_worker_not_called(tmp_path)

    def test_generic_ack_authorizes_non_deepseek_execution(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--task", "bounded task", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(pi, tmp_path, CODEX_PI_DELEGATION_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "selected_provider=beta" in result.stdout
        assert "selected_model=beta-vision" in result.stdout
        assert worker_log(tmp_path).exists()

    def test_legacy_deepseek_ack_cannot_authorize_other_provider(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--task", "bounded task", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(pi, tmp_path, CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "only authorizes a DeepSeek selection" in result.stderr
        assert_worker_not_called(tmp_path)

    def test_legacy_deepseek_ack_remains_compatible_for_deepseek(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            ["--task", "bounded task"],
            env=env_for_pi(
                pi,
                tmp_path,
                PI_DEEPSEEK_MODEL="deepseek-legacy",
                CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK="1",
            ),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "selected_provider=deepseek" in result.stdout
        assert "selected_model=deepseek-legacy" in result.stdout

    def test_implementation_requires_generic_write_ack(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "implementation",
                "--task",
                "bounded task",
                "--provider",
                "beta",
                "--model",
                "beta-vision",
            ],
            env=env_for_pi(pi, tmp_path, CODEX_PI_DELEGATION_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "CODEX_PI_WRITE_DELEGATION=1" in result.stderr
        assert_worker_not_called(tmp_path)

    def test_implementation_generic_write_ack_allows_worker(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "implementation",
                "--task",
                "bounded task",
                "--provider",
                "beta",
                "--model",
                "beta-vision",
            ],
            env=env_for_pi(
                pi,
                tmp_path,
                CODEX_PI_DELEGATION_ACK="1",
                CODEX_PI_WRITE_DELEGATION="1",
            ),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "selected_provider=beta" in result.stdout
        assert worker_log(tmp_path).exists()

    @pytest.mark.parametrize(
        ("mode", "must_have", "must_not_have"),
        [
            ("analysis", ["read"], ["bash", "write", "edit"]),
            ("review", ["read"], ["bash", "write", "edit"]),
            ("test", ["read", "bash"], ["write", "edit"]),
            ("implementation", ["read", "write", "edit", "bash"], []),
        ],
    )
    def test_mode_tool_restrictions_are_unchanged(self, tmp_path, mode, must_have, must_not_have):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                mode,
                "--task",
                "bounded task",
                "--provider",
                "beta",
                "--model",
                "beta-vision",
                "--dry-run",
            ],
            env=env_for_pi(pi, tmp_path),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        tools = tools_from_dry_run(result.stdout)
        for expected in must_have:
            assert expected in tools
        for forbidden in must_not_have:
            assert forbidden not in tools

    def test_metadata_records_actual_selection_and_generic_artifact_path(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "bounded task",
                "--provider",
                "beta",
                "--model",
                "beta-vision",
                "--thinking",
                "low",
                "--selection-rationale",
                "Small context and image-capable metadata are relevant to this task.",
            ],
            env=env_for_pi(pi, tmp_path, CODEX_PI_DELEGATION_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        meta = metadata_path(result.stdout)
        content = meta.read_text()
        assert "provider=beta" in content
        assert "model=beta-vision" in content
        assert "provider_model=beta/beta-vision" in content
        assert "thinking=low" in content
        assert "mode=analysis" in content
        assert "selection_source=explicit-task" in content
        assert "selection_rationale=Small context and image-capable metadata are relevant to this task." in content
        assert f"artifact_dir={tmp_path}/.codex/delegations/pi" in content
        assert "artifact_path=" in content
        assert "result_file=" in content

    def test_worker_failure_is_preserved(self, tmp_path):
        pi = make_fake_pi(tmp_path, exit_code=7)
        result = run_wrapper(
            ["--task", "bounded task", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(pi, tmp_path, CODEX_PI_DELEGATION_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode == 7
        assert "failed with exit code 7" in result.stderr

    def test_empty_worker_result_is_rejected(self, tmp_path):
        pi = make_fake_pi(tmp_path, empty_output=True)
        result = run_wrapper(
            ["--task", "bounded task", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(pi, tmp_path, CODEX_PI_DELEGATION_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "empty result" in result.stderr.lower()

    def test_stderr_path_is_reported_without_copying_credentials(self, tmp_path):
        pi = make_fake_pi(tmp_path, worker_stderr="diagnostic output")
        result = run_wrapper(
            ["--task", "bounded task", "--provider", "beta", "--model", "beta-vision"],
            env=env_for_pi(
                pi,
                tmp_path,
                CODEX_PI_DELEGATION_ACK="1",
                FAKE_PI_WORKER_STDERR="diagnostic output",
            ),
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "delegation_stderr=" in result.stdout
        assert "SECRET_SENTINEL" not in result.stdout

    def test_sensitive_context_file_is_rejected(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        sensitive = tmp_path / ".env"
        sensitive.write_text("SECRET_SENTINEL=value")
        result = run_wrapper(
            [
                "--task",
                "bounded task",
                "--provider",
                "beta",
                "--model",
                "beta-vision",
                "--context-file",
                str(sensitive),
            ],
            env=env_for_pi(pi, tmp_path, CODEX_PI_DELEGATION_ACK="1"),
            cwd=tmp_path,
        )

        assert result.returncode != 0
        assert "sensitive context file" in result.stderr
        assert_worker_not_called(tmp_path)

    def test_catalog_and_check_do_not_read_or_print_secret_state(self, tmp_path):
        pi = make_fake_pi(tmp_path)
        auth_path = make_auth_json(tmp_path)
        env = env_for_pi(
            pi,
            tmp_path,
            DEEPSEEK_API_KEY="SECRET_ENV_SENTINEL",
            PI_CODING_AGENT_DIR=str(auth_path.parent),
        )

        for args in (
            ["--catalog"],
            ["--check", "--provider", "beta", "--model", "beta-vision"],
        ):
            result = run_wrapper(args, env=env, cwd=tmp_path)
            assert result.returncode == 0
            assert "SECRET_SENTINEL" not in result.stdout
            assert "SECRET_ENV_SENTINEL" not in result.stdout
            assert "auth.json" not in result.stdout
            assert_worker_not_called(tmp_path)

        source = WRAPPER.read_text()
        assert "AUTH_CONFIGURED" not in source
        assert "DEEPSEEK_API_KEY" not in source


class TestInstaller:
    def test_dry_run_makes_no_changes(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        result = run_installer(["--install", "--dry-run", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "Would install" in result.stdout
        assert not target.exists()

    def test_first_install_succeeds(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        result = run_installer(["--install", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "installed_current" in result.stdout
        assert target.is_dir()
        assert (target / "SKILL.md").is_file()
        assert (target / "scripts" / "pi_deepseek_delegate.sh").is_file()

    def test_second_install_is_idempotent(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        result = run_installer(["--install", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "installed_current" in result.stdout

    def test_check_detects_current(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        result = run_installer(["--check", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "installed_current" in result.stdout

    def test_check_detects_drift(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        (target / "SKILL.md").write_text("modified content")
        result = run_installer(["--check", "--target", str(target), "--dev"])
        assert result.returncode == 4
        assert "installed_drifted" in result.stdout

    def test_check_detects_not_installed(self, tmp_path):
        target = tmp_path / "nonexistent" / "skill"
        result = run_installer(["--check", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "not_installed" in result.stdout

    def test_install_excludes_tests(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        assert not (target / "tests").exists()
        assert not (target / "test_pi_deepseek_delegate.py").exists()

    def test_uninstall_removes_owned_skill_files(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        result = run_installer(["--uninstall", "--target", str(target)])
        assert result.returncode == 0
        assert "uninstalled" in result.stdout
        assert not (target / "SKILL.md").exists()
        assert not (target / "scripts" / "pi_deepseek_delegate.sh").exists()

    def test_install_preserves_executable(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        wrapper = target / "scripts" / "pi_deepseek_delegate.sh"
        assert wrapper.is_file()
        assert wrapper.stat().st_mode & stat.S_IXUSR

    def test_install_does_not_affect_sibling(self, tmp_path):
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        sibling = tmp_path / "skills" / "other-skill"
        sibling.mkdir(parents=True)
        sibling_file = sibling / "SKILL.md"
        sibling_file.write_text("original")
        run_installer(["--install", "--target", str(target), "--dev"])
        assert sibling_file.read_text() == "original"

    def test_rejects_dirty_source_without_dev_override(self, tmp_path):
        result = run_installer(["--check", "--target", str(tmp_path / "out")])
        if result.returncode != 0:
            assert "dirty" in result.stdout.lower()

    def test_rejects_relative_target(self, tmp_path):
        result = run_installer(["--install", "--target", "relative/path", "--dev"])
        assert result.returncode != 0
        assert "absolute" in result.stdout.lower() or "absolute" in result.stderr.lower()

    def test_rejects_path_traversal_target(self, tmp_path):
        result = run_installer(["--install", "--target", "/tmp/../etc/skill", "--dev"])
        assert result.returncode != 0
        assert ".." in result.stdout.lower() or ".." in result.stderr.lower()


class TestSecrets:
    def test_no_secret_patterns_in_skill_source(self):
        secret_pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
        for root, dirs, files in os.walk(SKILL_DIR):
            dirs[:] = [directory for directory in dirs if directory not in {".git", "__pycache__", ".pytest_cache", "node_modules"}]
            for filename in files:
                if filename.endswith(".pyc"):
                    continue
                path = Path(root) / filename
                try:
                    content = path.read_text()
                except Exception:
                    continue
                assert not secret_pattern.search(content), f"Secret pattern found in {path}"

    def test_no_hardcoded_api_key_value_in_skill_source(self):
        key_value_pattern = re.compile(r"api[_-]?key[\s\"'=:]+sk-", re.IGNORECASE)
        for root, dirs, files in os.walk(SKILL_DIR):
            dirs[:] = [directory for directory in dirs if directory not in {".git", "__pycache__", ".pytest_cache", "node_modules"}]
            for filename in files:
                if filename.endswith((".pyc", ".py")):
                    continue
                path = Path(root) / filename
                try:
                    content = path.read_text()
                except Exception:
                    continue
                assert not key_value_pattern.search(content), f"API key value in {path}"
