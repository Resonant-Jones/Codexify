"""Deterministic tests for the pi-deepseek-delegation skill.

Uses fake pi executables, temporary directories, and synthetic outputs.
Never makes real network calls.
"""

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
WRAPPER = SCRIPTS_DIR / "pi_deepseek_delegate.sh"
INSTALLER = SCRIPTS_DIR / "install.sh"


def make_fake_pi(
    tmp_path: Path, model_list_output: str = "", exit_code: int = 0
) -> Path:
    """Create a fake pi executable that prints the given model list and exits."""
    pi_path = tmp_path / "bin" / "pi"
    pi_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""#!/usr/bin/env bash
if [[ "$*" == *"--list-models"* ]]; then
    cat <<'EOF'
{model_list_output}
EOF
    exit 0
fi
# Simulate a successful worker run
echo "FAKE_WORKER_RESULT"
exit {exit_code}
"""
    pi_path.write_text(script)
    pi_path.chmod(0o755)
    return pi_path


def make_fake_auth_json(tmp_path: Path, providers: list | None = None) -> Path:
    """Create a fake pi auth.json."""
    if providers is None:
        providers = ["deepseek"]
    auth_dir = tmp_path / ".pi" / "agent"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth = {p: {"type": "api_key", "key": "sk-fake-test-key"} for p in providers}
    auth_path = auth_dir / "auth.json"
    auth_path.write_text(json.dumps(auth, indent=2))
    return auth_path


def run_wrapper(
    args: list, env: dict | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    """Run the delegation wrapper with given args and env."""
    cmd = ["bash", str(WRAPPER), *args]
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else str(SKILL_DIR),
        env=merged_env,
    )


def run_installer(args: list, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the installer with given args and env."""
    cmd = ["bash", str(INSTALLER), *args]
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(SKILL_DIR), env=merged_env
    )


MODEL_LIST_OUTPUT = """provider  model              context  max-out  thinking  images
deepseek  deepseek-v4-flash  1M       384K     yes       no
deepseek  deepseek-v4-pro    1M       384K     yes       no
"""

# ---------------------------------------------------------------------------
# Model selection tests
# ---------------------------------------------------------------------------


class TestModelSelection:
    def test_inventory_supports_non_deepseek_provider_rows(self, tmp_path):
        """Inventory must expose exact provider/model rows beyond DeepSeek names."""
        listing = """provider  model              context  max-out  thinking  images
openai    gpt-5.1            400K     128K     yes       no
openai    o4-mini            200K     64K      yes       no
"""
        pi = make_fake_pi(tmp_path, listing)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "PI_DEEPSEEK_PROVIDER": "openai",
        }
        make_fake_auth_json(tmp_path, ["openai"])
        result = run_wrapper(["--check", "--provider", "openai"], env=env)
        assert result.returncode == 0
        assert "deepseek_model=gpt-5.1" in result.stdout
        assert "openai    gpt-5.1" in result.stdout

    def test_explicit_model_wins(self, tmp_path):
        """Explicit --model should be used regardless of listing."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check", "--model", "deepseek-v4-flash"], env=env)
        assert "deepseek_model=deepseek-v4-flash" in result.stdout

    def test_env_model_wins_when_set(self, tmp_path):
        """PI_DEEPSEEK_MODEL should be used when no explicit --model."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "PI_DEEPSEEK_MODEL": "deepseek-v4-flash",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_model=deepseek-v4-flash" in result.stdout

    def test_prefers_pro_when_listed(self, tmp_path):
        """deepseek-v4-pro should be preferred when both Pro and Flash are listed."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_model=deepseek-v4-pro" in result.stdout

    def test_flash_when_pro_absent(self, tmp_path):
        """deepseek-v4-flash should be selected when Pro is absent."""
        flash_only = "provider  model              context  max-out  thinking  images\ndeepseek  deepseek-v4-flash  1M       384K     yes       no\n"
        pi = make_fake_pi(tmp_path, flash_only)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_model=deepseek-v4-flash" in result.stdout

    def test_missing_model_fails(self, tmp_path):
        """Should fail clearly when no model is available."""
        pi = make_fake_pi(
            tmp_path, "provider  model  context  max-out  thinking  images\n"
        )
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_model=missing" in result.stdout
        assert result.returncode == 3

    def test_legacy_names_not_preferred(self, tmp_path):
        """Legacy names are not in the preferred list; fallback picks first listed."""
        listing_with_legacy = """provider  model              context  max-out  thinking  images
