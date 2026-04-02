# Account Export / Export Codexify History Status Investigation

Date: 2026-04-01
Scope: investigation-only (no runtime code changes)

## Summary
The live DATA tab does **not** implement a full account export. The current surface is a narrow download path for imported ChatGPT conversations, plus a separate thread-row NDJSON export and an unrelated single-entry Codex markdown export.

The exact label `Export Codexify History` does not appear in the active source. The live DATA tab renders `Import ChatGPT history` and `Download Codexify ZIP export`.

## Frontend surface

### Active settings surface
- The settings UI mounted by the app shell is `frontend/src/features/settings/SettingsView.tsx`, not the older `frontend/src/components/settings/SettingsView.tsx`.
- Anchor: `frontend/src/components/persona/layout/AppShell.tsx:35,2488-2490`

### DATA tab buttons
- The DATA tab renders the import and export buttons in `frontend/src/features/settings/SettingsView.tsx:1250-1268`.
- The import button only toggles local UI state:
  - `setImportPanelHidden(false)`
  - `setChatGPTModalOpen(true)`
- That means the import button does **not** itself trigger a backend call or route change. It opens the modal.

### Import wiring
- The modal submit path is `frontend/src/components/modals/ChatGPTImportModal.tsx:89-121`.
- It posts `POST /api/upload-chatgpt-export` via the shared API client.

### Export wiring
- The export button is wired to `handleDownloadExport` in `frontend/src/features/settings/SettingsView.tsx:942-949`.
- That function resolves `"/exports/chatgpt.zip"` and then:
  - in desktop mode, calls `openExternalUrl(exportUrl)` (`frontend/src/lib/runtimeConfig.ts:341-353`)
  - otherwise sets `window.location.href = exportUrl`
- Classification: browser navigation / download, not a frontend route change and not an XHR/fetch API call.
- The browser-side download path is not an app-authenticated fetch; it depends on whatever auth state the browser already has.

### Legacy adjacency
- The older `frontend/src/components/settings/SettingsView.tsx` contains ChatGPT import controls, but it is not the active settings surface mounted by `AppShell`.

## Backend / export surface

### Export router
- The export router is mounted under the `/exports` prefix.
- Anchor: `guardian/routes/api_exports.py:19-22`

### `GET /exports/threads.ndjson`
- Handler: `export_threads`
- Anchor: `guardian/routes/api_exports.py:243-295`
- Auth: `require_user`
- Response type: `StreamingResponse`
- Artifact format: `application/x-ndjson`, filename `threads.ndjson`
- Included entity family: `chat_threads` rows for the current authenticated user
- Excluded by design: message bodies, uploaded documents, generated documents, uploaded images, generated images

### `GET /exports/chatgpt.zip`
- Handler: `export_chatgpt_zip`
- Anchor: `guardian/routes/api_exports.py:298-425`
- Auth: `require_user`
- Response type: `Response`
- Artifact format: `application/zip`, filename `chatgpt_export_<timestamp>.zip`
- Included entity family: imported ChatGPT conversations only
- Internal payload contents:
  - `manifest.json`
  - per-thread `.json` export when `format=both` or `json`
  - per-thread `.md` export when `format=both` or `markdown`
- Data source helpers:
  - `fetch_imported_chatgpt_threads_for_user`
  - `fetch_imported_chatgpt_messages_for_thread`
- Anchor for those helpers: `guardian/core/pgdb.py:2225-2405`

### Import-adjacent surface
- Import route: `guardian/routes/migration.py:44-55`
- Canonical path: `POST /api/upload-chatgpt-export`
- Legacy alias: `POST /upload-chatgpt-export`
- Auth: `get_request_user_id` and `require_api_key`
- Response model: `MigrationStats`

### Nearest adjacent export-related surface
- Single-entry Codex markdown export:
  - `guardian/routes/codex.py:191-208`
  - legacy redirect alias in `guardian/guardian_api.py:1063-1068`
- This is not account export. It exports one Codex entry as markdown.

### Authentication note
- `require_user` accepts API key, bearer token, or `gc_session` cookie.
- Anchors:
  - `guardian/core/auth.py:124-140`
  - `guardian/routes/admin.py:270-307`
