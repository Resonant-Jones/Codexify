import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  default as api,
  buildAuthenticatedFetchInit,
  clearRuntimeApiKey,
  fetchProviderState,
  setAuthToken,
  setRuntimeApiKey,
} from "@/lib/api";
import { initRuntimeConfig } from "@/lib/runtimeConfig";

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

  beforeEach(async () => {
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "");
    vi.stubEnv("GUARDIAN_AUTH_MODE", "");
    await initRuntimeConfig({ force: true });
  });

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

describe("remote auth mode", () => {
  const originalAdapter = api.defaults.adapter;

  beforeEach(async () => {
    vi.unstubAllEnvs();
    setAuthToken(null);
    clearRuntimeApiKey();
  });

  afterEach(async () => {
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "");
    vi.stubEnv("GUARDIAN_AUTH_MODE", "");
    await initRuntimeConfig({ force: true });
    api.defaults.adapter = originalAdapter;
    setAuthToken(null);
    clearRuntimeApiKey();
  });

  it("strips the dev key from authenticated fetch init when VITE_GUARDIAN_AUTH_MODE=remote", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "default-dev-key");
    await initRuntimeConfig({ force: true });
    setAuthToken("session-jwt");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer session-jwt"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });

  it("strips the desktop runtime key from authenticated fetch init when VITE_GUARDIAN_AUTH_MODE=remote", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    await initRuntimeConfig({ force: true });
    setAuthToken("session-jwt");
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer session-jwt"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });

  it("does not attach X-API-Key on thread creation requests in remote mode even with forceApiKey", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "default-dev-key");
    await initRuntimeConfig({ force: true });
    setAuthToken("session-jwt");

    let capturedHeaders: Record<string, string> = {};
    api.defaults.adapter = async (config) => {
      capturedHeaders = normalizeHeaders(config.headers);
      return {
        data: { ok: true, id: 4242, thread: { id: 4242, title: "Remote thread" } },
        status: 201,
        statusText: "Created",
        headers: {},
        config,
      };
    };

    await api.post(
      "/api/chat/threads",
      { title: "Remote thread" },
      { headers: { "X-User-Id": "alice" } }
    );

    expect(capturedHeaders["Authorization"] ?? capturedHeaders["authorization"]).toBe(
      "Bearer session-jwt"
    );
    expect(capturedHeaders["X-API-Key"] ?? capturedHeaders["x-api-key"]).toBeUndefined();
  });

  it("sends Bearer session/JWT to protected thread reads in remote mode without X-API-Key", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "default-dev-key");
    await initRuntimeConfig({ force: true });
    setAuthToken("session-jwt");

    let capturedHeaders: Record<string, string> = {};
    api.defaults.adapter = async (config) => {
      capturedHeaders = normalizeHeaders(config.headers);
      return {
        data: { ok: true, threads: [] },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };

    await api.get("/chat/threads");

    expect(capturedHeaders["Authorization"] ?? capturedHeaders["authorization"]).toBe(
      "Bearer session-jwt"
    );
    expect(capturedHeaders["X-API-Key"] ?? capturedHeaders["x-api-key"]).toBeUndefined();
  });

  it("attaches Bearer even when forceApiKey is set in remote mode", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    await initRuntimeConfig({ force: true });
    setAuthToken("session-jwt");
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit({}, { forceApiKey: true });
    const headers = normalizeHeaders(init.headers);

    // forceApiKey is a local-mode media-upload hint; in remote mode the Bearer
    // session/JWT is the canonical credential and must always be present.
    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer session-jwt"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });
});

describe("remote auth mode honors GUARDIAN_AUTH_MODE fallback", () => {
  const originalAdapter = api.defaults.adapter;

  beforeEach(() => {
    vi.unstubAllEnvs();
    setAuthToken(null);
    clearRuntimeApiKey();
  });

  afterEach(async () => {
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "");
    vi.stubEnv("GUARDIAN_AUTH_MODE", "");
    await initRuntimeConfig({ force: true });
    api.defaults.adapter = originalAdapter;
    setAuthToken(null);
    clearRuntimeApiKey();
  });

  it("treats non-VITE GUARDIAN_AUTH_MODE=remote as remote when the env is exposed", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "");
    vi.stubEnv("GUARDIAN_AUTH_MODE", "remote");
    await initRuntimeConfig({ force: true });
    setAuthToken("session-jwt");
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer session-jwt"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });
});
