(base) resonant_jones@Christophers-MacBook-Air guardian-backend_v2 % rg -n "_require_sqlite_db\(" guardian/guardian_api.py
244:def _require_sqlite_db(feature: str) -> GuardianDB:
303:        sqlite_db = _require_sqlite_db("midterm retention prune")
670:        sqlite_db = _require_sqlite_db("chat thread creation")
698:        threads =_require_sqlite_db("chat thread listing").list_chat_threads()
716:        sqlite_db =_require_sqlite_db("chat message persistence")
750:    sqlite_db =_require_sqlite_db("chat message listing")
757:    sqlite_db =_require_sqlite_db("chat message deletion")
794:        sqlite_db =_require_sqlite_db("chat thread update")
821:        _require_sqlite_db("chat thread deletion").delete_thread(thread_id)
840:    sqlite_db = _require_sqlite_db("memory listing")
858:    sqlite_db = _require_sqlite_db("memory creation")
876:    sqlite_db = _require_sqlite_db("memory update")
891:    sqlite_db = _require_sqlite_db("memory deletion")
902:    sqlite_db = _require_sqlite_db("memory health check") if DB_BACKEND == "sqlite" else None
951:        sqlite_db =_require_sqlite_db("project update")
961:        _require_sqlite_db("project thread eviction").eject_threads_from_project(project_id)
1107:        sqlite_db = _require_sqlite_db("memory logging")
1136:        sqlite_db = _require_sqlite_db("memory summary logging")
1169:        rows =_require_sqlite_db("memory search").search_memory(query, limit)
1236:        rows =_require_sqlite_db("history listing").history_entries(limit=limit, tag=tag, agent=agent)
1344:    sqlite_db = _require_sqlite_db("thread lookup")
1364:    rows =_require_sqlite_db("child thread listing").get_child_threads(thread_id)
1384:    summary =_require_sqlite_db("thread summary lookup").get_thread_summary(thread_id)
1394:    thread_id = _require_sqlite_db("thread creation").create_thread(
1504:        _require_sqlite_db("prompt logging").insert_memory(
1566:            _require_sqlite_db("groq reply logging").insert_memory(
1592:            _require_sqlite_db("gemini reply logging").insert_memory(
1660:    profile = _require_sqlite_db("agent profile lookup").get_agent_profile(agent_id)
1674:    _require_sqlite_db("agent profile update").upsert_agent_profile(agent_id, **updates)
1690:    _require_sqlite_db("agent frequency update").upsert_agent_profile(agent_id, summarization_frequency=frequency)
1704:    allowed, msg =_require_sqlite_db("agent summarization check").check_summarization_allowed(agent_id, requested_by)
1782:    history = _require_sqlite_db("chat history retrieval").get_chat_history(
1800:    history =_require_sqlite_db("chat history summarization").get_chat_history(
(base) resonant_jones@Christophers-MacBook-Air guardian-backend_v2 %

(base) resonant_jones@Christophers-MacBook-Air guardian-backend_v2 % rg -n '\.\w+\(' guardian/guardian_api.py | grep -v "_require_sqlite_db"
55:    logging.warning(f"[Codexify ⚠️] Optional chat_with_ai module not available: {e}")
64:    logging.warning(f"[Codexify ⚠️] Optional groq_client not available: {e}")
70:logging.basicConfig(level=logging.INFO)
71:logger = logging.getLogger(__name__)
79:    cwd = Path(__file__).resolve().parents[1]
81:    mode = os.getenv("GUARDIAN_ENV", "development").strip()
87:        if p.exists():
90:            loaded.append(str(p))
91:    logger.info(
93:        " -> ".join(loaded) if loaded else "<none>"
99:API_KEY = os.getenv("GUARDIAN_API_KEY", "changeme")
101:logger.info("[auth] Using GUARDIAN_API_KEY=%s", _mask)
108:        logger.warning("Unauthorized attempt with API key")
114:GEMINI_API_URL = os.getenv("GEMINI_API_URL", "<https://api.gemini.ai/v1/chat>")
115:GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")
118:GUARDIAN_PROVIDER = os.getenv("GUARDIAN_PROVIDER", "gemini").lower()
119:GROQ_API_KEY = os.getenv("GROQ_API_KEY")
120:GROQ_MODEL_DEFAULT = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
125:    processor = BlipProcessor.from_pretrained(
130:    logging.warning(f"Fast BLIP processor unavailable, falling back to slow: {e}")
131:    processor = BlipProcessor.from_pretrained(
135:vision_model = BlipForConditionalGeneration.from_pretrained(
142:_ENABLE_MONDREAM = os.getenv("GUARDIAN_ENABLE_MONDREAM", "0").lower() in ("1", "true", "yes")
146:    mondream_dir = Path(__file__).resolve().parents[1] / "models" / "mondream1"
147:    repo_spec = str(mondream_dir) if mondream_dir.exists() else "vikhyatk/mondream1"
149:        mondream_processor = AutoProcessor.from_pretrained(
153:        mondream_model = AutoModelForVision2Seq.from_pretrained(
157:        logger.info("Mondream model loaded")
159:        logging.warning(f"Failed to load Mondream model: {e}")
166:    gray = pil_img.convert("L")
167:    arr = np.array(gray)
173:        if arr[i, :].max() > threshold:
180:        if arr[i, :].max() > threshold:
187:        if arr[:, j].max() > threshold:
194:        if arr[:, j].max() > threshold:
203:    return pil_img.crop((left, top, right, bottom))
208:PG_DSN = os.getenv("GUARDIAN_DB_URL") or os.getenv("DATABASE_URL")
209:DB_PATH = os.getenv("GUARDIAN_DB_PATH")  # may be "__DISABLE_SQLITE__"
217:        pg_pool = psycopg.ConnectionPool(PG_DSN)      # global pool
238:logger.info("📦 DB backend selected: %s", DB_BACKEND)
257:            with psycopg.connect(PG_DSN) as conn:  # type: ignore[arg-type]
258:                with conn.cursor() as cur:
259:                    cur.execute("SELECT id FROM projects WHERE name=%s", ("Loose Threads",))
260:                    row = cur.fetchone()
262:                        cur.execute(
266:                        conn.commit()
267:                        logger.info("[projects] Created default 'Loose Threads' project (pg)")
269:            with sqlite3.connect(SQLITE_PATH) as conn:
270:                c = conn.cursor()
271:                c.execute("SELECT id FROM projects WHERE name = ?", ("Loose Threads",))
272:                row = c.fetchone()
274:                    c.execute(
278:                    conn.commit()
279:                    logger.info("[projects] Created default 'Loose Threads' project (sqlite)")
281:        logger.warning("[projects] Failed to ensure Loose Threads project: %s", e)
286:MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))
290:    cutoff = (datetime.utcnow() - timedelta(days=MEMORY_RETENTION_DAYS)).isoformat()
292:        with psycopg.connect(PG_DSN) as conn:  # type: ignore[arg-type]
293:            with conn.cursor() as cur:
294:                cur.execute(
300:                    logger.info("[memory] pruned %d expired midterm entries", pruned)
301:                conn.commit()
304:        pruned = sqlite_db.prune_midterm(cutoff)
306:            logger.info("[memory] pruned %d expired midterm entries", pruned)
308:    logger.debug("[memory] prune skipped: %s",_e)
314:app.include_router(threads.router, prefix="/threads")
315:app.include_router(research.router, prefix="/research")
316:app.include_router(memory.router, prefix="/memory")
317:app.include_router(agent.router, prefix="/agent")
318:app.include_router(codexify_router)
322:_origins_env = os.getenv("GUARDIAN_ALLOWED_ORIGINS", "<http://localhost:5173>")
323:allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
326:app.add_middleware(
352:@app.post("/tools/execute", response_model=ToolResponse, tags=["Tools"])
362:    logger.info("Tools.execute: %s job_id=%s", body.name, jid)
373:    cid = connector_id.upper()
381:        if os.getenv(k):
386:    return connector_id.replace("_", " ").title()
390:    raw = os.getenv("GUARDIAN_CONNECTORS", "google_drive,github")
391:    ids = [c.strip() for c in raw.split(",") if c.strip()]
394:        out.append({
438:@app.get("/api/connectors", tags=["Connectors"])
441:    logger.info("[connectors] GET /api/connectors count=%d", len(CONNECTORS))
444:        cid = c.get("id")
445:        meta = CONNECTOR_REGISTRY.get(cid, {"requiredFields": [], "capabilities": {}})
446:        cfg = CONNECTOR_CONFIGS.get(cid, {})
449:        for f in meta.get("requiredFields", []):
450:            if f.get("secret") and not CONNECTOR_SECRETS.get(cid, {}).get(f["key"]):
453:        oc.update({
454:            "capabilities": meta.get("capabilities"),
455:            "requiredFields": meta.get("requiredFields"),
456:            "scopes": meta.get("scopes", []),
457:            "options": meta.get("options", []),
460:        out.append(oc)
463:@app.patch("/api/connectors/{connector_id}", tags=["Connectors"])
470:    unknown = [k for k in updates.keys() if k not in allowed]
472:        logger.warning("[connectors] PATCH unknown fields id=%s fields=%s", connector_id, unknown)
473:        raise HTTPException(status_code=400, detail={"error": f"Unknown fields: {', '.join(unknown)}"})
476:        if c.get("id") == connector_id:
477:            before_status = c.get("status")
481:            logger.info("[connectors] PATCH id=%s status=%s->%s", connector_id, before_status, c.get("status"))
486:@app.get("/api/connectors/{connector_id}", tags=["Connectors"])
489:        if c.get("id") == connector_id:
490:            meta = CONNECTOR_REGISTRY.get(connector_id, {})
491:            cfg = CONNECTOR_CONFIGS.get(connector_id, {})
493:            for f in meta.get("requiredFields", []):
494:                if f.get("secret") and not CONNECTOR_SECRETS.get(connector_id, {}).get(f["key"]):
497:                "capabilities": meta.get("capabilities"),
498:                "requiredFields": meta.get("requiredFields", []),
499:                "scopes": meta.get("scopes", []),
500:                "options": meta.get("options", []),
502:                "config": {k: ("••••" if any(f.get("key") == k and f.get("secret") for f in meta.get("requiredFields", [])) else v) for k, v in {**cfg,**CONNECTOR_SECRETS.get(connector_id, {})}.items()},
507:@app.post("/api/connectors/{connector_id}/config", tags=["Connectors"])
509:    meta = CONNECTOR_REGISTRY.get(connector_id)
512:    fields = body.get("fields", {})
513:    allowed = {f["key"]: f for f in meta.get("requiredFields", [])}
514:    unknown = [k for k in fields.keys() if k not in allowed]
516:        logger.warning("[connectors] CONFIG unknown keys id=%s fields=%s", connector_id, unknown)
517:        return JSONResponse(status_code=400, content={"ok": False, "error": f"Unknown fields: {', '.join(unknown)}"})
519:    cfg = CONNECTOR_CONFIGS.setdefault(connector_id, {})
520:    sec = CONNECTOR_SECRETS.setdefault(connector_id, {})
521:    for k, v in fields.items():
522:        if allowed[k].get("secret"):
526:    logger.info("[connectors] CONFIG id=%s updated keys=%s", connector_id, list(fields.keys()))
528:    masked = {k: ("••••" if allowed[k].get("secret") else v) for k, v in {**cfg,**sec}.items() if k in allowed}
531:@app.post("/api/connectors/github/authorize", tags=["Connectors"])
534:    redirect_uri = body.get("redirectUri")
537:    client_id = CONNECTOR_CONFIGS.get(cid, {}).get("client_id") or os.getenv("GITHUB_CLIENT_ID")
543:        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
544:    code_verifier = b64url(secrets.token_bytes(32))
545:    challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())
546:    state = b64url(secrets.token_bytes(16))
547:    AUTH_TX[state] = {"connector_id": cid, "code_verifier": code_verifier, "redirect_uri": redirect_uri, "ts": datetime.utcnow().isoformat()}
553:    logger.info("[connectors] AUTHORIZE id=github state=%s", state)
556:@app.get("/api/connectors/github/callback", tags=["Connectors"])
558:    tx = AUTH_TX.pop(state, None)
562:    CONNECTOR_SECRETS.setdefault["github", {}]("access_token") = "gho_simulated"
567:    logger.info("[connectors] CALLBACK id=github state=%s ok", state)
571:@app.post("/api/connectors/{connector_id}/test", tags=["Connectors"])
574:        ok = bool(CONNECTOR_SECRETS.get("github", {}).get("access_token"))
578:@app.post("/api/connectors/{connector_id}/sync", tags=["Connectors"])
582:    logger.info("[connectors] SYNC id=%s job_id=%s", connector_id, jid)
585:@app.get("/health/connectors", tags=["Connectors"])
588:    connected = sum(1 for c in CONNECTORS if c.get("status") == "connected")
591:@app.get("/jobs/{job_id}", tags=["Tools"])
593:    job = JOBS.get(job_id, {})
594:    status = job.get("status", "unknown")
596:    last_error = job.get("error") if status == "error" else None
612:        self.subscribers.append(queue)
618:            self.subscribers.remove(queue)
625:            "timestamp": datetime.utcnow().isoformat()
631:                queue.append(event_data)
633:                dead_subscribers.append(queue)
637:            self.unsubscribe(queue)
648:@app.post("/api/chat/threads", tags=["Chat"])
653:        raw_title = payload.get("title")
654:        title = (str(raw_title).strip() if raw_title is not None else "New Chat") or "New Chat"
655:        raw_user = payload.get("user_id")
657:        raw_summary = payload.get("summary")
658:        summary = str(raw_summary).strip() if raw_summary is not None else ""
659:        project_id = payload.get("project_id")
673:        recent_thread = sqlite_db.get_recent_thread(user_id)
676:            recent_id = recent_thread.get("id")
677:            if recent_id and sqlite_db.count_messages(recent_id) == 0:
678:                logger.info("Reusing recent empty thread %s for user %s", recent_id, user_id)
681:        record = sqlite_db.create_chat_thread(
687:        sqlite_db.write_audit_log("create", "chat_thread", str(record["id"]), user_id=user_id)
690:        logger.exception("Failed to create chat thread: %s", exc)
694:@app.get("/api/chat/threads", tags=["Chat"])
701:        logger.exception("Failed to list chat threads: %s", exc)
708:@app.post("/api/chat/{thread_id}/messages")
710:    role = body.get("role")
711:    content = body.get("content", "").strip()
714:    owner = body.get("user_id") or "default"
717:        sqlite_db.ensure_chat_thread(
725:        logger.exception("Failed to ensure chat thread %s exists: %s", thread_id, exc)
727:    mid = sqlite_db.create_message(thread_id, role, content)
728:    sqlite_db.write_audit_log("create", "chat_message", str(mid), user_id=str(owner))
731:    event_manager.emit("message.created", {
748:@app.get("/api/chat/{thread_id}/messages")
751:    items = sqlite_db.list_messages(thread_id, limit=limit, offset=offset)
752:    total = sqlite_db.count_messages(thread_id)
755:@app.delete("/api/chat/{thread_id}/messages/{message_id}")
758:    sqlite_db.delete_message(thread_id, message_id)
759:    sqlite_db.write_audit_log("delete", "chat_message", str(message_id), user_id="default")
766:@app.patch("/api/chat/threads/{thread_id}", tags=["Chat"])
775:        raw_title = body.get("title")
776:        title = (str(raw_title).strip() if raw_title is not None else "") or "New Chat"
779:        raw_summary = body.get("summary")
780:        summary = str(raw_summary).strip() if raw_summary is not None else ""
782:    project_id = body.get("project_id") if "project_id" in body else None
795:        existing = sqlite_db.get_chat_thread(thread_id)
799:        updated = sqlite_db.update_thread(
808:        refreshed = sqlite_db.get_chat_thread(thread_id)
810:            sqlite_db.write_audit_log("update", "chat_thread", str(thread_id), user_id=refreshed.get("user_id", "default"))
815:        logger.exception("Failed to update chat thread %s: %s", thread_id, exc)
818:@app.delete("/api/chat/threads/{thread_id}")
833:@app.get("/api/memory/{silo}")
841:    items = sqlite_db.list_memories(silo, limit=limit, offset=offset)
842:    count = sqlite_db.count_memories(silo)
845:@app.post("/api/memory/{silo}")
849:    content = str(body.get("content", "")).strip()
850:    tags = ",".join(body.get("tags", []) or [])
851:    pinned = bool(body.get("pinned", False))
855:        entry = {"id": len(EPHEMERAL_MEMORY) + 1, "user_id": "default", "silo": "ephemeral", "content": content, "tags": tags, "pinned": pinned, "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat()}
856:        EPHEMERAL_MEMORY.append(entry)
859:    eid = sqlite_db.add_memory("default", silo, content, tags=tags, pinned=pinned)
860:    sqlite_db.write_audit_log("create", "memory_entry", str(eid), user_id="default")
863:@app.patch("/api/memory/{silo}/{entry_id}")
869:            if e.get("id") == entry_id:
871:                if "tags" in body: e["tags"] = ",".join(body.get("tags", []) or [])
873:                e["updated_at"] = datetime.utcnow().isoformat()
877:    sqlite_db.update_memory(entry_id, content=body.get("content"), tags=",".join(body.get("tags", []) or []) if body.get("tags") is not None else None, pinned=body.get("pinned") if body.get("pinned") is not None else None)
878:    sqlite_db.write_audit_log("update", "memory_entry", str(entry_id), user_id="default")
881:@app.delete("/api/memory/{silo}/{entry_id}")
886:        idx = next((i for i, e in enumerate(EPHEMERAL_MEMORY) if e.get("id") == entry_id), -1)
888:            EPHEMERAL_MEMORY.pop(idx)
892:    sqlite_db.delete_memory(entry_id)
893:    sqlite_db.write_audit_log("delete", "memory_entry", str(entry_id), user_id="default")
900:@app.get("/health/memory")
907:            "midterm": sqlite_db.count_memories("midterm") if sqlite_db else None,
908:            "longterm": sqlite_db.count_memories("longterm") if sqlite_db else None,
912:@app.get("/health/chat")
918:            with psycopg.connect(PG_DSN) as conn:  # type: ignore[arg-type]
919:                with conn.cursor() as cur:
920:                    cur.execute("SELECT COUNT(_) FROM chat_messages")
921:                    messages = int(cur.fetchone()[0])
922:                    cur.execute("SELECT COUNT(_) FROM chat_threads")
923:                    threads = int(cur.fetchone()[0])
925:            with sqlite3.connect(SQLITE_PATH) as conn:
926:                c = conn.cursor()
928:                    c.execute("SELECT COUNT(_) FROM chat_messages")
929:                    messages = int(c.fetchone()[0])
933:                    c.execute("SELECT COUNT(_) FROM chat_threads")
934:                    threads = int(c.fetchone()[0])
936:                    c.execute("SELECT COUNT(DISTINCT thread_id) FROM chat_messages")
937:                    threads = int(c.fetchone()[0])
939:        logger.warning("[health/chat] check failed: %s", _e)
946:@app.patch("/projects/{project_id}")
948:    name = body.get("name")
949:    description = body.get("description")
952:        sqlite_db.update_project(project_id, name=name if name is not None else None, description=description if description is not None else None)
957:@app.delete("/projects/{project_id}")
963:        logger.warning("eject threads failed: %s", e)
967:            with psycopg.connect(PG_DSN) as conn:  # type: ignore[arg-type]
968:                with conn.cursor() as cur:
969:                    cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
970:                    conn.commit()
972:            with sqlite3.connect(SQLITE_PATH) as conn:
973:                c = conn.cursor()
974:                c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
975:                conn.commit()
1020:@app.get("/ping", summary="Health check endpoint", tags=["Memory"])
1025:    logger.debug("Ping request received")
1032:@app.get("/authz/debug", tags=["Diag"], summary="Echo masked API key received in header")
1040:@app.get("/healthz", tags=["Diag"], summary="DB health and table existence")
1050:            with psycopg.connect(PG_DSN) as conn:  # type: ignore[arg-type]
1051:                with conn.cursor() as cur:
1052:                    cur.execute("SELECT to_regclass('public.projects')")
1053:                    projects_exists = cur.fetchone()[0] is not None
1054:                    cur.execute("SELECT to_regclass('public.chat_threads')")
1055:                    threads_exists = cur.fetchone()[0] is not None
1057:            with sqlite3.connect(SQLITE_PATH) as conn:
1058:                c = conn.cursor()
1059:                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
1060:                projects_exists = c.fetchone() is not None
1061:                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_threads'")
1062:                threads_exists = c.fetchone() is not None
1064:        logger.warning("/healthz check failed: %s", e)
1074:@app.get("/debug/config", tags=["Diag"], summary="Return masked config for debugging (development only)")
1080:    env = os.getenv("GUARDIAN_ENV", "development")
1094:@app.post("/log", summary="Log a command entry", tags=["Memory"])
1105:    timestamp = datetime.now().isoformat()
1108:        sqlite_db.insert_memory(
1116:        logger.info(f"Log entry stored: {entry.command}")
1118:        logger.error(f"Failed to store log entry: {e}")
1123:@app.post("/summarize", summary="Store a summary entry", tags=["Memory"])
1134:    timestamp = datetime.now().isoformat()
1137:        sqlite_db.insert_memory(
1145:        logger.info(f"Summary entry stored for parent_id {entry.parent_id}")
1147:        logger.error(f"Failed to store summary entry: {e}")
1152:@app.get("/search", summary="Search memory entries", tags=["Memory"])
1179:        logger.info(
1183:        logger.error(f"Search failed: {e}")
1188:@app.get(
1226:            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
1228:            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
1230:        logger.error(f"Invalid date format in history filters: {ve}")
1239:            entry_dt = datetime.fromisoformat(r["timestamp"])
1244:            filtered_rows.append(r)
1254:        logger.info(
1258:        logger.error(f"Failed to retrieve history entries: {e}")
1277:@app.get("/threads", summary="List all threads", tags=["Threads"])
1295:                params.append(user_id)
1298:                params.append(project_id)
1300:            with psycopg.connect(PG_DSN) as conn:  # type: ignore[arg-type]
1301:                with conn.cursor() as cur:
1302:                    cur.execute(query, tuple(params))
1303:                    rows = cur.fetchall()
1314:                params.append(user_id)
1317:                params.append(project_id)
1319:            with sqlite3.connect(SQLITE_PATH) as conn:
1320:                c = conn.cursor()
1321:                c.execute(query, params)
1322:                rows = c.fetchall()
1328:        if "no such table" in str(e).lower():
1330:        logger.exception("Thread listing failed")
1335:        logger.exception("Thread listing failed")
1339:@app.get("/thread/{thread_id}", summary="Get thread details", tags=["Threads"])
1345:    row = sqlite_db.get_thread(thread_id)
1359:@app.get("/thread/{thread_id}/children", summary="List child threads", tags=["Threads"])
1379:@app.get("/thread/{thread_id}/summary", summary="Get thread summary", tags=["Threads"])
1388:@app.post("/thread", summary="Create a new thread", tags=["Threads"], status_code=201)
1404:@app.post("/threads", summary="Create a new thread (alias of /thread)", tags=["Threads"], status_code=201)
1417:@app.post("/projects", summary="Create a project", tags=["Projects"], status_code=201)
1424:        logger.exception("Failed to create project")
1426:        env = os.getenv("GUARDIAN_ENV", "development")
1431:@app.get("/projects", summary="List projects", tags=["Projects"])
1437:                "id": r.get("id") if isinstance(r, dict) else getattr(r, "id", None),
1438:                "name": r.get("name") if isinstance(r, dict) else getattr(r, "name", None),
1439:                "description": (r.get("description") if isinstance(r, dict) else getattr(r, "description", "")) or "",
1440:                "created_at": r.get("created_at") if isinstance(r, dict) else getattr(r, "created_at", None),
1446:        logger.exception("Failed to list projects")
1449:@app.delete("/projects/{project_id}", summary="Delete a project", tags=["Projects"])
1454:        logger.exception("Failed to delete project %s", project_id)
1466:@app.get("/", summary="Gemini proxy status", tags=["Gemini Proxy"])
1471:    logger.debug("Gemini status check requested")
1475:@app.get("/test", summary="Gemini proxy test endpoint", tags=["Gemini Proxy"])
1480:    logger.debug("Gemini test endpoint called")
1485:@app.post(
1505:            timestamp=datetime.now().isoformat(),
1513:        logger.debug(f"Prompt log failed (non-fatal): {e}")
1519:            if f.content_type.startswith("image/"):
1521:                data = f.file.read()
1522:                img = Image.open(BytesIO(data)).convert("RGB")
1524:                if caption_model.lower() == "mondream" and mondream_processor and mondream_model:
1527:                    enc = mondream_model.encode_image(**inputs)
1528:                    answer = mondream_model.answer_question(
1533:                    captions.append(answer.strip())
1537:                    outputs = vision_model.generate(**inputs)
1538:                    caption = processor.decode(outputs[0], skip_special_tokens=True)
1539:                    captions.append(caption)
1543:                + "\n".join(f"- {c}" for c in captions)
1557:        real_model = raw_model.split[":", 1](-1)
1561:            logger.error(f"Error contacting Groq API: {e}")
1567:                timestamp=datetime.now().isoformat(),
1575:            logger.debug(f"Reply log failed (non-fatal): {e}")
1586:        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30)
1587:        response.raise_for_status()
1588:        data = response.json()
1589:        reply_text = data.get("reply", "")
1593:                timestamp=datetime.now().isoformat(),
1601:            logger.debug(f"Reply log failed (non-fatal): {e}")
1603:        logger.info("Chat interaction logged successfully")
1606:        logger.error(f"HTTP error contacting Gemini API: {http_err}")
1609:        logger.error(f"Error contacting Gemini API: {e}")
1614:@app.get("/chat/stream", summary="Stream chat tokens from active provider", tags=["Chat"])
1625:    provider = (provider or GUARDIAN_PROVIDER).lower()
1634:    real_model = raw_model.split[":", 1](-1)
1638:            for token in gc.stream(prompt, real_model):  # type: ignore[union-attr]
1640:                if await request.is_disconnected():
1644:            response = requests.post(
1649:            response.raise_for_status()
1650:            reply = response.json().get("reply", "")
1655:@app.get("/whoami", summary="Get agent profile and identity", tags=["Agent"])
1666:@app.post("/profile", summary="Update agent profile fields", tags=["Agent"])
1678:@app.post(
1694:@app.get(
1708:@app.post(
1725:    planner = Planner(**config.get("planner", {}))
1726:    agents = [Agent(**a) for a in config.get("agents", [])]
1728:    report = asyncio.run(generate_report(query, planner, agents))
1736:@app.get("/api/events", tags=["Events"])
1743:        queue = event_manager.subscribe()
1748:                    event = queue.pop(0)
1749:                    yield f"data: {json.dumps(event)}\n\n"
1752:                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
1755:                await asyncio.sleep(0.1)
1758:                if await request.is_disconnected():
1763:            event_manager.unsubscribe(queue)
1772:@app.get("/history/v2", summary="Retrieve chat log history (v2)", tags=["Memory"])
1790:@app.post("/summarize/v2", summary="Summarize chat log history (v2)", tags=["Memory"])
1810:        if row.get("role") == "user" and row.get("message"):
1811:            messages.append({"role": "user", "content": row["message"]})
1812:        elif row.get("role") == "assistant" and row.get("response"):
1813:            messages.append({"role": "assistant", "content": row["response"]})
(base) resonant_jones@Christophers-MacBook-Air guardian-backend_v2 %
Scra
