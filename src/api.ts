// Centralized API helper for Guardian Web/Tauri
// Ensures: correct base URL, API key header, clear error messages.

const BASE = import.meta.env.VITE_GUARDIAN_API_BASE as string | undefined;
const KEY  = import.meta.env.VITE_GUARDIAN_API_KEY as string | undefined;

function assertEnv() {
  if (!BASE) {
    throw new Error(
      "[Guardian API] Missing VITE_GUARDIAN_API_BASE. Create src/.env.local with:\n" +
      "VITE_GUARDIAN_API_BASE=http://127.0.0.1:8000\n" +
      "VITE_GUARDIAN_API_KEY=<your-key>"
    );
  }
  if (!KEY) {
    throw new Error(
      "[Guardian API] Missing VITE_GUARDIAN_API_KEY. Add it to src/.env.local and restart Vite."
    );
  }
}

function normalizePath(path: string): string {
  if (!path) return "/";
  // Ensure leading slash; do not force trailing slash to avoid 307s on POST.
  return path.startsWith("/") ? path : `/${path}`;
}

async function parseMaybeJSON(res: Response) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return text || null;
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit & { raw?: boolean } = {}
): Promise<T> {
  assertEnv();

  const url = `${BASE}${normalizePath(path)}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      "accept": "application/json",
      "X-API-Key": KEY!, // FastAPI APIKeyHeader expects X-API-Key (case-insensitive, but we match docs)
      ...(init.headers || {}),
    },
  });

  if (!res.ok) {
    const body = await parseMaybeJSON(res);
    const hint =
      res.status === 401
        ? " (Unauthorized: check GUARDIAN_API_KEY on server and VITE_GUARDIAN_API_KEY in src/.env.local)"
        : res.status === 405
        ? " (Method Not Allowed: verify exact route path, no trailing slash on POST)"
        : "";
    throw new Error(
      `[Guardian API] ${res.status} ${res.statusText}${hint}\n` +
      `URL: ${url}\n` +
      (body ? `Body: ${typeof body === "string" ? body : JSON.stringify(body)}` : "")
    );
  }

  if ((init as any).raw) return (res as unknown) as T;
  const data = await parseMaybeJSON(res);
  return data as T;
}

// ——— Domain helpers ———

// Projects
export const createProject = (title: string) =>
  apiRequest<{ project_id: number }>("/projects", {
    method: "POST",
    body: JSON.stringify({ title, summary: "" }),
  });

export const deleteProject = (id: string) =>
  apiRequest<void>(`/projects/${id}`, { method: "DELETE" });

// Threads
export const createThread = (projectId: number, title: string) =>
  apiRequest<{ thread_id: number }>("/threads", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, title, summary: "" }),
  });

export const deleteThread = (id: string) =>
  apiRequest<void>(`/threads/${id}`, { method: "DELETE" });

// Chat
// Chat: backend expects { prompt, model? } and returns { reply, model_used }
export const sendChat = (threadId: string, content: string) =>
  apiRequest<{ reply: string; model_used: string }>("/chat", {
    method: "POST",
    body: JSON.stringify({ prompt: content }),
  });
