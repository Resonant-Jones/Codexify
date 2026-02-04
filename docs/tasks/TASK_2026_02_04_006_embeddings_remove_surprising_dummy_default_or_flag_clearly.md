# TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly

## Title

Make embeddings behavior explicit: no silent dummy vectors in real workflows

## Audit Link / Finding

- FINDING-2026-02-04-006

## Allowed Files List (ONLY)

- guardian/embedding_engine.py
- guardian/routes/embeddings.py
- README.md
- tests/*or guardian/tests/* (targeted embeddings behavior test)

## Command Checklist

Preflight:

- git status --porcelain -uall

Locate dummy default:

- rg -n "dummy" guardian/embedding_engine.py guardian/routes/embeddings.py

Implement (choose one within scope):
Option A (preferred): default to real backend when configured; otherwise return clear error/warning
Option B: keep dummy for dev but endpoint must return metadata/flag and README/UI must clearly mark it

Verify:

- Call embeddings endpoint with and without config
- Confirm behavior matches documented expectations

Tests:

- Add/adjust tests to assert dummy behavior is not silently treated as real

## Expected Outputs (Success Criteria)

- Embeddings endpoint does not silently return dummy vectors in “normal” mode
- If dummy remains, responses and docs clearly mark it as mock/dev-only

## Rollback / Cleanup Commands

- git restore --staged <paths>
- git restore <paths>

## Dependencies / Prereqs

- If testing real embeddings: configured LOCAL_EMBED_MODEL or OPENAI_API_KEY in local env (not committed)

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly: clarify embeddings behavior"

Commands:

- git add guardian/embedding_engine.py guardian/routes/embeddings.py README.md tests guardian/tests
- git commit --no-verify -m "TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly: clarify embeddings behavior"
Record CommitA=55b5d25c

### Docs Commit message EXACT

"TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly: finalize task docs and campaign mapping"

Commands:

- git add docs/tasks/TASK_2026_02_04_006_embeddings_remove_surprising_dummy_default_or_flag_clearly.md docs/Campaign/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly: finalize task docs and campaign mapping"
Record DocsCommit=afca36d8

Campaign mapping update EXACT:

- TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly -> [<commitA>] DocsCommit=<docsCommit>

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
