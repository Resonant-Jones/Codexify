import axios from "axios";

function readRuntimeEnv(name: string, fallback = ""): string {
  const viteEnv =
    typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  const nodeEnv =
    typeof process !== "undefined" ? ((process as any).env ?? {}) : {};
  const raw = viteEnv[name] ?? nodeEnv[name] ?? fallback;
  return String(raw ?? "");
}

function resolveApiKey(): string {
  return readRuntimeEnv("VITE_GUARDIAN_API_KEY").trim();
}

function resolveUseProxy(): boolean {
  const raw = readRuntimeEnv("VITE_USE_PROXY", "true")
    .trim()
    .toLowerCase();
  return raw === "1" || raw === "true" || raw === "yes";
}

function toHeaderRecord(headers?: HeadersInit): Record<string, string> {
  const normalized: Record<string, string> = {};
  if (!headers) return normalized;

  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      normalized[key] = value;
    });
    return normalized;
  }

  if (Array.isArray(headers)) {
    for (const [key, value] of headers) {
      normalized[key] = value;
    }
    return normalized;
  }

  return { ...headers };
}

function hasHeader(
  headers: Record<string, string>,
  key: string
): boolean {
  const target = key.toLowerCase();
  return Object.keys(headers).some((k) => k.toLowerCase() === target);
}

export function buildAuthenticatedFetchInit(
  init: RequestInit = {},
  options: { forceApiKey?: boolean } = {}
): RequestInit {
  const headers = toHeaderRecord(init.headers);
  const apiKey = resolveApiKey();
  const shouldAttachApiKey =
    !!apiKey && (options.forceApiKey || !resolveUseProxy());

  if (shouldAttachApiKey && !hasHeader(headers, "X-API-Key")) {
    headers["X-API-Key"] = apiKey;
  }

  return {
    ...init,
    ...(Object.keys(headers).length ? { headers } : {}),
    credentials: init.credentials ?? "include",
  };
}

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
  const apiKey = resolveApiKey();

  if (apiKey) {
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
          apiKey
        );
      } else {
        (headers as Record<string, string>)["X-API-Key"] = apiKey;
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
