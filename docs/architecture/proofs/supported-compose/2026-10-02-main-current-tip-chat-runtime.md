# Current-tip ordinary chat runtime proof

Date: 2026-10-02. Evaluated source: `1c3878697b17cfe830774870494461cc37772a68`,
local `main`, initially clean and eleven commits ahead of cached `origin/main`.
Authority: active ordinary-chat reliability Goal and Development Operator Level 0.
Classification: architecture-impact, PROOF_REQUIRED; no production code changes.
Governing contracts: ADR-001/002/003/038/069/087 and the chat runtime contract.
ADR impact: aligned; no new decision or release claim. Current-state remains HOLD.

## Environment and provenance

Project: `codexify_chat_proof_f091_20261002`, API `127.0.0.1:18888`, frontend
`127.0.0.1:15173`. This is the Goal-owned isolated project, using preserved data.
Six code participants were recreated against a Git archive of the evaluated
source: backend, frontend, chat worker, chat embedding worker, document embedding
worker, and warmup worker. PostgreSQL, Redis, Neo4j and their volumes stayed up.
Other projects and the shared Whoosh'd process were not restarted or modified.

The dependency image remained `codexify-chat-proof:f09156952`. The following
dependency inputs have no Git difference from that image's source baseline:
`pyproject.toml`, `requirements/all.txt`, `frontend/package.json`,
`frontend/package-lock.json`, `frontend/src/package.json`, `pnpm-lock.yaml`.
This is cached-dependency, refreshed-source evidence, not fresh installation or
reproducible dependency-build qualification. The normal Compose frontend startup
still runs its existing dependency installation commands against copied source.

Rendered Compose configuration was captured privately. Only source bindings were
overridden; the three data-service configurations compare equal. Frozen mounts
and SHA-256 readback prove the selected five backend source files in all five
Python participants, and the selected three frontend files in the frontend.
Participants started after binding those files; no later source repair occurred.
This is startup/mount evidence, not an introspection of Python's resident objects.

Immediately before recreation: all five relevant queues had length zero; fresh
chat heartbeat was idle; no turn-lock keys existed; PostgreSQL had no non-idle
application client sessions. The unrelated eval queue had one entry; its content
digest matched after recreation. These checks do not prove graceful drain of
active work or an atomic distributed quiescence barrier. No queue was cleared.

## Runtime outcomes

| Case | Durable identities | Observed outcome |
| --- | --- | --- |
| API ordinary chat | Thread 7; user 13; assistant 14; task `1488a306-aefc-4d93-bd0f-5f59c2048d05` | Exact marker reply, one user/assistant/attempt, `task.completed`, no turn lock. About 57.2 seconds; first token roughly 49 seconds after waiting-for-token state. |
| Unavailable explicit model | Thread 8; user 15; task `a39d84bf-8088-4860-813b-6a42d043acb8` | Accepted then `task.failed`, no assistant or fallback. Explicit synthetic model rejected as unavailable; reported execution/attempt truth false. |
| In-flight cancellation | Thread 9; user 16; task `fae2b077-abe6-4dd4-a952-b8e54b5b9ff6` | Cancel requested after visible token; `task.cancelled` in about 0.172 seconds, zero assistant rows, turn lock released. |
| Browser new-thread chat | Thread 10; user 17; assistant 18; task `6fef4bf6-8959-4af0-9e65-03c7aba28af4` | Exact assistant reply, one user/assistant/attempt, `task.completed`, no lock; **live transcript coherence failed** because the user message was absent until reload. |

Independent `psql` queries read the message content and metadata plus
`chat_completion_attempts` rows. Each attempt's request, task, thread and turn
identities agree with the task terminal event. Successful assistant IDs and
request correlation agree with persistence. Failure/cancellation threads each
have one authored user message and zero assistant messages. Redis lock checks
were zero for all four threads.

API and browser generation used provider `local`, logical model `local-chat`,
Whoosh'd inventory display `Gemma 4 12B IT QAT 4-bit`. Health/catalog reported
supported-profile-valid, local-only, no cloud configuration, and no fallback.
Health `release_hold=false` is that endpoint's runtime/configuration result; it
does not supersede the architecture qualification HOLD.

