# New-thread live-state gap on the isolated candidate

Level 0 proof-only task, candidate `39e6a9736f5dbb73c61880294e2d0e367e22b6ad`, observed October 4 local / October 5 UTC. Release remains HOLD. This receipt does not change ADR-087/038/003, release truth, or the accepted parent-only FAISS snapshot/deadline policy.

## Result

One natural browser Send created thread 39, authored message 74, and assistant 75. While the exact accepted attempt was executing, the visible message region reported `data-inference-state=idle`, displayed “Response outcome unconfirmed,” and exposed no Stop control. Captured console logs showed that the displaced chat closure nevertheless attached the accepted task. The assistant eventually rendered naturally and the historical uncertainty notice disappeared.

The source exposes a concrete remount path in `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`: `PanelShell` returns a native `div` for the prompt-first landing surface and `FrameCard` after promotion. Changing the element type replaces its descendant `GuardianChat` instance. The new-thread send closure continues after `promoteDeferredThread`, starts inference, then submits completion through a 100 ms callback. Those local hook updates can therefore belong to the replaced instance. A focused component preservation regression and stable wrapper repair are the next task; this proof makes no product change and does not yet claim that repair is sufficient.

## Exact durable identity

| Field | Value |
| --- | --- |
| Request | `req_941fc460277644169187a9f4a71800ed` |
| Task | `aaae403b-edc3-405a-ac64-5f22d1a73adb` |
| Thread | `39` |
| Turn | `655f2160-bc0b-4a55-8287-563877f52c94` |
| Authored / assistant | `74` / `75` |
| Provider / model | `local` / `local-chat`, no fallback |
| Original snapshot acceptance | `2026-10-05T02:51:31.844679+00:00` |
| Work deadline | `2026-10-05T03:03:31.844679+00:00` |
| Terminal deadline | `2026-10-05T03:04:31.844679+00:00` |
| Later acceptance confirmation | `2026-10-05T02:51:31.867391+00:00` |
| Completion | `2026-10-05T02:52:15.050360+00:00` |

The exact response was `LIVE CHAT OK 20261004 39E6A9736`. PostgreSQL assistant metadata, attempt completion link, one raw `task.completed` event, and the bounded receipt agreed. Completion took 43.205681 seconds from the original snapshot acceptance. The snapshot remained unchanged; no deadline was inferred or shortened, and no replay or synthetic terminal outcome was issued.

## Validation and custody

Private evidence: `/private/tmp/codexify-chat-live-observation-39e6a9736-20261004/`, containing the Task Spec, preconditions, initial/final attempts, messages, receipts, raw events, pending/completed DOM captures, screenshots, readback driver and validation result. Browser interaction used CUA on the existing private Vite 5182 tab. API/PostgreSQL/Redis readback was read-only.

`/Volumes/Dev_SSD/Codexify-main/.venv/bin/python .../readback.py` passed. A subsequent assertion run verified the exact tuple and completion, original 720/60-second deadline, preservation of all 73 prior messages and 38 prior attempts, exactly two added messages and one attempt, and unchanged schema `f1a6d83b9024`. It rechecked all 1,140 backend/worker source hashes and both container IDs/start times/restart counts against the coherent candidate activation receipt. Chat queue and turn locks were empty afterward, the worker was idle, system queue remained 18, and evaluation queue advanced naturally 35 to 36.

No service restart, source refresh, schema change, install, download, deletion, main edit, push, merge or deployment occurred. No automated runtime test applies to this documentation-only change; `git diff --check` is the scoped document check. No release documentation was widened. The live-state defect remains open; cancellation, failure, orphan recovery, retry, restart and shutdown still need fresh supported-path proof.
