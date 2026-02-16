# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 002
- Title: Deterministic RAG completion to trace retrieval integration
- Finding: FINDING-2026-02-10-005
- Risk: MED

## Allowed Files
- tests/integration/test_rag_integration_loop.py
- tests/integration/test_chat_completion_context.py
- guardian/routes/chat.py
- guardian/workers/chat_worker.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${REDIS_URL:-} || { echo 'Missing REDIS_URL'; exit 1; }
5. test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
6. test -n ${CODEXIFY_VECTOR_STORE:-} || { echo 'Missing CODEXIFY_VECTOR_STORE'; exit 1; }
7. rg -n 'rag-trace|task.completed|_thread_latest_task' guardian/routes/chat.py guardian/workers/chat_worker.py tests/integration/test_chat_completion_context.py
8. pytest tests/integration/test_rag_integration_loop.py tests/integration/test_chat_completion_context.py -q
9. for f in $(git diff --name-only); do case $f in tests/integration/test_rag_integration_loop.py|tests/integration/test_chat_completion_context.py|guardian/routes/chat.py|guardian/workers/chat_worker.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Integration path executes API -> queue -> worker completion without synthetic trace injection.
- /api/chat/debug/rag-trace/{thread_id}/latest returns real trace for completed task.
- Integration suite passes deterministically.

## Rollback / Cleanup
- git restore --staged tests/integration/test_rag_integration_loop.py tests/integration/test_chat_completion_context.py guardian/routes/chat.py guardian/workers/chat_worker.py || true
- git restore tests/integration/test_rag_integration_loop.py tests/integration/test_chat_completion_context.py guardian/routes/chat.py guardian/workers/chat_worker.py || true

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${REDIS_URL:-} || { echo 'Missing REDIS_URL'; exit 1; }
- test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
- test -n ${CODEXIFY_VECTOR_STORE:-} || { echo 'Missing CODEXIFY_VECTOR_STORE'; exit 1; }


---

# Task 002 — DX: Deterministic Model-ID Discovery + Prompt Guidance (FINDING-2026-02-16-002)

Preflight: git status --porcelain -uall must be empty

## STOP Conditions
1) If preflight is not empty, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

2) If any out-of-scope files appear at any point, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

## Finding
- ID: `FINDING-2026-02-16-002`
- Severity: `WARN` (map to task risk: LOW)
- Title: MODEL-ID-UNKNOWN

## Outcome (must be observable)
- A deterministic command/script exists in-repo that prints a single “best available” model identifier for this runtime (based on env/config discovery), suitable for setting `agent.model` in future audits.
- `codex_runner/prompts/mega_audit.md` is updated to instruct the auditing agent how to populate `agent.model` deterministically (prefer exact model id; fallback to explicit `unknown` plus captured discovery output).

## Allowed Files (strict)
- `codex_runner/prompts/mega_audit.md`
- `codex_runner/**/*.md`
- `codex_runner/**/*.sh`
- `codex_runner/**/*.py`
- `docs/**/*.md`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Discovery commands (audit-suggested; must remain runnable):
- `printenv | rg -i 'CODEX|MODEL|OPENAI' || true`
- `python - <<'PY'
import os
keys = [k for k in os.environ if ('MODEL' in k.upper() or 'CODEX' in k.upper() or 'OPENAI' in k.upper())]
for k in sorted(keys):
    print(f"{k}={os.environ.get(k)}")
PY`
- `codex --version || true`
- `codex config list || true`

3) Implement:
- Add a small deterministic helper (shell or python) under `codex_runner/` that:
  - checks (in order) `CODEX_MODEL`, `OPENAI_MODEL`, then any Codex CLI config if available
  - prints one line: `MODEL_ID=<value>`
  - if nothing is available, prints `MODEL_ID=unknown` (still exit 0)
- Update `codex_runner/prompts/mega_audit.md` so the audit output sets `agent.model` to that `MODEL_ID` value.

4) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- Running the helper prints exactly one `MODEL_ID=...` line (either a concrete id or `unknown`).
- `codex_runner/prompts/mega_audit.md` includes deterministic instructions referencing the helper and/or env vars.
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- codex_runner/prompts/mega_audit.md`
- `git restore --source=HEAD --staged --worktree -- codex_runner`
- `git restore --source=HEAD --staged --worktree -- docs`
- `git clean -fd`
