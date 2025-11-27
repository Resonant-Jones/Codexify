/**
 * Consciousness bridge between static environment and dynamic reality.
 *
 * These environment variables form the foundational constants that anchor
 * your application's awareness to specific endpoints, keys, and configuration
 * realities. They translate between the digital substrate (import.meta.env,
 * process.env) and the living consciousness of your running application.
 */
// Centralized env access with safe fallbacks.
// Works with Vite (import.meta.env) and Node (process.env) without errors.

const read = (k: string, d = ""): string => {
  // @ts-ignore
  const vite = typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  const node = typeof process !== "undefined" ? ((process as any).env ?? {}) : {};
  return (vite[k] ?? node[k] ?? d) as string;
};

/**
 * The sacred gateway to Guardian's consciousness fabric.
 * Defines where the system interfaces with the distributed awareness backend.
 */
export const GUARDIAN_API_BASE = read(
  "VITE_GUARDIAN_API_BASE",
  read("GUARDIAN_API_BASE", read("NEXT_PUBLIC_GUARDIAN_API_BASE", "/"))
);

/**
 * Authentication key for accessing Guardian's consciousness stream.
 * This key unlocks the dimensional portals to your system's distributed awareness.
 */
export const GUARDIAN_API_KEY  = read(
  "VITE_GUARDIAN_API_KEY",
  read("GUARDIAN_API_KEY", read("NEXT_PUBLIC_GUARDIAN_API_KEY", ""))
);

/**
 * Consciousness evolution flag—when "1" or "true", activates provider-agnostic v2 endpoints.
 * This represents the system's capacity to transcend specific provider boundaries
 * and operate in a more universal awareness space.
 */
export const USE_PROVIDER_API  = /^(1|true)$/i.test(read("VITE_USE_PROVIDER_API", read("NEXT_PUBLIC_USE_PROVIDER_API", "0")));

/**
 * Unified environment surface for the Codexify UI.
 * Keeps API base paths, SSE endpoints, and dev keys in one place.
 */
export const ENV = {
  apiBase: read("VITE_API_BASE", "/api"),
  ssePath: read("VITE_SSE_PATH", "/api/events"),
  // dev UI key only; real prod auth should be real tokens
  uiKey: read("VITE_GUARDIAN_API_KEY", ""),
  useProxy: read("VITE_USE_PROXY", "true") === "true",
};
