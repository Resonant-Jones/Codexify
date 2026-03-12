

# Beta Smoke Test

## Purpose

This document defines the minimum release-gate smoke test for the current Codexify beta milestone.

It validates only the presently supported release path:
- local single-node deployment
- Docker Compose runtime
- WebUI-first interaction model
- core thread chat + worker-backed completion loop
- document upload, embedding, and retrieval happy path

This is not a full QA plan. It is the short, repeatable release-truth check for whether the current beta promise is actually working.

## Scope

This smoke test is authoritative for the current beta release gate.
A milestone should not be treated as beta-ready unless the required checks in this file pass on the supported path.

Out of scope:
- non-Compose deployment
- public internet multi-user deployment
- federation durability
- sync guarantees outside the local stack
- unsupported provider paths
- unmerged/local-only work
- Tauri-specific packaging validation unless explicitly added later

## Supported path under test

- Branch: `main`
- Deployment model: local Docker Compose stack
- Primary interface: WebUI
- Required services: `frontend`, `backend`, `db`, `redis`, required workers
- System truth rule: if it is not merged to `main`, it does not count

## Preconditions

Before running this smoke test, confirm all of the following:

- You are testing the current `main` branch.
- Local environment variables required for the supported stack are present.
- Docker and Docker Compose are installed and functioning.
- No stale containers, volumes, or orphaned services are masking failures unless intentionally preserved for a restart test.
- The test environment is close enough to a fresh operator path that results are meaningful.

## Release gate summary

A smoke pass requires all required checks below to pass.

- [ ] Stack boot passes
- [ ] Frontend loads
- [ ] Backend health is acceptable
- [ ] Thread creation works
- [ ] User message send works
- [ ] Assistant completion works
- [ ] Turn/task flow does not stall
- [ ] Document upload works
- [ ] Embedding reaches ready state or equivalent supported success state
- [ ] Uploaded document content is retrievable through the supported chat/RAG path
- [ ] Core beta control surfaces do not regress the chat loop
- [ ] Restart does not obviously corrupt the supported local workflow

## Test procedure

### 1. Boot the supported stack

Objective: verify the supported local runtime boots cleanly.

Checks:
- Start the local Docker Compose stack from the current `main` branch.
- Confirm required services start successfully.
- Confirm there is no immediate crash loop in core services.
- Confirm workers required for completion / embedding / cron-related supported behavior are present.

Record:
- pass / fail
- any service that failed to start
- any degraded-but-running condition

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 2. Verify frontend availability

Objective: confirm the WebUI is reachable on the supported path.

Checks:
- Open the WebUI.
- Confirm the main application shell loads.
- Confirm the frontend can reach the backend without obvious fatal bootstrap failure.

Record:
- pass / fail
- visible bootstrap errors
- any gating/fallback state presented at load

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 3. Verify backend health surfaces

Objective: confirm the backend is not merely booted, but operational enough for the beta promise.

Checks:
- Verify the primary health endpoint responds successfully.
- Verify any currently maintained dependency or subsystem health endpoints used by the supported stack are acceptable.
- Confirm Redis/worker dependency health is not silently degraded in a way that invalidates chat completion.

Record:
- pass / fail
- endpoints checked
- health warnings observed

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 4. Create a thread

Objective: verify a user can begin a new conversation on the supported path.

Checks:
- Create a new thread in the WebUI.
- Confirm the thread appears in the expected UI state.
- Confirm the backend persists the thread without obvious error.

Record:
- pass / fail
- any UI or backend error

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 5. Send a user message

Objective: verify the basic input path from UI to backend persistence works.

Checks:
- Send a simple user message in the new thread.
- Confirm the message appears in the thread.
- Confirm no immediate request or persistence failure occurs.

Record:
- pass / fail
- any error surfaced to the user

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 6. Verify assistant completion

Objective: verify the worker-backed completion loop can produce an assistant turn.

Checks:
- Wait for the assistant turn to complete on the supported model/provider path.
- Confirm an assistant message is persisted.
- Confirm the resulting turn is visible in the UI.

Record:
- pass / fail
- time to completion if notable
- model/provider path used
- any degradation or retry behavior observed

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 7. Verify turn/task flow does not stall

Objective: confirm the chat/task lifecycle is not getting stuck in a broken intermediate state.

Checks:
- Confirm the turn completes without remaining stuck in an active/running state.
- Confirm task-event/SSE behavior is present enough for the supported UX.
- Confirm there is no obvious turn-lock, orphaned run, or permanently pending state after completion.

Record:
- pass / fail
- any stuck turn or event-stream anomaly

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 8. Upload a document

Objective: verify the document ingestion path begins successfully.

Checks:
- Upload a small supported document through the supported UI path.
- Confirm the document appears in the expected UI/state surface.
- Confirm ingestion starts without obvious fatal error.

Record:
- pass / fail
- file type tested
- any ingestion error observed

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 9. Verify embedding lifecycle

Objective: verify uploaded content reaches a supported ready state.

Checks:
- Observe the document through the embedding lifecycle.
- Confirm it reaches `ready` or the current equivalent supported success state.
- If recovery/retry behavior is required, record it explicitly rather than silently counting it as clean success.

Record:
- pass / fail
- final state
- whether retry/recovery was required
- any warnings or degraded behavior

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 10. Verify retrieval from uploaded content

Objective: confirm the uploaded document participates in retrievable context on the supported happy path.

Checks:
- Ask a narrow question grounded in the uploaded document.
- Confirm the system can answer using the uploaded content through the supported chat/RAG path.
- Confirm retrieval failure, hallucinated absence, or clearly missing context is not occurring on the happy path.

Record:
- pass / fail
- prompt used
- whether retrieval appeared grounded
- any ambiguity or degradation observed

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 11. Verify core beta control surfaces do not break the core loop

Objective: confirm newly added beta-facing control surfaces do not regress the release promise.

Checks:
- Exercise the currently relevant beta-gated control surfaces that are in scope for this milestone.
- Confirm their presence does not break thread load, message send, completion, or the thread view.
- This is a regression sanity check, not exhaustive feature validation.

Record:
- surfaces checked
- pass / fail
- any regression observed

Result:
- [ ] Pass
- [ ] Fail
- Notes:

### 12. Restart sanity check

Objective: confirm the supported local workflow survives a normal restart without obvious corruption.

Checks:
- Restart the supported local stack.
- Re-open the WebUI.
- Confirm the previously created thread still exists.
- Confirm message history is still present.
- Confirm the system is still capable of producing another assistant turn.

Record:
- pass / fail
- persistence issues observed
- startup issues after restart

Result:
- [ ] Pass
- [ ] Fail
- Notes:

## Failure handling

If any required check fails:

- Do not call the milestone beta-ready.
- Record the failing step exactly.
- Record whether the failure is hard, intermittent, or degraded-but-usable.
- Link the failure to the owning subsystem if known.
- Re-run the full smoke test after the fix if the failure affects the core release promise.

## Reporting template

Use this template for each run:

```md
Date:
Branch tested:
Commit:
Operator:
Environment:

Overall result:
- Pass / Fail / Degraded

Failing steps:
- None / list

Key blockers found:
- None / list

Notes:
- ...
```

## Exit rule

Codexify is considered smoke-pass ready for the current beta milestone only if all required checks in this document pass on `main` using the supported local Docker Compose path.