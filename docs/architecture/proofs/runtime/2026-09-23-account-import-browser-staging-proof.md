# Browser to durable account-import staging proof — 2026-09-23

## Verdict

**PASS — `proven-live-runtime` for the browser-to-durable-staging seam in the isolated local Compose project.** Chromium's rendered Settings UI selected one synthetic ZIP through the account-import folder picker. The normal coordinator created an account-owned job, uploaded one multipart batch through Guardian, and received HTTP 200. A separate HTTP GET after upload read the same durable job and matching 1-file / 474-byte counters. No account-import API was mocked or invoked directly as the import action; no database row was inserted or repaired manually.

This receipt does not qualify the complete supported profile, private preview, Safari/WebKit, worker materialization, canonical conversation persistence, indexing, retrieval, or release readiness.

## Source and runtime identity

- Repository: `/Volumes/Dev_SSD/Codexify-main`; branch: `main`; evaluated HEAD: `71a58d7294814e60a8fbebea5a916aafa46ac521`. `git merge-base --is-ancestor 38d60aa7cceb7afee024ccd4b9d7260b47c0d90e HEAD` passed. Initial working tree was clean.
- Disposable Compose project: `codexify_account_import_ui_probe_20260923`, previously stopped, with retained isolated Postgres/Redis volumes. It was started for this probe using `docker-compose.yml`, `docker-compose.whooshd-smoke.yml`, and its existing `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`. No Compose file was changed. The active default `codexify` project was untouched.
- Browser/frontend: Playwright Chromium at `http://127.0.0.1:5183`, served by `codexify_account_import_ui_probe_20260923-frontend-1` (image ID `sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293`). Backend: `codexify_account_import_ui_probe_20260923-backend-1` at loopback `127.0.0.1:8893` (image ID `sha256:f86d6720655406ac6943710e1fc3ea22b9d3d2b230a0c1ef999adfb71679d3f9`); frontend `/api` traffic used its Vite proxy to that backend. Postgres: isolated project `db-1` at loopback `127.0.0.1:5548`. This is a local-only subset, not full supported-Compose qualification.
- `worker-account-import` was exited before the probe and remained exited afterward. It was never started for this task. The default project's account-import worker was also absent from `compose ps`.
- The local auth account was `local`. The first browser attempt inherited the UI placeholder `You`; its create request returned 500 because Postgres rejected `user_id=You` under `openai_account_import_jobs_user_id_fkey`. No job was created by those attempts. The disposable browser's `cfy.userName` was then set to the existing `local` account and the UI was reloaded. This was browser identity setup, not a database repair. The successful job and independent readback both used `local` through the normal request boundary.

## Synthetic selection and browser chronology

The ZIP was built outside the repository from `frontend/src/tests/playwright/fixtures/chatgpt_export_sample.json`, with one synthetic `conversations.json` member. The ZIP had **474 bytes** and SHA-256 `a435ecf71d98a9a3a1e99b302bbf24d8b4b7f2f0c1fe8ea71200eb2a96bda398`. Selected file count was **1**. The temporary ZIP and its directory were removed at closeout. No raw fixture content or personal export was used.

The rendered path was Settings → Data → Import ChatGPT history → Import account data → OpenAI (ChatGPT), then **Choose Folder** with the one-ZIP synthetic folder. Folder selection started the normal coordinator. The single-file **Choose File** control is a different legacy import path and was not used.

| Step | Bounded browser/network receipt |
| --- | --- |
| Create | `POST /api/imports/openai-account` → 200; declared 1 file / 474 bytes, source `openai`; returned `receiving` job `40caeca7-6ac6-4269-a522-3ca95e34d3a0` |
| Upload | `POST /api/imports/openai-account/40caeca7-6ac6-4269-a522-3ca95e34d3a0/files` → 200; response job ID matched; uploaded 1 file / 474 bytes |
| Downstream commit | The coordinator subsequently sent `POST /api/imports/openai-account/40caeca7-6ac6-4269-a522-3ca95e34d3a0/commit` → 200. Commit and queue acceptance are downstream observations only. |
| Independent durable read | A new `page.request.get` through the same frontend proxy, with `X-User-Id: local`, called `GET /api/imports/openai-account/40caeca7-6ac6-4269-a522-3ca95e34d3a0` after upload → 200. It returned `queued`, source `openai`, declared 1 / 474, uploaded 1 / 474, warning count 0, failure count 0. The GET route uses a new Guardian service/session read of `openai_account_import_jobs`. |

The upload request header reported media type `multipart/form-data` with a boundary. Guardian accepted the nonempty upload, parsed the required repeated `files` and `relative_paths` fields, enforced equal list lengths, and staged exactly one file. Thus the matched envelope count is **one `files` part and one `relative_paths` part**. The browser tool did not expose the binary multipart body for direct part enumeration; the count is inferred from the route's required-field/equal-length validation plus the one-file upload response. No raw multipart body, credentials, cookie, or authorization header was preserved here.

The readback matched the browser-created job ID, declared count and bytes, upload response count and bytes, and selected ZIP size. The queued status followed the real commit request; it is not evidence that a worker executed. No `/api/imports/openai-account*` route was mocked.

## Logging and limits

Backend logs for the probe window contained **none** of `TypeError: %d format: a real number is required, not str`, `ChatGPT import sweep failed`, `account-import upload exception`, or an HTTP 422 multipart upload. The two earlier create attempts under `You` produced `IntegrityError` / HTTP 500 before the local-account retry; they did not reach upload or staging. The successful local-account create, upload, and readback returned 200.

The focused logging guard ran from the repository root before and after the probe: `.venv/bin/python -m pytest -v tests/security/test_content_credential_logging.py guardian/tests/test_guardian_api_startup.py` — **10 passed, 8 warnings** on each run. `git diff --check -- docs/architecture/proofs/runtime/2026-09-23-account-import-browser-staging-proof.md` passed after staging the sole new artifact. The final pre-commit `git status --short --untracked-files=all` listed only this proof artifact; no implementation file changed. The temporary ZIP, probe scripts, and generated browser snapshots were removed. Only the isolated frontend/backend/Postgres/Redis services started for this task were stopped; their volumes were retained, and `worker-account-import` remained exited. This test proof is separate from the live staging receipt.

ADR impact: **No ADR impact; aligned with ADR-069 and ADR-081.** No `00-current-state.md`, implementation, worker, migration, supported-profile, or Compose source file was changed. The account boundary was enforced by the route and Postgres foreign key; the synthetic job belongs to `local`. No release claim is expanded. Worker materialization, canonical Project/thread/message persistence, derived indexing, retrieval selection/injection, and Safari/WebKit transport remain unproven by this task.