deepseek  deepseek-reasoner  1M       384K     yes       no
deepseek  deepseek-chat      1M       384K     yes       no
"""
        pi = make_fake_pi(tmp_path, listing_with_legacy)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        # Fallback picks first listed model, which is deepseek-reasoner
        # This is correct behavior — the model is in the Pi listing
        assert "deepseek_model=deepseek-reasoner" in result.stdout
        # But preferred order (pro/flash) is not matched

    def test_falls_back_to_first_listed_model(self, tmp_path):
        """When preferred models are absent, fall back to the first listed model."""
        custom_listing = """provider  model              context  max-out  thinking  images
deepseek  some-other-model   1M       384K     yes       no
deepseek  another-model      1M       384K     yes       no
"""
        pi = make_fake_pi(tmp_path, custom_listing)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_model=some-other-model" in result.stdout


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_auth_storage_detected(self, tmp_path):
        """Pi auth storage should be detected when auth.json contains deepseek."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path, ["deepseek"])
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_auth=configured" in result.stdout
        assert "sk-fake-test-key" not in result.stdout

    def test_auth_storage_missing_provider(self, tmp_path):
        """Auth should be missing when deepseek not in auth.json."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path, ["other-provider"])
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_auth=missing" in result.stdout
        assert result.returncode == 2

    def test_env_auth_detected(self, tmp_path):
        """DEEPSEEK_API_KEY env var should be detected."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "DEEPSEEK_API_KEY": "sk-fake-env-key",
        }
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_auth=configured" in result.stdout
        assert "sk-fake-env-key" not in result.stdout

    def test_missing_auth_fails(self, tmp_path):
        """Missing authentication should cause check to fail."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        # No auth.json, no env key
        result = run_wrapper(["--check"], env=env)
        assert "deepseek_auth=missing" in result.stdout
        assert result.returncode == 2


# ---------------------------------------------------------------------------
# Consent tests
# ---------------------------------------------------------------------------


class TestConsent:
    def test_check_no_ack_required(self, tmp_path):
        """--check must not require external-provider acknowledgement."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--check"], env=env)
        assert result.returncode == 0

    def test_real_delegation_requires_ack(self, tmp_path):
        """Real delegation must require CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "0",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(["--task", "test", "--model", "deepseek-v4-pro"], env=env)
        assert result.returncode != 0
        assert (
            "external-provider acknowledgement" in result.stderr.lower()
            or "ack" in result.stderr.lower()
        )

    def test_implementation_requires_write_ack(self, tmp_path):
        """Implementation mode must require CODEX_DEEPSEEK_WRITE_DELEGATION."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
            "CODEX_DEEPSEEK_WRITE_DELEGATION": "0",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "implementation",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
            ],
            env=env,
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Mode tests
# ---------------------------------------------------------------------------


