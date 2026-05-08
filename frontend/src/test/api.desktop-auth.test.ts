import { afterEach, describe, expect, it } from "vitest";

import {
  default as api,
  buildAuthenticatedFetchInit,
  clearRuntimeApiKey,
  fetchProviderState,
  setAuthToken,
  setRuntimeApiKey,
} from "@/lib/api";

function normalizeHeaders(headers: RequestInit["headers"]): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) {
    const out: Record<string, string> = {};
    headers.forEach((value, key) => {
      out[key] = value;
    });
    return out;
  }
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }
  return { ...(headers as Record<string, string>) };
}

describe("desktop auth headers", () => {
  const originalAdapter = api.defaults.adapter;

  afterEach(() => {
    vi.unstubAllEnvs();
    api.defaults.adapter = originalAdapter;
    setAuthToken(null);
    clearRuntimeApiKey();
  });

  it("attaches the runtime desktop key alongside bearer token when available", () => {
    setAuthToken("bearer-token");
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer bearer-token"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("desktop-key");
  });

  it("uses X-API-Key when forceApiKey is true", () => {
    setAuthToken("bearer-token");
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit({}, { forceApiKey: true });
    const headers = normalizeHeaders(init.headers);

    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("desktop-key");
    expect(headers["Authorization"] ?? headers["authorization"]).toBeUndefined();
  });

  it("uses runtime desktop API key when bearer token is absent", () => {
    setAuthToken(null);
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("desktop-key");
    expect(headers["Authorization"] ?? headers["authorization"]).toBeUndefined();
  });

  it("defaults to attaching the dev key when proxy mode is unset", () => {
    vi.unstubAllEnvs();
    setAuthToken(null);
    clearRuntimeApiKey();
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "default-dev-key");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("default-dev-key");
  });

  it("sends the runtime desktop key through the axios client even when a bearer token exists", async () => {
    setAuthToken("bearer-token");
    setRuntimeApiKey("desktop-key");

    let capturedHeaders: Record<string, string> = {};
    api.defaults.adapter = async (config) => {
      capturedHeaders = normalizeHeaders(config.headers);
      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };

    await api.get("/api/health/llm");

    expect(capturedHeaders["Authorization"] ?? capturedHeaders["authorization"]).toBe(
      "Bearer bearer-token"
    );
    expect(capturedHeaders["X-API-Key"] ?? capturedHeaders["x-api-key"]).toBe(
      "desktop-key"
    );
  });

  it("keeps the runtime desktop key on the health poll path even when a bearer token is stale", async () => {
    setAuthToken("stale-bearer-token");
    setRuntimeApiKey("desktop-key");

    let capturedHeaders: Record<string, string> = {};
    api.defaults.adapter = async (config) => {
      capturedHeaders = normalizeHeaders(config.headers);
      return {
        data: { ok: true, status: "healthy" },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };

    await api.get("/health/chat");

    expect(capturedHeaders["Authorization"] ?? capturedHeaders["authorization"]).toBe(
      "Bearer stale-bearer-token"
    );
    expect(capturedHeaders["X-API-Key"] ?? capturedHeaders["x-api-key"]).toBe(
      "desktop-key"
    );
  });

  it("attaches the runtime desktop key to create-thread requests", async () => {
    setRuntimeApiKey("desktop-key");

    let capturedHeaders: Record<string, string> = {};
    api.defaults.adapter = async (config) => {
      capturedHeaders = normalizeHeaders(config.headers);
      return {
        data: { thread_id: 123, thread: { id: 123, title: "New Thread" } },
        status: 201,
        statusText: "Created",
        headers: {},
        config,
      };
    };

    await api.post("/api/chat/threads", {
      title: "New Thread",
      user_id: "local",
    });

    expect(capturedHeaders["X-API-Key"] ?? capturedHeaders["x-api-key"]).toBe(
      "desktop-key"
    );
  });

  it("fetchProviderState uses the authenticated desktop runtime client", async () => {
    setRuntimeApiKey("desktop-key");

    let capturedHeaders: Record<string, string> = {};
    api.defaults.adapter = async (config) => {
      capturedHeaders = normalizeHeaders(config.headers);
      return {
        data: { ok: true, status: "online" },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };

    await expect(fetchProviderState()).resolves.toEqual({
      ok: true,
      status: "online",
    });
    expect(capturedHeaders["X-API-Key"] ?? capturedHeaders["x-api-key"]).toBe(
      "desktop-key"
    );
  });
});
