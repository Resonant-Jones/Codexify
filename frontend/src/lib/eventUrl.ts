const BASE = import.meta.env.VITE_SSE_PATH ?? "/api/events";

/** Build the EventSource URL, optionally scoping to a tenant */
export function buildEventUrl(tenant?: string | null) {
  return tenant ? `${BASE}?tenant=${tenant}` : BASE;
}
