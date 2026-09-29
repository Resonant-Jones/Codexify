# Account import UI to durable staging proof — 2026-09-23

## Verdict and boundary

**G. Current UI → durable staging passes** for a disposable synthetic OpenAI folder in an isolated local Compose project. The rendered WebKit UI created job `60267dac-80c5-4563-85d5-24090662672e`, uploaded two files to its real Guardian route, received HTTP 200, and read the same `receiving` job back through the status API and PostgreSQL. Chromium repeated the chain. Commit was intercepted after upload; no account-import worker was started. This is a staging proof, not worker, canonical materialization, private-preview, or full supported-profile qualification. The current end-user complaint remains unlocalized beyond this isolated profile.

The prior [Safari 422 reproduction](./2026-09-02-account-import-422-reproduction-proof.md) remains a distinct, dated private-preview observation. This probe does not erase it or identify its cause.

## Source and runtime identity

- Branch: `main`; source HEAD during proof: `f3d1b0a15a3a76692835c2b35e0f40f9d2efaa3c`. Only the two task-owned files were edited for this proof.
- Compose project: `codexify_account_import_ui_probe_20260923`, fresh PostgreSQL and Redis volumes, distinct from the existing `codexify` project.
- Compose sources: `docker-compose.yml`, `docker-compose.whooshd-smoke.yml` for supported local-only provider posture, and `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml` for loopback ports and isolated import staging storage. The override was not committed. An initial backend start using only the base file and temporary override exited at profile validation because the ambient egress allowlist was nonempty; applying the repository smoke overlay resolved that startup conflict before any import was sent.
- Startup commands, from repository root: `docker compose -p codexify_account_import_ui_probe_20260923 -f docker-compose.yml -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml up -d db redis migrator`; `docker compose -p codexify_account_import_ui_probe_20260923 -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml up -d --no-deps --force-recreate backend`; `docker compose -p codexify_account_import_ui_probe_20260923 -f docker-compose.yml -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml up -d --no-deps frontend`.
- Running proof services: frontend, backend, PostgreSQL, Redis; migrator exited 0. The account-import worker was absent. This is an intentional staging-only subset, not the complete required-service set of `v1-local-core-web-mcp`.
- Frontend origin: `http://127.0.0.1:5183`; backend origin: `http://127.0.0.1:8893`; PostgreSQL host port: `127.0.0.1:5548`. Backend startup accepted `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`; isolated database revision: `a8d4c2f6b1e9`.
- Browser: Playwright WebKit for the primary receipt; Chromium for cross-browser confirmation. The temporary browser config pointed to the isolated frontend and did not start another Vite server.

## Rendered workflow and synthetic data

The current entry point is Settings → Data tab → **Import ChatGPT history** button → **Import account data** modal. The modal has an **Account import source** selector with **OpenAI (ChatGPT)** checked by default and a **Choose Folder** button. The folder picker starts the account-import coordinator immediately. A single JSON file and **Upload & Migrate** use a separate legacy endpoint, so this proof used the folder path.

