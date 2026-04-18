import { invokeCommandBus, type CommandBusInvokeResponse } from "@/lib/api";

// Lightweight client for Guardian Codex API (+ action layer)
let BASE = import.meta.env.VITE_GC_BASE || 'http://127.0.0.1:8000';
let TOKEN = '';
export function configureGC({ base, token }: { base?: string; token?: string }) {
  if (base) BASE = base; if (token) TOKEN = token;
}
export function setToken(t: string) { TOKEN = t; }

async function req(p: string, init: RequestInit = {}, attempt = 0): Promise<any> {
  const res = await fetch(`${BASE}${p}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
      ...(TOKEN ? { 'X-API-Key': TOKEN } : {})
    }
  });
  if (res.status===429 || (res.status>=500 && res.status<600)) {
    if (attempt<3) { await new Promise(r=>setTimeout(r, 400*(attempt+1))); return req(p,init,attempt+1); }
  }
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get('content-type')||''; return ct.includes('json') ? res.json() : res.text();
}
// Back-compat: some callers import { request } from this module
export { req as request };

type LegacyToolJobSnapshot = {
  state: string;
  result?: any;
};

const JOB_CACHE = new Map<string, LegacyToolJobSnapshot>();

function normalizeJobState(status: string | undefined): string {
  const normalized = String(status ?? "").trim().toLowerCase();
  if (normalized === "completed") return "completed";
  if (normalized === "failed") return "failed";
  if (normalized === "blocked" || normalized === "denied") {
    return "failed";
  }
  if (normalized === "planned" || normalized === "queued") return "running";
  if (normalized === "running") return "running";
  return normalized || "failed";
}

function normalizeJobResult(
  response: CommandBusInvokeResponse,
  state: string
): any {
  if (state === "completed") {
    return response.inline_result ?? {};
  }
  return response.error ?? response.inline_result ?? {};
}

async function executeCommandBusTool(
  commandId: string,
  args: Record<string, any>
): Promise<{ jobId: string; state: string; result?: any }> {
  const response = await invokeCommandBus({
    invoke_version: "1.0",
    command_id: commandId,
    actor: {
      kind: "human",
      id: "local",
    },
    arguments: {
      body: args,
    },
  });

  const jobId = String(response.run_id ?? "").trim();
  const state = normalizeJobState(response.status);
  const result = normalizeJobResult(response, state);
  if (jobId) {
    JOB_CACHE.set(jobId, { state, result });
  }
  return { jobId, state, result };
}

export const Threads = {
  list: () => req('/threads'),
  get: (id: string) => req(`/threads/${id}`),
  children: (id: string) => req(`/thread/${id}/children`),
  summary: (id: string) => req(`/threads/${id}/summary`),
  create: (body: { summary?: string; title?: string; project_id?: string | null }) =>
    req('/threads', { method: 'POST', body: JSON.stringify(body) }),
  del: (id: number | string) => req(`/threads/${id}`, { method: 'DELETE' })
};
export const Projects = {
  list: () => req('/api/projects'),
  create: (body: { name: string; description?: string }) =>
    req('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  del: (id: number | string) => req(`/api/projects/${id}`, { method: 'DELETE' })
};
export const Notes = {
  log:(b:any)=>req('/log',{method:'POST',body:JSON.stringify(b)}),
  summarize:(b:any)=>req('/summarize',{method:'POST',body:JSON.stringify(b)}),
  codexify:(b:any)=>req('/codexify',{method:'POST',body:JSON.stringify(b)})
};
export const Agent = {
  whoami:()=>req('/whoami'), updateProfile:(b:any)=>req('/profile',{method:'POST',body:JSON.stringify(b)})
};
export const Tools = {
  execute: async (body: { type: string; args: Record<string, any> }) => {
    const execution = await executeCommandBusTool(body.type, body.args);
    return { jobId: execution.jobId, state: execution.state, result: execution.result };
  },
  job: async (id: string) => {
    const snapshot = JOB_CACHE.get(id);
    if (!snapshot) {
      throw new Error(`job_not_found:${id}`);
    }
    return { state: snapshot.state, result: snapshot.result };
  }
};
