# DCW Starter → Backend Integration Guide

This guide shows exactly where to swap the starter’s local stubs for your real backend. It keeps the Save ritual untouched while replacing storage, auth, and routing with your services.

---

## Integration Surfaces (tl;dr)

- **Save ritual** → replace stub in `useSaveRitual.ts`

- **Project list / pins** → wire to your Projects API

- **Assets** → Library data provider

- **Auth** → token source + IPC header injector (if needed)

- **Telemetry** → optional event sink (opt‑in only)

---

## 1) Save Ritual → your Notes/Content API

Starter location:

```
apps/dcw-desktop-starter/src/hooks/useSaveRitual.ts
```

Replace the stubbed `post()` calls with your client (REST/GraphQL). Minimal contract:

```ts
// expected by the UI
type SaveResponse = { noteId: string; path: string };

async function savePrimary(payload: { turns: { threadId: string; turnIndex: number }[]; markdown: string }): Promise<SaveResponse> {
  const res = await api.notes.ingest({
    projectId: ui.projectId,
    content: payload.markdown,
    mode: 'append', // or 'create'
    appendPolicy: 'daily'
  });
  return { noteId: res.id, path: res.path };
}
```

If you need to keep the Tauri/IPC boundary, wrap your HTTP client inside an IPC command (Rust → fetch) or do HTTP directly in the renderer. For stricter security, use IPC.

**Rust command (optional):**

```rust
#[tauri::command]
async fn ingest_note(target_project_id: String, content: String, mode: String) -> Result<String, String> {
    // call your backend here (reqwest)
    // return note path or id
}
```

---

## 2) Projects & Pins → your Projects API

Locations:

```
apps/dcw-desktop-starter/src/state/pinsStore.ts
apps/dcw-desktop-starter/src/views/SettingsView.tsx
```

- Replace local `pinnedProjectIds` with values from your user profile endpoint.

- On change, call `PUT /users/:id/pins` (or your equivalent) and optimistic‑update the store.

- `PinsPopover.tsx` expects `{ id, name, lastNoteTitle? }` — hydrate from `/projects` and `/projects/:id/notes?limit=1`.

---

## 3) Assets (Library) → your Files/Media API

Location:

```
apps/dcw-desktop-starter/src/views/LibraryView.tsx
```

- Swap the fake `get_recent_assets()` with your provider (S3, Supabase, local FS, etc.).

- Return `{ id, kind, name, previewUrl, updatedAt }` to populate the thumbstrip and grid.

---

## 4) Auth Strategy

- **Renderer HTTP**: Use your existing client with tokens from secure storage (Keychain via Tauri plugin) and attach headers in interceptors.

- **IPC/Rust HTTP**: Store tokens securely in the keychain; inject auth in Rust when calling your backend.

- On logout, purge tokens, pins, and cached notes.

---

## 5) Telemetry (Opt‑In Only)

Location:

```
apps/dcw-desktop-starter/src/lib/telemetry.ts
```

- Replace console logging with your analytics sink if the user has opted in.

- Suggested minimal schema:

```ts
track('save.primary', { projectId, path, ms });
track('save.undo');
track('pins.opened');
track('time_to_save', { ms });
```

- Provide Settings → Privacy toggle that gates all `track()` calls.

---

## 6) URL/Deep Links (optional)

- If your backend sends links back into the app, define a custom scheme like `codexify://?mode=Codexify&sel=thread:abc123`.

- Tauri can register protocol handlers; in web builds fall back to `https://app.example.com/?…`.

---

## 7) Error & Offline Behavior

- Map backend errors to user‑legible snackbars. Keep **Undo** local when possible.

- Queue saves offline (local file or IndexedDB) and replay when online.

- Idempotence key on the client: `hash(threadId, turnIndex, targetPath)`.

---

## 8) Type Contracts (drop‑in)

```ts
// dcw-core/types.ts
export interface ProjectMeta { id: string; name: string; color?: string }
export interface NoteIngestRequest { projectId: string; content: string; mode: 'append'|'create'; appendPolicy?: 'daily'|'namedSection'|'bottom' }
export interface NoteIngestResponse { id: string; path: string }
export interface AssetMeta { id: string; kind: 'file'|'image'|'audio'|'model'; name: string; previewUrl?: string; updatedAt: string }
```

Use these in both the frontend and your backend client to avoid drift.

---

## 9) Minimal wiring example (REST)

```ts
// dcw-services/api.ts
import { NoteIngestRequest, NoteIngestResponse } from 'dcw-core/types';

export async function ingestNote(body: NoteIngestRequest, token: string): Promise<NoteIngestResponse> {
  const res = await fetch(`${BASE}/notes/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

Then in `useSaveRitual.ts`:

```ts
import { ingestNote } from 'dcw-services/api';
const token = await getToken();
await ingestNote({ projectId, content, mode: 'append', appendPolicy: 'daily' }, token);
```

---

## 10) Checklist for “connected” status

-  Save writes to your backend and returns a real path/ID

-  Pins load from and persist to user profile

-  Library lists real assets

-  Auth tokens stored securely and refreshed

-  Telemetry only fires when opted in

---