The test created a temporary `openai-export` folder and selected it through the rendered **Choose Folder** control. It contained only:

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `openai-export/conversations.json` | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `openai-export/nested/user.json` | 2 | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` |

No real export or user conversation data was used. The fixture directory was removed by the test after submission. The database and staging storage were isolated in this disposable Compose project.

## Correlated browser, API, and database evidence

| Step | WebKit primary receipt |
| --- | --- |
| Browser create | `POST /api/imports/openai-account` → HTTP 200, `source_system=openai`, job ID `60267dac-80c5-4563-85d5-24090662672e`, declared 2 files / 4 bytes |
| Browser upload | `POST /api/imports/openai-account/60267dac-80c5-4563-85d5-24090662672e/files` → HTTP 200; browser multipart header included a boundary; body had ordered `files`, `relative_paths` pairs with the two listed filenames and paths |
| Exact-job API readback | `GET /api/imports/openai-account/60267dac-80c5-4563-85d5-24090662672e` → HTTP 200, `receiving`, declared 2/4 and uploaded 2/4 |
| Read-only PostgreSQL readback | Same ID, owner `local`, source `openai`, `receiving`, declared 2/4, uploaded 2/4, two manifest entries with the listed paths, sizes, and hashes |
| Commit boundary | Browser `POST .../commit` intercepted after the real upload and given a synthetic 409 response; no commit request reached Guardian |

The WebKit receipt was captured at `2026-09-23T15:18:00.327Z`. The focused Chromium run produced job `1e4370bc-5389-4401-9cc6-dfd6a1f07668` at `2026-09-23T15:18:48.348Z`; the full Chromium spec produced another correlated job, `de0806ad-7a34-4d82-8ad5-c8729aefdf46`, at `2026-09-23T15:20:50.278Z`. Every real-backend scenario intercepted commit and asserted exact-job API and PostgreSQL readback. The independent PostgreSQL query for the WebKit job used `BEGIN READ ONLY` and `ROLLBACK`; its manifest path, size, and SHA-256 metadata matched the synthetic fixture.

After the test added explicit manifest-path assertions to its PostgreSQL readback, the final focused WebKit run passed with job `480efaba-13b2-4d01-a97f-c9601bd7cf8d` at `2026-09-23T15:23:16.950Z`, and the final full Chromium run passed with job `44eb5ac1-354d-4bfa-a6d7-771eb726accf` at `2026-09-23T15:23:31.661Z`. Both again reported HTTP 200 for create, upload, and status; 2/2 files and 4/4 bytes; matching manifest paths; and commit interception.

The first boundary failure classification is therefore **G**, limited to this isolated local runtime. No `422`, route rejection, staging persistence failure, or UI entry-point regression occurred here. The historical private-preview Safari failure and any current affected-account behavior remain separate and unproven by this run.

## Existing UI tests and validation

The three older migration UI cases had a stale `Import from ChatGPT` heading assertion. The rendered modal title is `Import account data`. The two single-file cases also needed the non-directory file input selector and the current sidebar-opening step before locating a thread tile; the large-file case needed the same title and input selector. After those test-only alignments, the full Chromium file passed 6/6. These older cases fulfill all `/api` requests in Playwright and simulate import/completion; their pass is not real backend or worker proof.

- Focused WebKit real-backend scenario: 1 passed, `proven-live-runtime` for browser → real Guardian → exact-job API → disposable PostgreSQL staging.
- Focused Chromium real-backend scenario: 1 passed, same evidence class and boundary.
- Complete migration Playwright file in Chromium: 6 passed; its one real-backend scenario has the staging proof above, while the other five cases are isolated `proven-test` evidence.
- `.venv/bin/python -m pytest -v tests/routes/test_migration_routes.py`: 28 passed, `proven-test` route contract.
- `.venv/bin/python -m pytest -v tests/workers/test_account_import_worker.py`: 9 passed, `proven-test` regression guard only; no worker ran in this staging probe.

The checked-in Playwright config exposes Chromium only and the package layout requires `pnpm --dir frontend/src exec playwright`; the requested `pnpm --dir frontend exec ...` command was not directly runnable in this checkout. Browser tests used `/private/tmp/codexify-account-import-ui-staging-20260923/playwright.config.mjs` to target the isolated frontend and select WebKit or Chromium. The first full-file run was rejected by automatic approval review because the older scenarios could have exceeded the staging boundary. Inspection showed each older scenario fulfills every `/api` request locally, while the real-backend scenario intercepts only commit; the subsequent scoped full run was approved.

## Scope and follow-through

No production frontend, backend, route, queue, worker, schema, importer, ownership, provenance, UMS, or retrieval behavior changed. Multipart field names and staging semantics remain unchanged. No affected user account or private-preview data was accessed. No release claim or `00-current-state.md` change is justified. ADR impact: **No ADR impact**. Documentation follow-through: this proof artifact only.

Next prerequisite: **Trace the browser-created staged job through commit, queue, worker, and canonical thread/message materialization** in a separate authorized task. This proof intentionally stops before that boundary.
