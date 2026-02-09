import axios from "axios";

const API_KEY = (import.meta.env.VITE_GUARDIAN_API_KEY ?? "").trim();

function resolveTimeoutMs(): number {
  const candidates = [
    import.meta.env.VITE_HTTP_TIMEOUT_MS,
    import.meta.env.VITE_API_TIMEOUT_MS,
    import.meta.env.VITE_AXIOS_TIMEOUT_MS,
  ];
  for (const raw of candidates) {
    if (raw == null || raw === "") continue;
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return parsed;
    }
  }
  return 15000;
}

const DEFAULT_TIMEOUT_MS = resolveTimeoutMs();

/**
 * Central Axios instance for the frontend.
 * Reads `VITE_API_BASE_URL` at build time; defaults to "/api".
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  withCredentials: true,
  timeout: DEFAULT_TIMEOUT_MS,
});

api.interceptors.request.use((config) => {
  if (API_KEY) {
    const headers = config.headers ?? {};
    const getHeader =
      typeof (headers as { get?: (key: string) => string | undefined }).get ===
      "function"
        ? (key: string) =>
            (headers as { get: (key: string) => string | undefined }).get(key)
        : undefined;
    const existing =
      getHeader?.("X-API-Key") ??
      getHeader?.("x-api-key") ??
      (headers as Record<string, string | undefined>)["X-API-Key"] ??
      (headers as Record<string, string | undefined>)["x-api-key"];
    if (!existing) {
      if (
        typeof (headers as { set?: (key: string, value: string) => void }).set ===
        "function"
      ) {
        (headers as { set: (key: string, value: string) => void }).set(
          "X-API-Key",
          API_KEY
        );
      } else {
        (headers as Record<string, string>)["X-API-Key"] = API_KEY;
      }
    }
    config.headers = headers;
  }
  const baseURL = String(
    config.baseURL ?? api.defaults.baseURL ?? ""
  ).replace(/\/+$/, "");
  if (
    baseURL.endsWith("/api")
    && typeof config.url === "string"
    && config.url.startsWith("/api/")
  ) {
    config.url = config.url.replace(/^\/api/, "");
  }
  return config;
});

export default api;
