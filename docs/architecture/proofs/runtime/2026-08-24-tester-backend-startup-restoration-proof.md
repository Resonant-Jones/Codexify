# Tester backend startup restoration proof

## Result

**BLOCKED — the accepted Tester provider posture is no longer the startup
blocker, but persisted Chroma state prevents backend initialization.**

## Scope and source

- **Branch:** `codex/define-github-watchdog-control-plane`
- **Source commit at preflight:**
  `45736720aeb7cfa210aeb69b966795a83897fbe5`
  (`Restore tester model authority`), present in `HEAD` ancestry.
- **Governing decisions:** ADR-052 (dual-provider Tester profile) and ADR-074
  (Tester provider/model configuration authority).
- **Accepted Tester posture:** global `local` / Whoosh'd; operator-selected
  `gemma-4-12b-it-qat-4bit`; `ALLOW_CLOUD_PROVIDERS=true`;
  `CODEXIFY_LOCAL_ONLY_MODE=false`; DeepSeek remains the bounded,
  thread-selected, `deepseek`-allowlisted lane.

`.env.tester` remained ignored and unstaged. It was not changed by this task.

## First repaired blocker

The original backend exit code was `3`. A one-shot lifespan probe in the
canonical Tester Compose backend image exposed the first unsanitized exception:

```text
RuntimeError: supported profile drift: LOCAL_CHAT_MODEL expected
'qwen3.8-27b-4bit' but found 'gemma-4-12b-it-qat-4bit'
```

The failure occurred in `guardian.guardian_api._refresh_supported_profile_state`
while calling `build_supported_profile_runtime_state`.

**Classification:** `CONFIGURATION_ERROR`.

### Root cause and repair

`guardian/core/supported_profile.py` compared every manifest value literally.
That incorrectly made ADR-074's historical profile default into a requirement
even when the operator explicitly supplied `LOCAL_CHAT_MODEL`. The supported
profile still owns provider, cloud, egress, endpoint, and route posture; only
the explicit concrete local-chat-model selection is operator-owned.

The repair exempts only an explicit `LOCAL_CHAT_MODEL` environment selection
from that one literal comparison. It does not change provider routing, model
inventory handling, fail-closed availability, cloud authorization, DeepSeek
configuration, or Compose authority.

Changed files:

- `guardian/core/supported_profile.py`
- `tests/core/test_supported_profile_provider.py`

The new regression first failed against the old validator and then passed. The
focused Tester/provider suite passed: `19 passed`.

## Current stopping blocker

After the profile repair, the same bounded lifespan probe advanced into
`backend.rag.embedder` and failed while creating Chroma's persistent client:

```text
PanicException: range start index 10 out of range for slice of length 9
```

Relevant frames:

- `backend/rag/embedder.py:282` (`__init__`)
- `backend/rag/embedder.py:239` (`_create_chroma_client`)
- `chromadb` Rust startup (`PersistentClient`)

**Classification:** `EXTERNAL_RUNTIME_ERROR` — persisted Chroma state is
incompatible with the installed Chroma runtime. This task does not authorize a
Chroma reset, metadata rewrite, dependency change, or storage migration
repair.

The recreated backend therefore still exits with code `3`, and `worker-chat`
was not started. No backend health, chat-health, or provider-catalog claim is
made.

## Boundaries preserved

- No ordinary chat thread, user message, completion task, or assistant message
  was created.
- The Chroma panic occurred before startup's warmup enqueue, so no model or
  cloud request was initiated by this task.
- No Whoosh'd, DeepSeek, Redis, Postgres, Watchdog, or release-support
  configuration was changed.
- No Watchdog attempt, snapshot, dispatch, queue task, or inference occurred.

## Validation

- `git merge-base --is-ancestor 45736720... HEAD` — passed.
- `.venv/bin/python -m pytest -v tests/core/test_supported_profile_provider.py
  tests/ops/test_codexify_tester_services.py` — passed (`19 passed`).
- `.venv/bin/ruff check guardian/core/supported_profile.py
  tests/core/test_supported_profile_provider.py` — passed.
- Canonical Tester Compose render — passed, with existing unset
  `LOCAL_VISION_MODEL` / `LOCAL_GGUF_MODEL` warnings.
- `git diff --check` — passed before this proof record was added.

An exploratory, unrelated health-profile test set also exposed three existing
assertions expecting the old `host.docker.internal:11434/v1` local base while
the current supported profile requires `http://host.docker.internal:8000/v1`.
Those assertions are outside this startup repair and were not changed.

## Deferred next slice

Diagnose the persisted Chroma runtime/index compatibility without deleting or
rewriting durable state. Only after that prerequisite is resolved can backend
and `worker-chat` startup be re-qualified, followed by the separate ordinary
local-completion proof.