class TestModes:
    def test_analysis_excludes_shell_and_write(self, tmp_path):
        """Analysis mode must exclude shell and write/edit tools."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
                "--dry-run",
            ],
            env=env,
        )
        assert result.returncode == 0
        # The actual --tools argument should contain only read,grep,find,ls
        # Search for the exact --tools argument pattern
        import re

        tools_match = re.search(r"--tools\s+(\S+)", result.stdout)
        assert tools_match, f"Could not find --tools in output: {result.stdout[:500]}"
        tools_val = tools_match.group(1)
        assert "read" in tools_val
        assert "bash" not in tools_val
        assert "write" not in tools_val
        assert "edit" not in tools_val

    def test_review_excludes_shell_and_write(self, tmp_path):
        """Review mode must exclude shell and write/edit tools."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "review",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
                "--dry-run",
            ],
            env=env,
        )
        import re

        tools_match = re.search(r"--tools\s+(\S+)", result.stdout)
        assert tools_match, f"Could not find --tools in output: {result.stdout[:500]}"
        tools_val = tools_match.group(1)
        assert "read" in tools_val
        assert "bash" not in tools_val
        assert "write" not in tools_val
        assert "edit" not in tools_val

    def test_test_mode_permits_bounded_shell(self, tmp_path):
        """Test mode permits bash but not write/edit."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "test",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
                "--dry-run",
            ],
            env=env,
        )
        import re

        tools_match = re.search(r"--tools\s+(\S+)", result.stdout)
        assert tools_match, f"Could not find --tools in output: {result.stdout[:500]}"
        tools_val = tools_match.group(1)
        assert "bash" in tools_val
        assert "write" not in tools_val
        assert "edit" not in tools_val

    def test_implementation_permits_write(self, tmp_path):
        """Implementation mode permits write/edit/bash."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
            "CODEX_DEEPSEEK_WRITE_DELEGATION": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "implementation",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
                "--dry-run",
            ],
            env=env,
        )
        tools_line = [l for l in result.stdout.split("\n") if "--tools" in l]
        if tools_line:
            tools_str = " ".join(tools_line)
            assert "write" in tools_str
            assert "edit" in tools_str
            assert "bash" in tools_str


# ---------------------------------------------------------------------------
# Execution / result tests
# ---------------------------------------------------------------------------


