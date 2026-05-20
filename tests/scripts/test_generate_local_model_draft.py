"""Tests for the local model draft adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.content import generate_local_model_draft as draft_module

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "content" / "generate_local_model_draft.py"


def _make_markdown(
    tmp_path: Path, name: str, content: str = "# Title\n\nBody.\n"
) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _generate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sources: list[Path] | None = None,
    body: str = "## Summary\n\nGrounded draft body.",
    output: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> Path:
    output_path = output or (tmp_path / "draft.md")
    source_paths = sources or [_make_markdown(tmp_path, "source.md")]

    def fake_post(
        endpoint: str, model: str, messages: list[dict[str, str]]
    ) -> str:
        return body

    monkeypatch.setattr(draft_module, "_post_chat_completion", fake_post)
    draft_module.generate_local_model_draft(
        date_str="2026-05-17",
        source_paths=source_paths,
        output_path=output_path,
        draft_kind="website-update",
        provider="local",
        model="local-test",
        endpoint="http://localhost:11434/v1",
        force=force,
        dry_run=dry_run,
    )
    return output_path


def test_successful_draft_generation_with_mocked_local_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = _generate(tmp_path, monkeypatch)

    content = output.read_text(encoding="utf-8")
    assert "# website-update — 2026-05-17" in content
    assert "Grounded draft body." in content
    assert (
        "Model-assisted draft — review required before publication." in content
    )


def test_multiple_source_files_included(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src1 = _make_markdown(tmp_path, "one.md", "# One\n\nFirst source.\n")
    src2 = _make_markdown(tmp_path, "two.md", "# Two\n\nSecond source.\n")

    output = _generate(tmp_path, monkeypatch, sources=[src1, src2])
    content = output.read_text(encoding="utf-8")

    assert f"`{src1}`" in content
    assert f"`{src2}`" in content


def test_missing_source_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(FileNotFoundError, match="source file not found"):
        _generate(tmp_path, monkeypatch, sources=[tmp_path / "missing.md"])


def test_empty_source_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _make_markdown(tmp_path, "empty.md", "")

    with pytest.raises(ValueError, match="empty"):
        _generate(tmp_path, monkeypatch, sources=[src])


def test_non_markdown_source_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "source.txt"
    src.write_text("plain text\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not a Markdown file"):
        _generate(tmp_path, monkeypatch, sources=[src])


def test_missing_endpoint_model_failure() -> None:
    with pytest.raises(ValueError, match="no local draft endpoint configured"):
        draft_module._resolve_endpoint(None, {})
    with pytest.raises(ValueError, match="no local draft model configured"):
        draft_module._resolve_model(None, {})


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.openai.com/v1",
        "http://api.anthropic.com:443/v1",
        "http://api.groq.com:443/v1",
        "http://api.minimax.io:443/v1",
    ],
)
def test_cloud_endpoint_rejection(endpoint: str) -> None:
    with pytest.raises(ValueError):
        draft_module._validate_local_endpoint(endpoint, {})


def test_lan_endpoint_rejected_by_default() -> None:
    with pytest.raises(ValueError, match="LAN/Tailscale"):
        draft_module._validate_local_endpoint(
            "http://192.168.1.44:11434/v1", {}
        )


def test_lan_endpoint_allowed_with_env() -> None:
    endpoint = draft_module._validate_local_endpoint(
        "http://192.168.1.44:11434/v1",
        {"CODEXIFY_ALLOW_LOCAL_DRAFT_LAN": "1"},
    )
    assert endpoint == "http://192.168.1.44:11434/v1"


def test_existing_output_without_force_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "draft.md"
    output.write_text("existing\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        _generate(tmp_path, monkeypatch, output=output)


def test_overwrite_with_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "draft.md"
    output.write_text("existing\n", encoding="utf-8")

    _generate(
        tmp_path,
        monkeypatch,
        output=output,
        body="Replacement body.",
        force=True,
    )

    assert "Replacement body." in output.read_text(encoding="utf-8")


def test_dry_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "dry-run.md"
    _generate(tmp_path, monkeypatch, output=output, dry_run=True)

    assert not output.exists()


def test_source_secret_like_value_blocks_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _make_markdown(tmp_path, "source.md", "# Source\n\napi_key=abc123\n")

    with pytest.raises(ValueError, match="secret-like value"):
        _generate(tmp_path, monkeypatch, sources=[src])


def test_generated_secret_like_value_blocks_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "draft.md"

    with pytest.raises(ValueError, match="secret-like value"):
        _generate(tmp_path, monkeypatch, output=output, body="token=abc123")
    assert not output.exists()


def test_prompt_contains_grounding_and_no_invention_constraints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, list[dict[str, str]]] = {}

    def fake_post(
        endpoint: str, model: str, messages: list[dict[str, str]]
    ) -> str:
        captured["messages"] = messages
        return "Grounded draft."

    monkeypatch.setattr(draft_module, "_post_chat_completion", fake_post)
    src = _make_markdown(
        tmp_path, "source.md", "# Local Fact\n\nOnly this fact.\n"
    )
    draft_module.generate_local_model_draft(
        date_str="2026-05-17",
        source_paths=[src],
        output_path=tmp_path / "draft.md",
        draft_kind="email",
        provider="local",
        model="local-test",
        endpoint="http://localhost:11434/v1",
    )

    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert "Use only the provided source text" in prompt
    assert "Do not invent metrics" in prompt
    assert "release promises" in prompt
    assert "unresolved gaps" in prompt


def test_output_includes_note_sources_draft_kind_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _make_markdown(tmp_path, "source.md")

    output = _generate(tmp_path, monkeypatch, sources=[src])
    content = output.read_text(encoding="utf-8")

    assert "**Draft kind:** website-update" in content
    assert "**Provider:** local" in content
    assert "**Model:** local-test" in content
    assert "**Endpoint:** `http://localhost:11434/v1`" in content
    assert f"`{src}`" in content
    assert (
        "Model-assisted draft — review required before publication." in content
    )


def test_no_command_execution_occurs() -> None:
    assert not hasattr(draft_module, "subprocess")
