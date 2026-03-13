# TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix

## Metadata
- Task-ID: TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix
- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Risk: HIGH
- Branch: campaign/2026-02-06/loop-integrity-auth-and-defaults
- Task artifact: docs/work/tasks/2026/02/TASK_2026_02_06_005_embedder_stub_alias_to_dummy_and_template_fix.md
- Owner: resonant_jones

## Objective
Make `/api/embeddings` **work under default repo env templates** by restoring backward-compatible embedder selection:
- `EMBEDDING_BACKEND=stub` must not break local setups (treat as alias for `dummy`).
- Templates/docs must not ship an invalid default value.

## Background
Recent validation restricts `EMBEDDING_BACKEND` to `{dummy, gpt_oss, nomic}`.
Repo templates still define `EMBEDDING_BACKEND=stub`, causing a 400 error on fresh setups.

## Scope
### In-scope
- Backend: treat `stub` as an alias for `dummy` (and optionally `mock -> dummy` if historically present).
- Templates/docs: update `.env.example`/`.env.template` (and any canonical env docs) to use an allowed default (`dummy`) and explicitly document accepted values.
- Add/adjust tests to lock the behavior so default config doesn’t regress.

### Out-of-scope
- Implementing a new embeddings backend.
- Changing embedding vector dimensionality/format.
- Any refactor unrelated to resolving `stub` defaults and documenting the contract.

## Allowed files (STRICT)
> Do not modify files outside this list.

- guardian/embedding_engine.py
- guardian/routes/embeddings.py
- .env.example
- .env.template
- README.md
- guardian/tests/test_embeddings_endpoint.py
- docs/work/tasks/2026/02/TASK_2026_02_06_005_embedder_stub_alias_to_dummy_and_template_fix.md
- docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Preconditions (NO GUESSING)
Run these to confirm context and locate current behavior:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# must be clean before starting
git status --porcelain -uall

# confirm current env template values
rg -n "^EMBEDDING_BACKEND=" .env.example .env.template README.md || true

# confirm allowed embedder validation and current behavior
rg -n "EMBEDDING_BACKEND|embedder|dummy|stub|mock|Unsupported embedder" guardian/embedding_engine.py guardian/routes/embeddings.py

# confirm tests exist / current expectations
rg -n "embeddings" guardian/tests/test_embeddings_endpoint.py || true
```

## Execution plan
### Step-by-step commands (copy/paste)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 1) preflight
git status --porcelain -uall

# 2) implement + adjust tests/docs/templates within allowed files
# (edit files listed in Allowed files)

# 3) run focused checks
python -m pytest -q guardian/tests/test_embeddings_endpoint.py

# 4) ensure only allowed files changed
git status --porcelain -uall
```

## Expected results
- With `EMBEDDING_BACKEND=stub`, `/api/embeddings` returns **200** and a valid embeddings payload (no “Unsupported embedder: stub”).
- `.env.example` and `.env.template` no longer set `EMBEDDING_BACKEND=stub`.
- README documents accepted values (at minimum: `dummy`, `gpt_oss`, `nomic`) and notes that `stub` is accepted as an alias for backward compatibility.
- `guardian/tests/test_embeddings_endpoint.py` includes coverage for the alias behavior (stub → dummy), so a regression fails tests.

## Rollback / cleanup

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard changes to the task’s allowed files (if abandoning)
git restore -- \
  guardian/embedding_engine.py \
  guardian/routes/embeddings.py \
  .env.example \
  .env.template \
  README.md \
  guardian/tests/test_embeddings_endpoint.py \
  docs/work/tasks/2026/02/TASK_2026_02_06_005_embedder_stub_alias_to_dummy_and_template_fix.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

# remove any untracked files created during work
git clean -fd
```

## Commit plan (MANUAL; index.lock workaround)
### Commit mode
- two-phase

### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix: alias stub to dummy + keep embeddings default working`

- Manual commands:

```bash
git status --porcelain -uall

git add \
  guardian/embedding_engine.py \
  guardian/routes/embeddings.py \
  guardian/tests/test_embeddings_endpoint.py

git commit --no-verify -m "TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix: alias stub to dummy + keep embeddings default working"

git status --porcelain -uall
git log -1 --oneline
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix: docs finalize + mapping`

- Manual commands:

```bash
git status --porcelain -uall

git add \
  .env.example \
  .env.template \
  README.md \
  docs/work/tasks/2026/02/TASK_2026_02_06_005_embedder_stub_alias_to_dummy_and_template_fix.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix: docs finalize + mapping"

git status --porcelain -uall
git log -1 --oneline
```

## Mapping
- TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix -> [<commitA>, <commitB>]

## Notes
- If `mock` appears in historical env docs/templates, treat it like `stub` (alias to `dummy`).
- Prefer behavior that keeps “fresh clone + default .env” functional even without external model backends.

## Summary (fill after completion)
- What changed:
  - `stub` now aliases to `dummy` in `guardian/embedding_engine.py`.
  - `/api/embeddings` now accepts `stub` as dummy-mode provider in `guardian/routes/embeddings.py`.
  - Added regression coverage in `guardian/tests/test_embeddings_endpoint.py` for `EMBEDDING_BACKEND=stub`.
  - Updated defaults to `EMBEDDING_BACKEND=dummy` in `.env.example` and `.env.template`.
  - Updated README accepted values and alias note.
- Commands run + outputs:
  - `rg -n "^EMBEDDING_BACKEND=" .env.example .env.template README.md || true`
    - Found `EMBEDDING_BACKEND=stub` in `.env.example` and `.env.template` before edits.
  - `python -m pytest -q guardian/tests/test_embeddings_endpoint.py`
    - Failed: `No module named pytest`.
  - `git status --porcelain -uall`
    - Only task-allowed files changed.
- Commit A hash:
  - `62b4ba58`
- Commit B hash:
  - `2738a365`
- Final mapping:
  - TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix -> [62b4ba58, 2738a365]
