# Preserve new-thread live inference through panel promotion

Level 0 bounded repair and browser proof, starting at `f7d313a7fa18b71f70bee526baf5cce8ec0a8e37`. Release remains HOLD. Governing ADR-003/038/087 are unchanged; this restores observation of the existing accepted request rather than creating request, provider, deadline, persistence or vector authority.

## Change and regression

Promoting a prompt-first draft changed `PanelShell` from a native `div` to `FrameCard`, replacing the descendant `GuardianChat` instance. The displaced send closure continued to request completion, while the replacement instance rendered idle and treated the pending task as historical uncertainty. The preceding proof receipt records that defect.

`GuardianChatWithSidebar.tsx` now keeps `FrameCard` across promotion. `FrameCard.tsx` provides an `unframed` visual mode that suppresses its own chrome while retaining the content topology. Direct-child selectors leave nested framed cards intact. Normal conversation chrome remains the default. The sidebar regression verifies that draft promotion retains the exact chat DOM node; it failed before the repair and passes afterward. A FrameCard regression verifies preserved draft input and nested-card identity across the visual transition.

Files changed: those two components, their stability/FrameCard tests, and this receipt. No new ADR or canonical token was required. Release-current-state and broader qualification documentation are explicitly deferred until the full gate is proven.

## Fresh source-verified browser turn

The real browser showed the authored prompt, “Working…” and an enabled Stop button after new-thread promotion. Later observation showed the model awaiting its first token with Stop still present. It then displayed Completed and the exact canonical assistant response without reload. Reload preserved the authored/assistant transcript.

| Field | Value |
| --- | --- |
| Thread | `42` |
| Request | `req_b85dbceda2fc4442a9f39c0546b415a2` |
| Task | `f3af3d46-8d97-44b5-a201-5586aadf27d9` |
| Turn | `26f24812-e185-42a5-8c55-85a12113bdc3` |
| Authored / assistant | `80` / `81` |
| Exact reply | `VERIFIED PANEL OK 20261004 F7D313A7F` |
| Provider / model | `local` / `local-chat`, no fallback |
| Original snapshot acceptance | `2026-10-05T03:05:03.553700+00:00` |
| Work deadline | `2026-10-05T03:17:03.553700+00:00` |
| Terminal deadline | `2026-10-05T03:18:03.553700+00:00` |
| Completion elapsed | `36.465437` seconds |

PostgreSQL assistant metadata and attempt link, the single raw `task.completed` event, and the bounded receipt agreed on this identity. The original non-sliding 720/60-second snapshot remained unchanged. Stop visibility is proven; its cancellation effect was deliberately not exercised in this success task.

## Validation and source custody

Private root: `/private/tmp/codexify-chat-panel-continuity-f7d313a7f-20261004/`. It contains the Task Spec, failing pre-repair regression log, passing test report, source hashes and served-transform checks, initial/final readback, raw events, DOM snapshots, screenshots and assertion driver.

- `.../.venv/bin/python .../run-regression.py`: failed before repair at the exact chat-node continuity assertion, as expected.
- `.../.venv/bin/python .../run-frontend.py`: passed 199 tests across sidebar stability, FrameCard, terminal projection, chat turn-lock lifecycle and inference-state suites. Existing dependencies and verified LFS payloads were reused in private scratch; no install or download. React act warnings remain diagnostic output, not failed assertions.
- `.../.venv/bin/python .../readback.py` and `.../.venv/bin/python .../validate.py`: passed exact completion/identity/deadline, record preservation, source, schema, container lifecycle, queue and lock checks.
- `git diff --check`: passed. Full frontend lint was not rerun; its previously recorded missing-plugin limitation remains outside this task.

An initial frontend refresh was insufficient: direct HTTP inspection proved the still-live owned Vite process served old cached transforms despite updated files on disk. Threads 40 and 41 completed on that stale source and are **not repair evidence**. Their records were preserved and validated. Only the verified owned Vite PID was stopped; a fresh owned server on localhost 5182 served the tested private source. Both repair markers were verified over HTTP before thread 42, and the browser's landing DOM showed the new unframed card. This was a frontend proof-server refresh, not a backend/worker restart or task recovery.

Validation preserved all 75 prior messages and 39 prior attempts, accounted for exactly six new messages/three attempts across the three natural requests, matched 685 frontend source files against the frozen baseline plus scoped changes, and matched all 1,140 backend/worker source hashes. Schema `f1a6d83b9024`, backend/worker IDs/start times/restart counts, system queue 18 and runtime bindings remained unchanged. Afterward the worker was idle, chat queue and turn locks were empty, and evaluation queue advanced naturally 36 to 39.

No main mutation, push, merge, deployment, backend source refresh, schema migration, data deletion, queue cleanup, shortened deadline, synthetic outcome or replay occurred. Parent-only mutable FAISS authority and bounded read-only search snapshots remain intact. The Goal stays active: fresh cancellation, explicit-model/provider failure, orphan fencing/retry, restart and shutdown evidence is still required. This receipt proves one branch-local successful live-observed turn, not complete supported-Compose qualification.
