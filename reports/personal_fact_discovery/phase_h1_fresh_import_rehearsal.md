# Phase H1 Fresh Import Rehearsal

Status: blocked

## Canonical Archive

- Archive path verified: `/Users/chriscastillo/Downloads/OpenAI-export`
- Archive access path used for import/recon: `/tmp/codexify-openai-export.zTajRH`
- Archive contents verified with read-only recon:
  - `files_scanned`: `4513`
  - `json_like_files`: `61`
  - `conversations_found`: `5043`
  - `messages_scanned`: `111841`
  - `assets_found`: `4452`
  - `orphan_assets_found`: `4452`
  - `parse_failures`: `0`

## Reset And Migration

- DB reset command used:

  ```bash
  docker compose exec -T db psql -U codexify -d postgres -c 'DROP DATABASE "Codexify" WITH (FORCE);' -c 'CREATE DATABASE "Codexify";'
  ```

- Migrations run:

  ```bash
  docker compose run --rm migrator
  ```

- Auth / user state after reset:
  - auth mode: `local`
  - single-user identity: `local`

## Import Attempts

### Attempt 1: direct import against the full extracted archive

- Command shape:

  ```bash
  docker compose run --rm --no-deps -v /tmp/codexify-openai-export.zTajRH:/import:ro -e CODEXIFY_CHATGPT_IMPORT_EMBEDDINGS=0 -e CODEXIFY_CHATGPT_IMPORT_EMBED_ISOLATED=0 -e CODEXIFY_DISABLE_DOTENV=1 backend -c "from backend.rag.openai_export_adapter import import_openai_export_path; ..."
  ```

- Outcome:
  - the process was repeatedly killed with exit `137`
  - Postgres repeatedly entered recovery / shutdown during the run
  - the initial importer path also misdetected the archive manifest `__export_file_manifests__/conversations.json` as a legacy `conversations.json` export and returned zero imported records until the temp copy was adjusted

### Attempt 2: shard fan-out over the extracted archive

- I split the conversation JSON files into temp shard directories under `/tmp/codexify-openai-split3`
- 5-way parallel import was too aggressive and caused Postgres to restart/shutdown under load
- A single shard did complete during that experiment:
  - `group`: `g2`
  - `threads_imported`: `469`
  - `messages_imported`: `13183`
- The wider fan-out still destabilized the database, so it was not a safe route for H1

## Current Partial Snapshot

Latest stable snapshot before the final shutdown:

- `chat_threads`: `72`
- `chat_messages`: `1917`
- `personal_facts_total`: `4`
- `personal_facts_candidate`: `4`
- `personal_facts_verified`: `0`
- `personal_facts_disputed`: `0`
- `personal_facts_archived`: `0`
- `personal_facts_runtime_eligible`: `0`
- `assistant_guardrailed`: `3`
- `promotion_blocked`: `4`
- `quarantine`: `4`
- `evidence_rows`: `210`

## Review Console

- Not fully verified on the final fresh import state because the import never reached a stable completion point.
- Earlier UI code inspection confirmed the review surface is `frontend/src/settings/FactCandidateReview.tsx` via the Personal Facts settings panel, but a fresh end-to-end load could not be proven from the completed import state.

## Discrepancies From The Seeded DB

- The seeded database was not a good proxy for the archive-derived state.
- The archive import path is sensitive to the manifest file named `conversations.json` inside `__export_file_manifests__`; that manifest can falsely trigger the legacy importer branch.
- The archive is much larger than the seeded DB and needs a durable, resumable import path to complete reliably.

## Bugs Found

1. OpenAI export adapter legacy misdetection
   - `__export_file_manifests__/conversations.json` is treated as a legacy `conversations.json` export unless filtered out.
2. Import stability under load
   - Both single-process and parallel shard import attempts caused Postgres recovery/shutdown cycles.
3. Concurrency pressure
   - 5-way shard fan-out was too aggressive for the local DB.

## Recommendation Before Broader Beta

- Fix the export adapter so manifest files cannot hijack the legacy importer path.
- Add bounded/resumable import checkpoints so the archive can be imported in smaller verified steps.
- Keep parallelism conservative until the importer is proven stable under load.
- Re-run the fresh import rehearsal only after the import path is deterministic on a clean local database.

