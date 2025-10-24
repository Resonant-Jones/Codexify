import { GUARDIAN_API_BASE, GUARDIAN_API_KEY, USE_PROVIDER_API, ENV } from "./env";
import { getPreferredProvider } from "./providerPref";
import { combineBaseAndPath } from "./urlJoin";

type ChatSyncReq = { prompt: string; provider?: string; model?: string; temperature?: number; top_p?: number; max_tokens?: number; };
type ChatSyncRes = { provider: string; model: string | null; text: string };

type EmbedReq = { texts: string[]; embedder?: string; model?: string };
type EmbedRes = { provider: string; model: string | null; vectors: number[][] };

type Capabilities = { chat: string[]; embeddings: string[] };

const headers = () => ({
  "Content-Type": "application/json",
  ...(GUARDIAN_API_KEY ? { "X-API-Key": GUARDIAN_API_KEY } : {}),
});

// Build a base that works in both dev (Vite) and prod.
// - If GUARDIAN_API_BASE is an absolute URL, use it directly.
// - If it's empty or "/", fall back to ENV.apiBase (defaults to "/api" for Vite proxy).
// - Otherwise, use GUARDIAN_API_BASE as-is.
const base = (path: string) => {
  const b = GUARDIAN_API_BASE || "/";
  const isAbs = /^https?:\/\//i.test(b);
  const chosen = isAbs ? b : (b === "/" ? (ENV.apiBase || "/api") : b);
  return combineBaseAndPath(chosen, path);
};

// If a provider wasn't explicitly set, default to the persisted preference.
const withDefaultProvider = <T extends { provider?: string }>(body: T): T & { provider?: string } => {
  try {
    const persisted = getPreferredProvider();
    const provider = body.provider ?? (persisted ?? undefined);
    return { ...body, provider } as any;
  } catch {
    return body as any;
  }
};

// --- v2 (provider-agnostic) endpoints
const v2 = {
  get: async <T = unknown>(path: string): Promise<T> => {
    const res = await fetch(base(path), { headers: headers() });
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json();
  },
  capabilities: async (): Promise<Capabilities> => {
    const r = await fetch(base("/capabilities"), { headers: headers() });
    if (!r.ok) throw new Error(`capabilities failed: ${r.status}`);
    return r.json();
  },
  chat: async (body: ChatSyncReq): Promise<ChatSyncRes> => {
    const r = await fetch(base("/chat"), { method: "POST", headers: headers(), body: JSON.stringify(withDefaultProvider(body)) });
    if (!r.ok) throw new Error(`chat failed: ${r.status}`);
    return r.json();
  },
  chatStream: (
    q: ChatSyncReq & { signal?: AbortSignal },
    onToken: (t: string) => void,
    onDone?: (error?: unknown) => void,
  ): (() => void) => {
    const { signal, ...rest } = q;
    const qWithDefault = withDefaultProvider({ ...rest });
    const qs = new URLSearchParams();
    Object.entries(qWithDefault).forEach(([k, v]) => (v !== undefined && v !== null) && qs.append(k, String(v)));
    const url = `${base("/chat/stream")}?${qs.toString()}`;
    const ctrl = new AbortController();
    const s = signal ?? ctrl.signal;

    // SSE via fetch reader—simple and dependency-free
    fetch(url, { headers: headers(), signal: s })
      .then(async (res) => {
        if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx: number;
          while ((idx = buf.indexOf("\n\n")) >= 0) {
            const frame = buf.slice(0, idx).trim();
            buf = buf.slice(idx + 2);
            if (frame.startsWith("data: ")) {
              const payload = frame.slice(6);
              if (payload !== "[DONE]") onToken(payload);
            }
          }
        }
      })
      .then(() => onDone?.())
      .catch((err) => {
        onDone?.(err);
      });

    return () => ctrl.abort();
  },
  embeddings: async (body: EmbedReq): Promise<EmbedRes> => {
    const r = await fetch(base("/embeddings"), { method: "POST", headers: headers(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`embeddings failed: ${r.status}`);
    return r.json();
  },
};

// --- v1 fallback (fill these to match your legacy routes if still needed)
const v1 = {
  get: async <T = unknown>(path: string): Promise<T> => {
    const res = await fetch(base(path), { headers: headers() });
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json();
  },
  capabilities: async (): Promise<Capabilities> => ({ chat: [], embeddings: [] }),
  chat: async (body: ChatSyncReq): Promise<ChatSyncRes> => {
    // Example: adjust to your old route if different
    const r = await fetch(base("/chat"), { method: "POST", headers: headers(), body: JSON.stringify({ prompt: body.prompt }) });
    if (!r.ok) throw new Error(`v1 chat failed: ${r.status}`);
    const text = await r.text();
    return { provider: "legacy", model: null, text };
  },
  chatStream: (
    q: ChatSyncReq & { signal?: AbortSignal },
    onToken: (t: string) => void,
    onDone?: (error?: unknown) => void,
  ): (() => void) => {
    // If v1 had no stream, emulate by calling sync once
    let stopped = false;
    v1.chat(q)
      .then((res) => {
        if (!stopped) onToken(res.text);
      })
      .then(() => onDone?.())
      .catch((err) => {
        if (!stopped) onDone?.(err);
      });
    return () => {
      stopped = true;
    };
  },
  embeddings: async (_: EmbedReq): Promise<EmbedRes> => ({ provider: "legacy", model: null, vectors: [] }),
};

export const GuardianAPI = USE_PROVIDER_API ? v2 : v1;
