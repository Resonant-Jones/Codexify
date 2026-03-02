import { afterEach, describe, expect, it } from "vitest";

import {
  buildAuthenticatedFetchInit,
  clearRuntimeApiKey,
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
  afterEach(() => {
    setAuthToken(null);
    clearRuntimeApiKey();
  });

  it("prefers bearer token when forceApiKey is not set", () => {
    setAuthToken("bearer-token");
    setRuntimeApiKey("desktop-key");

    const init = buildAuthenticatedFetchInit();
    const headers = normalizeHeaders(init.headers);

    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer bearer-token"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
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
});