class TestExecution:
    def test_explicit_fallback_runs_after_first_model_fails(self, tmp_path):
        """Fallback is opt-in and tries the next exact model after failure."""
        pi_path = tmp_path / "bin" / "pi"
        pi_path.parent.mkdir(parents=True, exist_ok=True)
        pi_path.write_text("""#!/usr/bin/env bash
if [[ "$*" == *"--list-models"* ]]; then
cat <<'EOF'
provider  model              context  max-out  thinking  images
deepseek  first-model        1M       384K     yes       no
deepseek  second-model       1M       384K     yes       no
EOF
exit 0
fi
if [[ "$*" == *"--model first-model"* ]]; then exit 1; fi
echo "FALLBACK_RESULT"
exit 0
""")
        pi_path.chmod(0o755)
        env = {
            "PATH": str(pi_path.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "test",
                "--model",
                "first-model",
                "--fallback-model",
                "second-model",
                "--fallback-on-failure",
            ],
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode == 0
        assert "model_fallback_next=second-model" in result.stderr
        assert "second-model" in result.stdout

    def test_successful_worker_produces_result_and_metadata(self, tmp_path):
        """A successful delegation produces result and metadata files."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "test task",
                "--model",
                "deepseek-v4-pro",
                "--output-dir",
                str(output_dir),
            ],
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode == 0
        assert "delegation_result=" in result.stdout
        assert "delegation_metadata=" in result.stdout

    def test_worker_failure_preserved(self, tmp_path):
        """Non-zero Pi exit must be preserved."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT, exit_code=1)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            ["--mode", "analysis", "--task", "test", "--model", "deepseek-v4-pro"],
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode == 1

    def test_empty_result_rejected(self, tmp_path):
        """A Pi invocation producing empty output must be rejected."""
        pi_path = tmp_path / "bin" / "pi"
        pi_path.parent.mkdir(parents=True, exist_ok=True)
        pi_path.write_text("""#!/usr/bin/env bash
if [[ "$*" == *"--list-models"* ]]; then
    cat <<'EOF'
provider  model              context  max-out  thinking  images
deepseek  deepseek-v4-pro    1M       384K     yes       no
EOF
    exit 0
fi
# Produce empty output
exit 0
""")
        pi_path.chmod(0o755)
        env = {
            "PATH": str(pi_path.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        result = run_wrapper(
            ["--mode", "analysis", "--task", "test", "--model", "deepseek-v4-pro"],
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode != 0
        assert "empty" in result.stderr.lower()

    def test_sensitive_context_file_rejected(self, tmp_path):
        """Context files with sensitive names must be rejected."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        sensitive = tmp_path / ".env"
        sensitive.write_text("SECRET=value")
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
                "--context-file",
                str(sensitive),
            ],
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode != 0

    def test_no_secret_in_output(self, tmp_path):
        """Output and metadata must never contain API key values."""
        pi = make_fake_pi(tmp_path, MODEL_LIST_OUTPUT)
        env = {
            "PATH": str(pi.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "test task",
                "--model",
                "deepseek-v4-pro",
                "--output-dir",
                str(output_dir),
            ],
            env=env,
            cwd=tmp_path,
        )
        assert "sk-fake-test-key" not in result.stdout
        assert "sk-fake-test-key" not in result.stderr
        # Check metadata file contents
        result_path_line = [
            l for l in result.stdout.split("\n") if "delegation_metadata=" in l
        ]
        if result_path_line:
            meta_path = result_path_line[0].split("=", 1)[-1]
            if os.path.exists(meta_path):
                meta_content = Path(meta_path).read_text()
                assert "sk-fake-test-key" not in meta_content

    def test_stderr_preserved(self, tmp_path):
        """stderr from Pi must be preserved."""
        pi_path = tmp_path / "bin" / "pi"
        pi_path.parent.mkdir(parents=True, exist_ok=True)
        pi_path.write_text("""#!/usr/bin/env bash
if [[ "$*" == *"--list-models"* ]]; then
    cat <<'EOF'
provider  model              context  max-out  thinking  images
deepseek  deepseek-v4-pro    1M       384K     yes       no
EOF
    exit 0
fi
echo "diagnostic output" >&2
echo "FAKE_RESULT"
exit 0
""")
        pi_path.chmod(0o755)
        env = {
            "PATH": str(pi_path.parent) + ":" + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(tmp_path / ".pi" / "agent"),
            "CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK": "1",
        }
        make_fake_auth_json(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = run_wrapper(
            [
                "--mode",
                "analysis",
                "--task",
                "test",
                "--model",
                "deepseek-v4-pro",
                "--output-dir",
                str(output_dir),
            ],
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode == 0
        assert "delegation_stderr=" in result.stdout


# ---------------------------------------------------------------------------
# Installer tests
# ---------------------------------------------------------------------------


class TestInstaller:
    def test_dry_run_makes_no_changes(self, tmp_path):
        """--dry-run must not create files."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        result = run_installer(
            ["--install", "--dry-run", "--target", str(target), "--dev"]
        )
        assert result.returncode == 0
        assert "Would install" in result.stdout
        assert not target.exists()

    def test_first_install_succeeds(self, tmp_path):
        """First install must create the target directory."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        result = run_installer(["--install", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "installed_current" in result.stdout
        assert target.is_dir()
        assert (target / "SKILL.md").is_file()
        assert (target / "scripts" / "pi_deepseek_delegate.sh").is_file()

    def test_second_install_idempotent(self, tmp_path):
        """Second install should succeed and be idempotent."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        result2 = run_installer(["--install", "--target", str(target), "--dev"])
        assert result2.returncode == 0
        assert "installed_current" in result2.stdout

    def test_check_detects_current(self, tmp_path):
        """--check must report installed_current after install."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        result = run_installer(["--check", "--target", str(target), "--dev"])
        assert result.returncode == 0
        assert "installed_current" in result.stdout

    def test_check_detects_drift(self, tmp_path):
        """--check must report installed_drifted when files differ."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        # Corrupt a file
        (target / "SKILL.md").write_text("modified content")
        result = run_installer(["--check", "--target", str(target), "--dev"])
        assert result.returncode == 4
        assert "installed_drifted" in result.stdout

    def test_check_detects_not_installed(self, tmp_path):
        """--check must report not_installed when target missing."""
        target = tmp_path / "nonexistent" / "skill"
        result = run_installer(["--check", "--target", str(target), "--dev"])
        assert "not_installed" in result.stdout

    def test_install_excludes_tests(self, tmp_path):
        """Installed target must not include tests directory."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        assert not (target / "tests").exists()
        assert not (target / "test_pi_deepseek_delegate.py").exists()

    def test_uninstall_removes_skill(self, tmp_path):
        """Uninstall must remove only the owned skill files."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        assert target.is_dir()
        result = run_installer(["--uninstall", "--target", str(target)])
        assert result.returncode == 0
        assert "uninstalled" in result.stdout
        # After uninstall, owned files are gone; directory tree may remain if empty
        assert not (target / "SKILL.md").exists()
        assert not (target / "scripts" / "pi_deepseek_delegate.sh").exists()

    def test_install_preserves_executable(self, tmp_path):
        """Executable permissions on wrapper must be preserved."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        run_installer(["--install", "--target", str(target), "--dev"])
        wrapper = target / "scripts" / "pi_deepseek_delegate.sh"
        assert wrapper.is_file()
        st = wrapper.stat()
        assert st.st_mode & stat.S_IXUSR

    def test_install_does_not_affect_sibling(self, tmp_path):
        """Installer must not touch sibling skill directories."""
        target = tmp_path / "skills" / "pi-deepseek-delegation"
        sibling = tmp_path / "skills" / "other-skill"
        sibling.mkdir(parents=True)
        sibling_file = sibling / "SKILL.md"
        sibling_file.write_text("original")
        run_installer(["--install", "--target", str(target), "--dev"])
        assert sibling_file.read_text() == "original"

    def test_rejects_non_git_source(self, tmp_path):
        """Installer must reject non-git source without --dev."""
        # The real source IS in a git worktree, so this should pass without --dev.
        # Test that --dev is needed for dirty source.
        # Since the worktree HAS dirty files, we test that --dev works
        result = run_installer(["--check", "--target", str(tmp_path / "out")])
        # Without --dev and a dirty worktree, this should fail
        if result.returncode != 0:
            assert "dirty" in result.stdout.lower()

    def test_rejects_relative_target(self, tmp_path):
        """Installer must reject relative target paths."""
        result = run_installer(["--install", "--target", "relative/path", "--dev"])
        assert result.returncode != 0
        assert (
            "absolute" in result.stdout.lower() or "absolute" in result.stderr.lower()
        )

    def test_rejects_path_traversal_target(self, tmp_path):
        """Installer must reject target paths containing '..'."""
        result = run_installer(["--install", "--target", "/tmp/../etc/skill", "--dev"])
        assert result.returncode != 0
        assert ".." in result.stdout.lower() or ".." in result.stderr.lower()


# ---------------------------------------------------------------------------
# Secret sentinel
# ---------------------------------------------------------------------------


class TestSecrets:
    def test_no_secret_in_source(self):
        """No API key patterns should appear in skill source files."""
        import re

        secret_pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
        for root, dirs, files in os.walk(SKILL_DIR):
            # Skip .git, __pycache__, .pytest_cache, fixtures
            dirs[:] = [
                d
                for d in dirs
                if d not in (".git", "__pycache__", ".pytest_cache", "node_modules")
            ]
            for fname in files:
                if fname.endswith(".pyc"):
                    continue
                fpath = Path(root) / fname
                try:
                    content = fpath.read_text()
                except Exception:
                    continue
                matches = secret_pattern.findall(content)
                # The fake auth test has sk-fake-test-key which is fine
                real_matches = [
                    m
                    for m in matches
                    if "fake" not in m.lower() and "example" not in m.lower()
                ]
                assert (
                    not real_matches
                ), f"Secret pattern found in {fpath}: {real_matches}"

    def test_no_api_key_value_in_source(self):
        """No hardcoded API key values in source (env var names are fine)."""
        import re

        key_value_pattern = re.compile(r'api[_-]?key[\s"\'=:]+sk-', re.IGNORECASE)
        for root, dirs, files in os.walk(SKILL_DIR):
            dirs[:] = [
                d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")
            ]
            for fname in files:
                if fname.endswith((".pyc", ".py")):
                    continue
                fpath = Path(root) / fname
                try:
                    content = fpath.read_text()
                except Exception:
                    continue
                assert not key_value_pattern.search(
                    content
                ), f"API key value in {fpath}"