Whoosh'd request readback exposes `upstream_request_id`, not the task correlation
fields used by the first observation query. That initial query found no records
and was inconclusive. Corrected readback matched the cancellation request ID:
`whoosh-393c9667c4c541eba4642f8e2a8c5fff`, status `cancelled`, stream true,
`cancel_requested=false`. This establishes the correlated runtime's stopped
status; it does not prove a successful explicit cancel RPC rather than transport
disconnect cancellation. No foreign request was cancelled by this proof harness.

Terminal events have truthful nested final selection (`local`/`local-chat`) but
top-level `final_provider`/`final_model` are null on the two successful cases.
The operator projection consequences remain unevaluated; do not silently treat
all terminal selection fields as equivalent.

## Browser failure and reload localization

Real Playwright CLI, session `main1c-runtime`, opened the supported frontend.
An empty composer submitted `Reply with exactly: BROWSER_MAIN_1c3878697_20261002`
and navigated to `/chat/10`. After completion, the screenshot showed only the
Guardian reply. The DOM check for the complete authored prompt returned false.
PostgreSQL simultaneously proved both canonical messages. No active-generation
banner or stop action remained in the terminal snapshot.

Reloading the same URL restored both prompt and assistant, with the same IDs and
counts; no new request or authored message was submitted. This is a live
projection gap in draft-to-persisted-thread handoff, not lost durable content.
Source inspection found that the new-thread branch in `GuardianChat` activates
the empty thread before message persistence and increments a reload version
after posting; the existing-thread branch explicitly refreshes the shared
snapshot after posting. Only assistant message events enter its shared message
handler. This is a candidate causal seam requiring focused reproduction, not a
completed repair or proof that every ordering fails.

Proof stopped at this failure. No later idle-code restart, queued cancellation,
retry, unavailable-model UI, or full shutdown qualification was performed.

## Commands and artifacts

External evidence: `/private/tmp/codexify-main-runtime-1c3878697-20261002/`, mode
0700; private configuration and records mode 0600. Credentials were reused from
the earlier owned project's private environment file; no secret was committed.

Commands from the repository root:

```sh
git status --short --branch
git archive 1c3878697b17cfe830774870494461cc37772a68
git diff f09156952 HEAD -- pyproject.toml requirements/all.txt frontend/package.json frontend/package-lock.json frontend/src/package.json pnpm-lock.yaml
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py prepare
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py idle
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py refresh
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py hashes
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-main-runtime-1c3878697-20261002/api_probe.py health
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-main-runtime-1c3878697-20261002/api_probe.py cold
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-main-runtime-1c3878697-20261002/negative_probe.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-main-runtime-1c3878697-20261002/inflight_cancel_probe.py
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py readback cold
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py readback unavailable-model
python3 /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py readback inflight-cancel
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-main-runtime-1c3878697-20261002/runtime_proof.py browser-readback 10
git diff --check
```

The private `compose.sh` rendered configuration, then ran `up -d --no-deps
--no-build --pull never --force-recreate` for only the six named code services.
API probes/readback passed. Browser prompt-presence check failed before reload,
then the refreshed snapshot showed both messages. No automated runtime unit
tests apply to the committed receipt; this task gathered actual runtime proof.

Harness failures: system Python lacked Requests; reused the existing project
venv without installing dependencies. A copied credential-path replacement
initially pointed to a nonexistent file; corrected before any chat was created.
Two exploratory SQL queries assumed nonexistent attempt status/tasks schema;
schema inspection corrected the idleness/readback queries. Sandbox Chrome launch
failed at the macOS process handshake; narrow automatic-review escalation
allowed the same isolated browser launch. Favicon 404s and an existing UI warning
were observed; no full console-clean claim is made.

Evidence includes source/config provenance, idle receipts, all four event and
PostgreSQL packs, request readback, result summaries, and artifact digests.
Screenshot: `.playwright-cli/page-2026-10-02T19-53-40-599Z.png`.
DOM/reload observations: `browser-reload-observation-part1.log` through `part4.log`.
The last reload observation includes the restored prompt and assistant.

## Remaining obligation

The Goal remains incomplete. Next: reproduce and repair the live new-thread
authored-message projection gap, then rerun this actual browser/PG path. Continue
current-tip failure/retry and restart recovery proof afterward. Full reachable
deadline enforcement, terminal reserve, persistence/event failure recovery,
finite graceful drain and broader supported qualification remain unproven.
No push, merge, deployment, current-state rewrite, or memory update occurred.