- The DATA-tab export click path does not use the authenticated fetch helper that the rest of the frontend uses for normal API calls, so the button is only safe if browser auth state already exists in the current runtime.

## Coverage against the expected account export scope

| Data family | Status | Repo anchor(s) | Why |
|---|---|---|---|
| Chats / thread history | Partially implemented | `guardian/routes/api_exports.py:243-295`, `guardian/routes/api_exports.py:298-425`, `guardian/core/pgdb.py:2108-2184`, `guardian/core/pgdb.py:2225-2405` | There is a thread-row NDJSON export and a ChatGPT-conversation ZIP export, but no single full conversation-history export for all chat messages across the product. |
| Uploaded documents | Partially implemented | `guardian/routes/media.py:1011-1029`, `guardian/routes/media.py:1981-2000`, `guardian/routes/documents.py:457-500`, `guardian/routes/share.py:69-183`, `guardian/routes/share.py:196-320` | Documents can be uploaded, listed, linked to threads, and shared individually, but there is no bulk account export path. |
| Generated documents | Partially implemented | `guardian/routes/documents.py:307-322`, `guardian/routes/documents.py:457-500`, `guardian/routes/share.py:116-137`, `guardian/routes/share.py:296-320` | Generated docs can be created, linked to threads, and shared individually, but there is no bulk export bundle for them. |
| Uploaded images | Partially implemented | `guardian/routes/media.py:629-647`, `guardian/routes/media.py:959-983`, `guardian/routes/media.py:1887-1908` | Images can be uploaded, retrieved, and listed, but there is no account export route that packages all user-owned images. |
| Generated images | Partially implemented | `guardian/routes/media.py:1499-1510`, `guardian/routes/media.py:1887-1908` | Generated images are tracked and listable via `GET /images?tag=generated`, but there is no bulk export route. |
| Thread-linked artifacts / related media | Partially implemented | `guardian/routes/documents.py:457-500`, `guardian/routes/share.py:243-320` | Thread-document links and shareable thread/document payloads exist, but there is no unified export envelope for all linked artifacts. |

## Bug diagnosis for the reported `GET /codex` 404

- `GET /codex` is **not** the direct cause of the DATA-tab export button.
- The active export button resolves to `GET /exports/chatgpt.zip`, not `/codex`.
- The `GET /codex` 404 is therefore unrelated noise for the DATA-tab export path.
- If a separate legacy codex link is being exercised, the failure mode is route drift:
  - canonical codex routes are `/api/codex/entries`, `/api/codex/entries/{entry_id}`, and `/api/codex/entries/{entry_id}/export`
  - the compatibility aliases under `/codex/...` are gated by `CODEXIFY_ENABLE_CODEX_ROUTES`
  - anchors: `guardian/routes/codex.py:191-208`, `guardian/guardian_api.py:1047-1068`
- So the concrete issue is not "account export is broken because `/codex` 404s"; the concrete issue is that the DATA-tab export surface is only wired to a narrow export bundle and does not cover the full account scope.

## Truthful conclusion

Account Export currently is:
- a narrow authenticated download of imported ChatGPT conversations (`/exports/chatgpt.zip`)
- a separate NDJSON export of thread rows (`/exports/threads.ndjson`)
- a separate single-entry Codex markdown export

Account Export currently is not:
- a complete "extract everything I put into Codexify" feature
- a bulk export for uploaded documents, generated documents, uploaded images, generated images, or all thread-linked artifacts

Production-safety verdict for the DATA-tab export button:
- **Not production-safe as a full account-export control.**
- It only covers a subset of user-owned data and it relies on browser navigation/open-external behavior rather than a guaranteed authenticated fetch flow.

Minimum next engineering task:
- define and implement a real account-export contract that enumerates all user-owned data families, serializes them into one authenticated export artifact or job result, and includes explicit handling for thread history, docs, images, generated artifacts, and thread links.

## Search strings used
- `Import ChatGPT History`
- `Export Codexify History`
- `Import ChatGPT history`
- `Download Codexify ZIP export`
- `/exports/chatgpt.zip`
- `/api/upload-chatgpt-export`
- `/codex/entries/{entry_id}/export`
- `CODEXIFY_ENABLE_CODEX_ROUTES`

## Verification
- No automated tests apply for this investigation-only documentation task.
- Code inspection only; no runtime behavior was changed.
