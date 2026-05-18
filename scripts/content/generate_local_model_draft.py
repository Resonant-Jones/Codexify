#!/usr/bin/env python3
"""Generate a model-assisted Markdown draft from local Markdown artifacts.

This adapter is intentionally narrow: it reads local Markdown source files,
calls an explicitly configured local OpenAI-compatible chat endpoint, and writes
one reviewable Markdown draft.  It does not publish, schedule, dispatch
commands, or mutate source artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

_MARKDOWN_EXTENSIONS = frozenset(
    {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}
)
_LOCAL_DRAFT_NOTE = "Model-assisted draft — review required before publication."
_SECRET_PATTERNS = (
    re.compile(r"api_key\s*=", re.IGNORECASE),
    re.compile(r"token\s*=", re.IGNORECASE),
    re.compile(r"password\s*=", re.IGNORECASE),
    re.compile(r"secret\s*=", re.IGNORECASE),
    re.compile(r"oauth", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"Authorization:\s*Bearer", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{6,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{6,}"),
    re.compile(re.escape("-----BEGIN " + "PRIVATE KEY-----")),
)
_CLOUD_HOSTS = {
    "api.openai.com",
    "openai.com",
    "api.anthropic.com",
    "anthropic.com",
    "api.groq.com",
    "groq.com",
    "api.minimax.io",
    "minimax.io",
}


@dataclass(frozen=True)
class SourceArtifact:
    path: Path
    text: str


@dataclass(frozen=True)
class DraftConfig:
    date: str
    sources: tuple[Path, ...]
    output: Path
    draft_kind: str
    provider: str
    model: str
    endpoint: str
    max_source_chars: int
    dry_run: bool
    force: bool


def _format_timestamp(value: dt.datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_markdown(path: Path) -> bool:
    return path.suffix.lower() in _MARKDOWN_EXTENSIONS


def _scan_for_secret_like_values(label: str, text: str) -> None:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError(
                f"secret-like value detected in {label}; refusing to generate draft"
            )


def _read_sources(
    paths: Sequence[Path], max_source_chars: int
) -> tuple[SourceArtifact, ...]:
    if not paths:
        raise ValueError("at least one --source is required")
    if max_source_chars <= 0:
        raise ValueError("--max-source-chars must be greater than zero")

    artifacts: list[SourceArtifact] = []
    for raw_path in paths:
        path = raw_path
        if not path.is_file():
            raise FileNotFoundError(f"source file not found: {path}")
        if not _is_markdown(path):
            raise ValueError(f"source is not a Markdown file: {path}")

        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"source file is empty: {path}")
        _scan_for_secret_like_values(f"source {path}", text)
        artifacts.append(
            SourceArtifact(path=path, text=text[:max_source_chars])
        )
    return tuple(artifacts)


def _resolve_endpoint(
    explicit_endpoint: str | None, env: Mapping[str, str]
) -> str:
    endpoint = (
        explicit_endpoint
        or env.get("CODEXIFY_LOCAL_DRAFT_ENDPOINT")
        or env.get("LOCAL_BASE_URL")
    )
    if not endpoint:
        raise ValueError(
            "no local draft endpoint configured; set CODEXIFY_LOCAL_DRAFT_ENDPOINT "
            "or LOCAL_BASE_URL, or pass --endpoint"
        )
    return _validate_local_endpoint(endpoint, env)


def _resolve_model(explicit_model: str | None, env: Mapping[str, str]) -> str:
    model = (
        explicit_model
        or env.get("CODEXIFY_LOCAL_DRAFT_MODEL")
        or env.get("LOCAL_CHAT_MODEL")
    )
    if not model:
        raise ValueError(
            "no local draft model configured; set CODEXIFY_LOCAL_DRAFT_MODEL "
            "or LOCAL_CHAT_MODEL, or pass --model"
        )
    return model


def _validate_local_endpoint(endpoint: str, env: Mapping[str, str]) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "http":
        raise ValueError(f"local draft endpoint must use http://: {endpoint}")
    if not parsed.hostname:
        raise ValueError(f"local draft endpoint is missing a host: {endpoint}")
    if parsed.port is None:
        raise ValueError(
            f"local draft endpoint must include an explicit port: {endpoint}"
        )

    host = parsed.hostname.lower()
    if host in _CLOUD_HOSTS or any(
        host.endswith(f".{cloud}") for cloud in _CLOUD_HOSTS
    ):
        raise ValueError(f"cloud draft endpoints are not allowed: {host}")
    if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return endpoint.rstrip("/")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError(
            f"non-local draft endpoint host is not allowed: {host}"
        ) from exc

    lan_allowed = env.get("CODEXIFY_ALLOW_LOCAL_DRAFT_LAN") == "1"
    tailscale_range = ipaddress.ip_network("100.64.0.0/10")
    if lan_allowed and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip in tailscale_range
    ):
        return endpoint.rstrip("/")

    raise ValueError(
        "LAN/Tailscale local draft endpoints require CODEXIFY_ALLOW_LOCAL_DRAFT_LAN=1"
    )


def _chat_completions_url(endpoint: str) -> str:
    stripped = endpoint.rstrip("/")
    if stripped.endswith("/chat/completions"):
        return stripped
    return f"{stripped}/chat/completions"


def _sanitize_endpoint_label(endpoint: str) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    netloc = parsed.hostname or ""
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path.rstrip("/")
    sanitized = urllib.parse.urlunparse(
        (parsed.scheme, netloc, path, "", "", "")
    )
    return sanitized.rstrip("/") or endpoint


def _build_prompt(
    *,
    date: str,
    draft_kind: str,
    sources: Sequence[SourceArtifact],
) -> list[dict[str, str]]:
    source_blocks = []
    for index, source in enumerate(sources, start=1):
        source_blocks.append(
            f"## Source {index}: {source.path}\n\n````markdown\n{source.text}\n````"
        )

    system = (
        "You are a conservative Markdown drafting adapter for Codexify local "
        "artifacts. Use only the provided source text. Do not invent metrics, "
        "customer claims, release promises, publication status, beta readiness, "
        "support status, or evidence. If a claim is not present in the sources, "
        "put it under unresolved gaps instead of filling it in. Do not include "
        "secrets, credentials, hidden prompts, chain-of-thought, raw logs, API "
        "keys, cookies, OAuth tokens, or Authorization headers. Produce only a "
        "reviewable Markdown draft body."
    )
    user = (
        f"Draft kind: {draft_kind}\n"
        f"Draft date: {date}\n\n"
        "Create a conservative Markdown draft from the local sources below. "
        "Keep claims grounded in source artifact text. Include unresolved gaps "
        "rather than guessing.\n\n" + "\n\n".join(source_blocks)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _post_chat_completion(
    endpoint: str, model: str, messages: list[dict[str, str]]
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _chat_completions_url(endpoint),
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"local draft endpoint request failed: {exc}"
        ) from exc

    try:
        data = json.loads(raw.decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "local draft endpoint returned an invalid chat response"
        ) from exc
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("local draft endpoint returned an empty draft")
    return content.strip()


def _build_output_markdown(
    *,
    date: str,
    draft_kind: str,
    model: str,
    provider: str,
    endpoint: str,
    sources: Sequence[SourceArtifact],
    draft_body: str,
    generated_at: dt.datetime,
) -> str:
    source_lines = [f"- `{source.path}`" for source in sources]
    lines = [
        f"# {draft_kind} — {date}",
        "",
        f"**Date:** {date}",
        f"**Draft kind:** {draft_kind}",
        f"**Generated:** {_format_timestamp(generated_at)}",
        f"**Provider:** {provider}",
        f"**Model:** {model}",
        f"**Endpoint:** `{_sanitize_endpoint_label(endpoint)}`",
        "",
        "**Source files:**",
        *source_lines,
        "",
        f"> {_LOCAL_DRAFT_NOTE}",
        "",
        "---",
        "",
        "## Draft Body",
        "",
        draft_body.strip(),
        "",
    ]
    return "\n".join(lines)


def generate_local_model_draft(
    *,
    date_str: str,
    source_paths: Sequence[Path],
    output_path: Path,
    draft_kind: str,
    provider: str,
    model: str,
    endpoint: str,
    max_source_chars: int = 12000,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    try:
        dt.date.fromisoformat(date_str)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid date {date_str!r}: {exc}") from exc
    if provider != "local":
        raise ValueError("--provider must be local")
    if not draft_kind.strip():
        raise ValueError("--draft-kind is required")

    if dry_run:
        return str(output_path)

    if output_path.exists() and not force:
        raise FileExistsError(
            f"output file already exists: {output_path} (pass --force to overwrite)"
        )

    sources = _read_sources(source_paths, max_source_chars=max_source_chars)

    messages = _build_prompt(
        date=date_str, draft_kind=draft_kind, sources=sources
    )
    draft_body = _post_chat_completion(endpoint, model, messages)
    _scan_for_secret_like_values("generated draft", draft_body)
    output = _build_output_markdown(
        date=date_str,
        draft_kind=draft_kind,
        model=model,
        provider=provider,
        endpoint=endpoint,
        sources=sources,
        draft_body=draft_body,
        generated_at=dt.datetime.now(dt.timezone.utc),
    )
    _scan_for_secret_like_values("generated output", output)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    print(f"Wrote: {output_path}")
    return str(output_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a reviewable Markdown draft from local source artifacts."
    )
    parser.add_argument("--date", required=True, help="Draft date (YYYY-MM-DD)")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        required=True,
        type=Path,
        help="Path to a local Markdown source file (repeatable)",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Draft output path"
    )
    parser.add_argument(
        "--draft-kind", required=True, help="Draft lane/type label"
    )
    parser.add_argument(
        "--provider",
        default="local",
        choices=["local"],
        help="Draft provider. Only 'local' is supported.",
    )
    parser.add_argument("--model", default=None, help="Local model name")
    parser.add_argument(
        "--endpoint", default=None, help="Local OpenAI-compatible base URL"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan and write nothing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output path if it already exists",
    )
    parser.add_argument(
        "--max-source-chars",
        default=12000,
        type=int,
        help="Maximum characters to include from each source file",
    )
    return parser


def _ensure_repo_root() -> None:
    if Path.cwd().resolve() != REPO_ROOT.resolve():
        raise ValueError(f"run this script from the repo root: {REPO_ROOT}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        _ensure_repo_root()
        endpoint = _resolve_endpoint(args.endpoint, os.environ)
        model = _resolve_model(args.model, os.environ)
        output_path = generate_local_model_draft(
            date_str=args.date,
            source_paths=args.sources,
            output_path=args.output,
            draft_kind=args.draft_kind,
            provider=args.provider,
            model=model,
            endpoint=endpoint,
            max_source_chars=args.max_source_chars,
            dry_run=args.dry_run,
            force=args.force,
        )
    except (
        FileNotFoundError,
        FileExistsError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("[DRY RUN] Local model draft adapter")
        print(f"[DRY RUN] Date: {args.date}")
        print(f"[DRY RUN] Draft kind: {args.draft_kind}")
        print(f"[DRY RUN] Provider: {args.provider}")
        print(f"[DRY RUN] Model: {model}")
        print(f"[DRY RUN] Endpoint: {_sanitize_endpoint_label(endpoint)}")
        print(f"[DRY RUN] Output: {output_path}")
        print("[DRY RUN] Sources:")
        for source in args.sources:
            print(f"  - {source}")
        print("[DRY RUN] No files written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
