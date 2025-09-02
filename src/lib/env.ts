// Centralized env access with safe fallbacks.
// Works with Vite (import.meta.env) and Node (process.env) without errors.

const read = (k: string, d = ""): string => {
  // @ts-ignore
  const vite = typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  const node = typeof process !== "undefined" ? ((process as any).env ?? {}) : {};
  return (vite[k] ?? node[k] ?? d) as string;
};

export const GUARDIAN_API_BASE = read("VITE_GUARDIAN_API_BASE", read("NEXT_PUBLIC_GUARDIAN_API_BASE", "/"));
export const GUARDIAN_API_KEY  = read("VITE_GUARDIAN_API_KEY", read("NEXT_PUBLIC_GUARDIAN_API_KEY", ""));
// Feature flag: when "1" or "true", use provider-agnostic v2 endpoints.
export const USE_PROVIDER_API  = /^(1|true)$/i.test(read("VITE_USE_PROVIDER_API", read("NEXT_PUBLIC_USE_PROVIDER_API", "0")));

