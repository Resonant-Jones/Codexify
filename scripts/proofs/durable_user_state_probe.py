"""Opt-in isolated persistence probe; never executes chat/provider/worker work.

Run under the environment recorded by the PERSIST-003 receipt. The controller
owns the disposable PostgreSQL target and launches each phase in a new process.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("seed", "seed-media", "snapshot", "serve"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--port", type=int, default=17174)
    args = parser.parse_args()
    root = Path(args.output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if os.environ.get("PERSISTENCE_PROOF_ISOLATED_TARGET") != "persist003":
        raise RuntimeError("Explicit isolated persistence target required")
    dsn = os.environ["DATABASE_URL"]
    if "@127.0.0.1:" not in dsn:
        raise RuntimeError("The probe requires its disposable loopback target")

    from guardian.core import dependencies
    from guardian.core.db import load_guardian_db_from_env
    from guardian.db import models
    from guardian.services import onboarding_service
    from guardian.protocol_tokens import EmbeddingLifecycleStatus

    chatdb = dependencies.init_database()
    db = load_guardian_db_from_env()
    assert chatdb is not None and db is not None

    if args.phase == "seed":
        with db.get_session() as session:
            for owner in ("persist003-a", "persist003-b"):
                session.add(models.User(id=owner, username=owner,
                                        email=f"{owner}@example.invalid",
                                        password_hash="non-login-proof-fixture", role="guest"))
            session.commit()
            for owner in ("persist003-a", "persist003-b"):
                session.add(models.AuthenticatedPrincipal(account_id=owner, subject_id=f"{owner}@example.invalid"))
            session.commit()
            projects = []
            for owner in ("persist003-a", "persist003-b"):
                row = models.Project(user_id=owner, name="Persistence proof", description=f"Owned by {owner}")
                session.add(row)
                session.flush()
                projects.append(row.id)
            session.commit()
        threads = []
        for owner, project in zip(("persist003-a", "persist003-b"), projects):
            row = chatdb.create_chat_thread(owner, f"Retained {owner}", project_id=project,
                                           metadata={"fixture": "already-terminal", "authored_origin": "persist003"})
            threads.append(row["id"])
        other = chatdb.create_chat_thread("persist003-a", "Other account A thread", project_id=projects[0])["id"]
        message_ids = []
        for owner, thread in zip(("persist003-a", "persist003-b"), threads):
            message_ids += [chatdb.create_message(thread, "user", f"Authored prompt {owner}", user_id=owner),
                            chatdb.create_message(thread, "assistant", f"Persisted result {owner}", user_id=owner)]
        config = {"use_retrieval": True, "custom_system_prompt": "Retained authored configuration"}
        with db.get_session() as session:
            session.get(models.ChatThread, threads[0]).thread_config = config
            for mid in message_ids:
                session.get(models.ChatMessage, mid).extra_meta = {"fixture": "persist003", "lineage_marker": f"message-{mid}"}
            session.commit()
            onboarding_service.patch_state(session, "persist003-a", {"status": "completed", "desktop_tour_completed": True, "contextual_tips_enabled": False})
        from guardian.routes import documents
        from guardian.core.dependencies import RequestUserScope
        documents.configure_db(db)
        scope = RequestUserScope(user_id="persist003-a", account_id="persist003-a", multi_user_enabled=True)
        note = asyncio.run(documents.save_workspace_note(
            documents.WorkspaceNoteSaveRequest(thread_id=threads[0], title="Retained note", content="Authored note content", format="md"),
            _api_key="resolved-proof-scope", request_user_scope=scope))
        blob = b"Retained uploaded document bytes\n"
        from guardian.core.storage import create_storage_from_env
        storage = create_storage_from_env()
        src = storage.upload_file(blob, "documents/persist003-retained.txt", "text/plain")
        with db.get_session() as session:
            session.add(models.UploadedDocument(id="persist003-upload", project_id=projects[0], thread_id=threads[0], user_id="persist003-a", filename="persist003-retained.txt", filesize=len(blob), mime_type="text/plain", src_url=src, parsed_text=blob.decode(), embedding_status=EmbeddingLifecycleStatus.PENDING.value))
            session.add(models.ThreadDocument(thread_id=threads[0], document_id="persist003-upload", relation="attached"))
            session.add(models.ProjectDocumentLink(project_id=projects[0], document_id="persist003-upload", document_type="uploaded", attached_by="persist003-a"))
            session.commit()
        manifest = {"projects": projects, "threads": threads, "other_thread": other, "messages": message_ids,
                    "note": note["document_id"], "upload": "persist003-upload", "blob_url": src,
                    "blob_sha256": hashlib.sha256(blob).hexdigest(), "thread_config": config}
        (root / "fixture.json").write_text(json.dumps(manifest, indent=2))
        print(json.dumps({"seeded": True, "pid": os.getpid(), "fixture": manifest}))
        return

    if args.phase == "seed-media":
        # Retained legacy-compatible rows only; never invokes generation/upload work.
        import base64
        from datetime import datetime, timezone
        from guardian.core.storage import create_storage_from_env

        media_manifest_path = root / "media-fixture.json"
        if media_manifest_path.exists():
            raise RuntimeError("Media fixture already exists; preserve it")
        storage = create_storage_from_env()
        timestamp = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1kAAAAASUVORK5CYII=")
        rows = []
        blob_hashes = {}
        with db.get_session() as session:
            for model in (models.UploadedImage, models.GeneratedImage):
                assert session.query(model).filter(model.id.like("persist017-%")).count() == 0
            fixtures = [("persist003-a", 1, 1, "uploaded", 105),
                        ("persist003-b", 2, 2, "uploaded", 2),
                        ("persist003-a", 1, 1, "generated", 2),
                        ("persist003-b", 2, 2, "generated", 1)]
            for owner, project, thread, family, count in fixtures:
                for index in range(count):
                    row_id = f"persist017-{owner[-1]}-{family}-{index:03d}"
                    data = png + row_id.encode()
                    src = storage.upload_file(data, f"images/{row_id}.png", "image/png")
                    blob_hashes[src] = hashlib.sha256(data).hexdigest()
                    common = dict(id=row_id, project_id=project, thread_id=(3 if owner == "persist003-a" and family == "uploaded" and index == 0 else thread), user_id=owner, src_url=src, created_at=timestamp)
                    if family == "uploaded":
                        row = models.UploadedImage(**common, filename=f"Retained {row_id}.png", filesize=len(data), mime_type="image/png", source_tag="uploaded")
                    else:
                        row = models.GeneratedImage(**common, prompt=f"Retained {row_id}", model="persist017-fixture-only")
                    session.add(row)
                    rows.append(dict(id=row_id, owner=owner, family=family, src=src, deleted=False, source_tag=family, thread=common["thread_id"]))
            for suffix, tag, deleted in (("unclassified", None, False), ("legacy-source", "generated", False), ("deleted", "uploaded", True)):
                row_id = f"persist017-a-{suffix}"
                data = png + row_id.encode()
                src = storage.upload_file(data, f"images/{row_id}.png", "image/png")
                blob_hashes[src] = hashlib.sha256(data).hexdigest()
                session.add(models.UploadedImage(id=row_id, project_id=1, thread_id=1, user_id="persist003-a", src_url=src, filename=f"Retained {suffix}.png", filesize=len(data), mime_type="image/png", source_tag=tag, created_at=timestamp, deleted_at=timestamp if deleted else None))
                rows.append(dict(id=row_id, owner="persist003-a", family="uploaded", src=src, deleted=deleted, source_tag=tag, thread=1))
            session.commit()
        manifest = dict(rows=rows, blob_sha256=blob_hashes)
        media_manifest_path.write_text(json.dumps(manifest, indent=2))
        print(json.dumps(dict(seeded=True, pid=os.getpid(), uploaded_rows=110, generated_rows=3, blob_count=len(blob_hashes))))
        return

    if args.phase == "snapshot":
        from sqlalchemy import text
        tables = ("projects", "chat_threads", "chat_messages", "generated_documents", "uploaded_documents", "thread_documents", "project_document_links", "user_onboarding_state", "authenticated_principals", "chat_completion_attempts", "user_profiles", "uploaded_images", "generated_images", "media_assets", "media_aliases")
        snapshot = {}
        with db.get_session() as session:
            for table in tables:
                snapshot[table] = [dict(row) for row in session.execute(text(f"SELECT * FROM {table} ORDER BY 1")).mappings()]
        fixture = json.loads((root / "fixture.json").read_text())
        snapshot["chatdb_messages"] = [chatdb.list_messages(tid) for tid in fixture["threads"]]
        snapshot["chatdb_threads"] = [chatdb.get_chat_thread(tid) for tid in fixture["threads"]]
        from guardian.core.storage import create_storage_from_env
        snapshot["blob_sha256"] = hashlib.sha256(create_storage_from_env().download_file(fixture["blob_url"])).hexdigest()
        assert snapshot["blob_sha256"] == fixture["blob_sha256"]
        media_manifest_path = root / "media-fixture.json"
        if media_manifest_path.exists():
            media_manifest = json.loads(media_manifest_path.read_text())
            storage = create_storage_from_env()
            snapshot["media_blob_sha256"] = {
                src: hashlib.sha256(storage.download_file(src)).hexdigest()
                for src in media_manifest["blob_sha256"]
            }
            assert snapshot["media_blob_sha256"] == media_manifest["blob_sha256"]
        print(json.dumps({"pid": os.getpid(), "snapshot": snapshot}, default=str, sort_keys=True))
        return

    from fastapi import FastAPI
    from guardian.routes import chat, documents, media, onboarding, projects, user_profile
    documents.configure_db(db)
    app = FastAPI()

    @app.middleware("http")
    async def capture_probe_failure(request, call_next):
        try:
            return await call_next(request)
        except Exception:
            import traceback
            (root / "route-exception.log").write_text(traceback.format_exc())
            raise

    app.include_router(chat.api_chat_router)
    app.include_router(chat.threads_router)
    app.include_router(chat.thread_router)
    app.include_router(documents.router)
    app.include_router(media.router, prefix="/api/media")
    app.include_router(projects.api_router)
    app.include_router(projects.router)
    app.include_router(onboarding.router)
    app.include_router(user_profile.router)
    # Mount only the existing production signed-media callback, without starting
    # Guardian's shared workers/providers. Preserve its body/decorator verbatim.
    import ast
    from typing import Optional
    from fastapi import HTTPException, Query
    from fastapi.responses import FileResponse
    from guardian.core.media_signing import verify_media_signature
    from guardian.core.storage import ensure_storage_base_path

    source_path = Path("guardian/guardian_api.py")
    source_tree = ast.parse(source_path.read_text())
    callbacks = [node for node in source_tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "serve_signed_media"]
    if len(callbacks) != 1:
        raise RuntimeError("Expected the existing signed-media callback")
    callback = callbacks[0]
    callback_module = ast.Module(body=[callback], type_ignores=[])
    namespace = dict(app=app, Path=Path, Optional=Optional, HTTPException=HTTPException,
                     Query=Query, FileResponse=FileResponse,
                     verify_media_signature=verify_media_signature,
                     media_storage_path=ensure_storage_base_path().resolve())
    exec(compile(callback_module, str(source_path), "exec"), namespace)
    (root / "signed-media-source.json").write_text(json.dumps({
        "source": str(source_path), "callback": callback.name,
        "ast_sha256": hashlib.sha256(ast.dump(callback, include_attributes=False).encode()).hexdigest(),
    }))
    from guardian.core.auth import ACCOUNT_SESSION_PURPOSE, issue_session_token
    # Synthetic credentials only, retained in the private task directory.
    tokens = {owner: issue_session_token(f"{owner}@example.invalid", purpose=ACCOUNT_SESSION_PURPOSE)[0]
              for owner in ("persist003-a", "persist003-b")}
    token_path = root / "tokens.json"
    token_path.write_text(json.dumps(tokens))
    token_path.chmod(0o600)
    (root / "backend-pid.json").write_text(json.dumps({"pid": os.getpid()}))
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
