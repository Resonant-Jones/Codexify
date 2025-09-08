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

export const Threads = {
  list: () => req('/threads'),
  get: (id: string) => req(`/thread/${id}`),
  children: (id: string) => req(`/thread/${id}/children`),
  summary: (id: string) => req(`/thread/${id}/summary`),
  create: (body: { summary?: string; title?: string; project_id?: string | null }) =>
    req('/threads', { method: 'POST', body: JSON.stringify(body) }),
  del: (id: number | string) => req(`/thread/${id}`, { method: 'DELETE' })
};
export const Projects = {
  list: () => req('/projects'),
  create: (body: { name: string; description?: string }) =>
    req('/projects', { method: 'POST', body: JSON.stringify(body) }),
  del: (id: number | string) => req(`/projects/${id}`, { method: 'DELETE' })
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
  execute:(b:any)=>req('/tools/execute',{method:'POST',body:JSON.stringify(b)}),
  job:(id:string)=>req(`/jobs/${id}`)
};
