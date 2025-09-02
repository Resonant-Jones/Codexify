
Codex Patch — “Guardian MVP Wire-Up”

1) Frontend: always send the API key + normalize paths

A) Add env vars (Vite)

Create or update .env.local in your frontend repo:

# frontend/.env.local

VITE_GUARDIAN_API_BASE=<http://127.0.0.1:8000>
VITE_GUARDIAN_API_KEY=dev-guardian-key   # must match backend GUARDIAN_API_KEY

B) Centralize fetch (recommended)

If you have a central API helper (e.g. src/api.ts or src/lib/api.ts), make it look like this:

// src/api.ts  (or wherever your apiRequest lives)
const BASE = import.meta.env.VITE_GUARDIAN_API_BASE;
const KEY  = import.meta.env.VITE_GUARDIAN_API_KEY;

export async function apiRequest<T>(path: string, init: RequestInit & { raw?: boolean } = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      'x-api-key': KEY,                       // <— key goes out on every call
      ...(init.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (init as any).raw ? (res as any) : res.json();
}

If you don’t have a centralized helper, patch your existing calls in AppShell.tsx as follows.

C) Patch AppShell.tsx thread creation (loose threads)

In three places we create a thread without a project—desktop tile, mobile sheet tile, and the top bar plus button. Change /threads/ to /threads and add headers.

Replace each block like this:

resp = await apiRequest<{ thread_id: number }>("/threads/", {
  method: "POST",
  body: JSON.stringify({ title, summary: "" }),
});

with this:

resp = await apiRequest<{ thread_id: number }>("/threads", {
  method: "POST",
  headers: {
    "content-type": "application/json",
    "x-api-key": import.meta.env.VITE_GUARDIAN_API_KEY,
  },
  body: JSON.stringify({ title, summary: "" }),
});

(Leave createThread(parseInt(targetPid), title) alone if it already hits your project-scoped route—your helper will now inject the key automatically if you did step B.)

D) If you send chat from the UI

Wherever you call chat, ensure:

await apiRequest("/chat", {
  method: "POST",
  body: JSON.stringify({ thread_id, content }),
  // headers added automatically by apiRequest OR include block above if calling fetch directly
});

⸻

2) Backend: accept the key and align route contracts

You already run uvicorn guardian.guardian_api:app. Make sure your app verifies the key and exposes POST /threads and POST /chat (no trailing slash) since that’s what the UI now uses.

A) Set the key

In your backend env (shell, .env, or proc manager):

export GUARDIAN_API_KEY=dev-guardian-key

B) Minimal key verification dependency (FastAPI)

In guardian/guardian_api.py (or wherever your FastAPI app is defined), add:

import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Depends

API_KEY = os.environ.get("GUARDIAN_API_KEY")

def verify_api_key(x_api_key: Optional[str] = Header(None),
                   authorization: Optional[str] = Header(None)):
    key = x_api_key
    if not key and authorization and authorization.startswith("Bearer "):
        key = authorization[len("Bearer "):]
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

Then ensure your endpoints include it:

@app.post("/threads")
def create_thread(req: ThreadCreate,_=Depends(verify_api_key)):
    # existing creation logic (or call into your service)
    ...

@app.post("/chat")
def chat(req: ChatRequest, _=Depends(verify_api_key)):
    # existing chat logic
    ...

If you already have routes but only at /threads/ and /chat/, either duplicate them at the no-slash path as above or switch the UI back to those exact paths. With this patch we standardize on no trailing slash to avoid 307s.

C) CORS for browser + Tauri

Add (or verify) CORS allows your dev origins:

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

⸻

3) Quick validation

Terminal sanity checks:

# threads

curl -i -X POST <http://127.0.0.1:8000/threads> \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-guardian-key' \
  -d '{"project_id":1,"title":"New Thread"}'

# chat

curl -i -X POST <http://127.0.0.1:8000/chat> \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-guardian-key' \
  -d '{"thread_id":"1","content":"Hello Guardian"}'

You should see 200/201 and no 307/405. In your Uvicorn logs, the 401 “Unauthorized attempt with API key” line should vanish.

⸻

4) MVP readiness checklist (condensed)
 • ✅ Create thread (loose + project) works end-to-end
 • ✅ Send message returns assistant reply and persists
 • ✅ Workspace tiles read real docs list (we can flip from demo array to endpoint once you expose GET /docs?project_id=...)
 • ✅ Light/Dark unified via sheet/base tone; universal tiles everywhere
 • ✅ Auth via API key; CORS clean
