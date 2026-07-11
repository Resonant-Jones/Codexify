#!/usr/bin/env python3
"""Seed the isolated Codexify Peekaboo demo account in the tester runtime."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CONTENT_PATH = Path(__file__).with_name("demo-content.json")
DEMO_ASSETS = ROOT / "Demo-Assets" / "peekaboo-demo" / "assets"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def config() -> dict[str, str]:
    values = load_env_file(ROOT / ".env.tester")
    values.update(load_env_file(ROOT / ".env.demo"))
    values.update({key: value for key, value in os.environ.items() if key.startswith("DEMO_")})
    return {
        "api_base": values.get("DEMO_API_BASE", "http://localhost:8889").rstrip("/"),
        "frontend_base": values.get("DEMO_FRONTEND_BASE", "http://localhost:5174").rstrip("/"),
        "username": values.get("DEMO_USERNAME", "rowan"),
        "password": values.get("DEMO_PASSWORD", ""),
        "database_url": values.get("DEMO_DATABASE_URL", ""),
        "postgres_user": values.get("POSTGRES_USER", "codexify"),
        "postgres_password": values.get("POSTGRES_PASSWORD", "codexify"),
        "postgres_db": values.get("POSTGRES_DB", "Codexify"),
    }


def request_json(
    base: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    expected: tuple[int, ...] = (200,),
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            if response.status not in expected:
                raise RuntimeError(f"{method} {path}: unexpected status {response.status}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code in expected:
            return json.loads(detail) if detail else {}
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {detail[:240]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to reach {base}: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def request_file(
    base: str,
    path: str,
    file_path: Path,
    *,
    fields: dict[str, str] | None = None,
    token: str | None = None,
    expected: tuple[int, ...] = (200,),
) -> dict[str, Any]:
    boundary = f"----CodexifyDemo{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in (fields or {}).items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ]
        )
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    body = b"".join(chunks)
    headers = {
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base}{path}", data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            if response.status not in expected:
                raise RuntimeError(f"POST {path}: unexpected status {response.status}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code in expected:
            return json.loads(detail) if detail else {}
        raise RuntimeError(f"POST {path}: HTTP {exc.code}: {detail[:240]}") from exc
    return json.loads(raw) if raw else {}


def login(cfg: dict[str, str]) -> str:
    if not cfg["password"] or cfg["password"].startswith("<"):
        raise RuntimeError("Set DEMO_PASSWORD in .env.demo before running the demo seed.")
    try:
        request_json(
            cfg["api_base"],
            "/auth/register",
            method="POST",
            payload={"username": cfg["username"], "password": cfg["password"]},
        )
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise
    response = request_json(
        cfg["api_base"],
        "/auth/login",
        method="POST",
        payload={"username": cfg["username"], "password": cfg["password"]},
    )
    token = str(response.get("token", "")).strip()
    if not token:
        raise RuntimeError("Login did not return a session token.")
    return token


def list_threads(cfg: dict[str, str], token: str) -> list[dict[str, Any]]:
    response = request_json(cfg["api_base"], "/api/chat/threads?limit=200", token=token)
    return list(response.get("threads", []))


def list_images(cfg: dict[str, str], token: str) -> list[dict[str, Any]]:
    response = request_json(cfg["api_base"], "/api/media/images?limit=100", token=token)
    return list(response.get("images", []))


def list_documents(cfg: dict[str, str], token: str) -> list[dict[str, Any]]:
    response = request_json(cfg["api_base"], "/api/media/documents?limit=100", token=token)
    return list(response.get("documents", []))


def reset_demo_account(cfg: dict[str, str], token: str) -> None:
    for image in list_images(cfg, token):
        image_id = image.get("id")
        if image_id:
            request_json(
                cfg["api_base"],
                f"/api/media/images/{image_id}",
                method="DELETE",
                token=token,
            )
    for document in list_documents(cfg, token):
        document_id = document.get("id")
        if document_id:
            request_json(
                cfg["api_base"],
                f"/api/media/documents/{document_id}",
                method="DELETE",
                token=token,
            )
    for thread in list_threads(cfg, token):
        thread_id = thread.get("id")
        if thread_id is None:
            continue
        request_json(
            cfg["api_base"],
            f"/api/chat/threads/{int(thread_id)}?force=true",
            method="DELETE",
            token=token,
        )


def seed(cfg: dict[str, str], token: str, content: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for thread_spec in reversed(content["threads"]):
        created = request_json(
            cfg["api_base"],
            "/api/chat/threads",
            method="POST",
            payload={"title": thread_spec["title"]},
            token=token,
        )
        thread = created.get("thread") or {}
        thread_id = int(created.get("id") or thread.get("id"))
        messages = thread_spec.get("messages", []) or [
            {"role": "user", "content": "Noted."}
        ]
        for message in messages:
            request_json(
                cfg["api_base"],
                f"/api/chat/{thread_id}/messages",
                method="POST",
                payload={"role": message["role"], "content": message["content"]},
                token=token,
            )
        records.append({"id": thread_id, "title": thread_spec["title"], "message_count": len(messages)})
    return records


def seed_assets(cfg: dict[str, str], token: str, records: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_title = {record["title"]: int(record["id"]) for record in records}
    primary_thread_id = by_title["What changed since Tuesday?"]
    uploaded_images: list[str] = []
    for filename in (
        "abstract-signal-study.png",
        "interface-moodboard.png",
        "field-notes-map.png",
    ):
        response = request_file(
            cfg["api_base"],
            "/api/media/upload/image",
            DEMO_ASSETS / "images" / filename,
            fields={"thread_id": str(primary_thread_id), "source_tag": "uploaded"},
            token=token,
        )
        uploaded_images.append(str(response.get("id", "")))

    uploaded_documents: list[str] = []
    for filename in ("launch-brief.md", "onboarding-observations.txt", "workspace-notes.txt"):
        response = request_file(
            cfg["api_base"],
            "/api/media/upload/document",
            DEMO_ASSETS / "documents" / filename,
            fields={"thread_id": str(primary_thread_id), "source_tag": "demo"},
            token=token,
        )
        uploaded_documents.append(str(response.get("id", response.get("document_id", ""))))
    return {"images": uploaded_images, "documents": uploaded_documents}


def normalize_sidebar_order(cfg: dict[str, str], records: list[dict[str, Any]]) -> None:
    """Use the tester DB only for deterministic ordering of this demo user."""
    database_url = cfg["database_url"] or (
        f"postgresql://{cfg['postgres_user']}:{cfg['postgres_password']}"
        f"@localhost:5434/{cfg['postgres_db']}"
    )
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for deterministic sidebar ordering.") from exc

    base = datetime.now(timezone.utc)
    order_by_title = {record["title"]: record["id"] for record in records}
    content = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for position, thread_spec in enumerate(content["threads"], start=1):
                thread_id = order_by_title[thread_spec["title"]]
                stamp = base + timedelta(seconds=len(content["threads"]) - position)
                cursor.execute(
                    "UPDATE chat_threads SET last_interaction_at = %s, updated_at = %s "
                    "WHERE id = %s AND user_id = %s",
                    (stamp, stamp, thread_id, cfg["username"]),
                )


def verify(cfg: dict[str, str], token: str, content: dict[str, Any]) -> dict[str, Any]:
    threads = list_threads(cfg, token)
    titles = [str(thread.get("title", "")) for thread in threads]
    expected_titles = [str(thread["title"]) for thread in content["threads"]]
    if titles[: len(expected_titles)] != expected_titles:
        raise RuntimeError(f"Sidebar order mismatch: {titles[:len(expected_titles)]}")
    by_title = {str(thread.get("title")): thread for thread in threads}
    counts: dict[str, int] = {}
    for thread_spec in content["threads"]:
        title = str(thread_spec["title"])
        thread_id = int(by_title[title]["id"])
        messages = request_json(cfg["api_base"], f"/api/chat/{thread_id}/messages?limit=100", token=token)
        counts[title] = len(messages.get("messages", []))
        expected_count = len(thread_spec.get("messages", []) or [{"role": "user", "content": "Noted."}])
        if counts[title] != expected_count:
            raise RuntimeError(f"Message count mismatch for {title!r}: {counts[title]} != {expected_count}")
    primary_id = int(by_title["What changed since Tuesday?"]["id"])
    images = list_images(cfg, token)
    documents = list_documents(cfg, token)
    image_names = sorted(str(image.get("filename", "")) for image in images)
    document_names = sorted(str(document.get("filename", "")) for document in documents)
    expected_image_names = sorted(
        ["abstract-signal-study.png", "interface-moodboard.png", "field-notes-map.png"]
    )
    expected_document_names = sorted(
        ["launch-brief.md", "onboarding-observations.txt", "workspace-notes.txt"]
    )
    if image_names != expected_image_names:
        raise RuntimeError(f"Demo image mismatch: {image_names}")
    if document_names != expected_document_names:
        raise RuntimeError(f"Demo document mismatch: {document_names}")
    return {
        "username": cfg["username"],
        "thread_count": len(threads),
        "titles": titles,
        "message_counts": counts,
        "image_count": len(images),
        "document_count": len(documents),
        "primary_thread_id": primary_id,
        "image_filenames": image_names,
        "document_filenames": document_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("reset", "seed", "verify", "reset-and-seed"))
    args = parser.parse_args()
    cfg = config()
    content = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    token = login(cfg)
    if args.command in {"reset", "reset-and-seed"}:
        reset_demo_account(cfg, token)
    if args.command in {"seed", "reset-and-seed"}:
        records = seed(cfg, token, content)
        normalize_sidebar_order(cfg, records)
        seed_assets(cfg, token, records)
    if args.command in {"verify", "seed", "reset-and-seed"}:
        print(json.dumps(verify(cfg, token, content), indent=2, sort_keys=True))
    else:
        print(json.dumps({"username": cfg["username"], "reset": True}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, ValueError) as exc:
        print(f"demo seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
