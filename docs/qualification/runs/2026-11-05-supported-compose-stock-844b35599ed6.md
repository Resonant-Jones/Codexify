# Stock Compose runtime qualification — 844b35599ed6 — 2026-11-05

- Rubric: ../rubrics/supported-compose-stock.md
- Rubric version: 1
- Verdict: PASS
- Date: 2026-11-05 (America/New_York)
- Tester: automated architecture-impact qualification agent
- Evaluated source: 844b35599ed67123ed7e6434bb4a302728ef52b2
- Runtime profile: v1-local-core-web-mcp
- Startup: stock Docker Compose, without the source-matched launcher
- Provider/model inventory: local / local-chat (Whoosh'd)

## Qualification metadata

```yaml qualification-metadata
qualification_id: supported-compose-stock
rubric_version: 1
verdict: PASS
commit: 844b35599ed67123ed7e6434bb4a302728ef52b2
date: 2026-11-05
tester_alias: stock-compose-runtime-qualification
tester_kind: automated
assistance_level_peak: 0
evidence:
  - docs/architecture/proofs/supported-compose/2026-11-05-supported-compose-stock-844b35599ed6.md
```

## Scope and result

This is one integrated stock-startup execution of the supported
`v1-local-core-web-mcp` profile at the named local revision, in a disposable
Compose project with its own network, volumes, container names and host ports.
The source-matched launcher was not invoked, no launcher-produced
`src-<sha12>` image was resolved, and no shared production tag was replaced
or re-pointed. The Private Preview lane was verified unmodified before and
after.

Every required check was exercised and passed:

- the source-head migration contract on the stock path — the migrator's own
  coherence proof passed at 135 revisions, the migrator exited 0, and the live
  `alembic_version`, read **directly out of PostgreSQL** rather than from a
  container exit code, was the evaluated checkout's single head `a7d4c9e2f1b3`
  with exactly one row;
- health and inventory, with the supported profile `valid: true` and an empty
  mismatch list;
- ordinary chat, durably read back with a native origin assertion on every
  message and a terminal outcome recorded for every accepted completion,
  including the failures;
- **document ingestion and retrieval** — the shared Chroma collection was
  created at the configured model's own dimension (1024), the document
  embedded to `ready`, and the ingested content reached the model's answer;
- explicit model authority — an explicitly requested unavailable model failed
  closed before provider execution, persisted no assistant message, and
  recorded `task.failed` on the durable attempt;
- browser projection — a real browser rendered the thread, the terminal state
  converged in the UI, and a reload preserved the projected state;
- restart recovery — the backend restarted and returned healthy with all
  durable state intact.

No blocking criterion occurred.

**This receipt supersedes the 2026-11-05 run at `456da46b8`, whose verdict was
`FAIL`.** That run failed document ingestion and retrieval because the shared
collection was created at dimension 384 while the configured local embedder
produces 1024. The defect, its mechanism and its repair are recorded rather
than edited away: the FAIL receipt and its proof remain in the repository, and
the repair derives the embedding dimension from the configured model and stops
the vector health probe from writing into the shared collection.

## Check matrix

| Check | Result | Assistance | Evidence | Notes |
| --- | --- | ---: | --- | --- |
| 1. Supported topology and startup | PASS | 0 | proof §4 | All seven required services healthy/running; `docker compose config --quiet` succeeded; every application service resolved the same image `sha256:54721b1c05e…`; no cloud credential carried; empty egress allowlist. |
| 1. Migrations applied at the source head | PASS | 0 | proof §4 | Migrator exit 0; coherence proof passed at 135 revisions; live `alembic_version` = `a7d4c9e2f1b3`, exactly one row, read directly from PostgreSQL. |
| 2. Health and inventory | PASS | 0 | proof §5 | `/ping`, `/health` (`release_hold: false`, profile `valid: true`, no mismatches), `/health/llm` (local, authorized, available, `local-chat`). |
| 3. Ordinary chat and durable readback | PASS | 0 | proof §6 | Assistant message `WOMBATS-77` persisted with a native origin assertion; attempt linked by `completed_message_id`; `task.running` → `message.created` → `task.completed` recorded. Two cold-start completions failed closed and were surfaced by the UI as "2 earlier response tasks failed." |
| 4. Document ingestion and retrieval | PASS | 0 | proof §7 | Collection created at 1024; document embedded to `ready`; the ingested identifier was returned in the model's answer. |
| 5. Explicit model authority | PASS | 0 | proof §8 | Failed before provider execution; no substitute executed; no assistant message persisted; durable attempt recorded `task.failed`. |
| 6. Browser projection | PASS | 0 | proof §9 | Real browser rendered the thread; terminal state converged; reload preserved it. A direct browser health fetch to `localhost` fails on IPv6-first resolution and leaves a "Backend connection delayed" banner — recorded as a known limitation outside this check's criteria. |
| 7. Restart recovery | PASS | 0 | proof §10 | Backend restarted and returned healthy; both messages and the document's `ready` status survived. |

## Known limitations observed, not silently repaired

- The WebUI's direct health fetch to `http://localhost:18999/health` fails in the
  browser with `net::ERR_FAILED`: the backend binds IPv4-only while Chromium
  resolves `localhost` to `::1` first. The UI shows a persistent "Backend
  connection delayed" banner although the backend is healthy and the chat
  projection is unaffected. This is outside the required criteria of check 6
  and does not invalidate it, but it is a real operator-visible defect.
- `/api/voice/capabilities`, `/api/codex/entries` and `/api/ui/session`
  returned 404 in the browser. These are routes the supported profile
  quarantines, so the 404 is the expected posture, not a failure.

## Evidence and release boundary

- [Detailed runtime proof](../../architecture/proofs/supported-compose/2026-11-05-supported-compose-stock-844b35599ed6.md)
- The image was assembled from a base built by the same repository
  `backend/Dockerfile` under BuildKit, plus this revision's `guardian/` and
  `backend/` trees overlaid verbatim. The image's baked migration source
  (`versions/*.py` and `env.py`) and its `run_migrator.py` were verified
  byte-identical to the evaluated checkout by SHA-256 **inside the image**,
  before any startup was judged. The proof does not claim the image is
  byte-identical to a from-scratch build of the repository Dockerfile on this
  date.
- Registry output is generated by `scripts/qualification/generate_registry.py`
  and validated by `scripts/qualification/validate_registry.py`.
- This receipt qualifies only the `supported-compose-stock` surface. It never
  qualifies `supported-compose` (the source-matched path) or
  `onboarding-and-people`. A receipt for one surface never qualifies another.
- **Release remains HOLD.** This receipt is evidence for one surface, not a
  release decision.
