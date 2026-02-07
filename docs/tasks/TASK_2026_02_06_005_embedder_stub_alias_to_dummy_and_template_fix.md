# TASK_2026_02_06_005_embedder_stub_alias_to_dummy_and_template_fix

## Objective

Prevent default environment configurations from breaking the `/api/embeddings` endpoint by restoring backward-compatible embedder behavior.

## Background

Recent validation restricts EMBEDDING_BACKEND to `{dummy, gpt_oss, nomic}`.
Repo templates still define `EMBEDDING_BACKEND=stub`, causing a 400 error on fresh setups.

## Requirements

### Backend

- Treat `stub` as an alias for `dummy`
- Optional: also alias `mock -> dummy` if present historically
- `/api/embeddings` must succeed under default config

### Templates / Docs

- Update `.env.example` and templates to use `dummy`
- Document accepted values explicitly

## Acceptance Criteria

- `EMBEDDING_BACKEND=stub` no longer errors
- Fresh clone + default `.env` returns embeddings successfully
- No regression for explicit real backends

## Files Likely Touched

- Guardian embedder resolution logic
- `.env.example`
- README / environment docs

## Commit Plan

- Commit A: backend alias logic
- Commit B: template + docs update
