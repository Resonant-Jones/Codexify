import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildAuthenticatedFetchInit,
  getAuthToken,
  getDevApiKey,
  setAuthToken,
} from "@/lib/api";
import {
  __resetAuthStateForTests,
  getAuthState,
  markAuthUnauthenticatedFrom401,
  resolveAuthStateOnBoot,
} from "@/lib/authState";
import {
  __resetRuntimeApiKeyForTests,
} from "@/lib/runtimeAuth";
import { initRuntimeConfig } from "@/lib/runtimeConfig";

const SESSION_TOKEN_STORAGE_KEY = "guardian.auth.token";

function normalizeHeaders(
  headers: RequestInit["headers"]
): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) {
    const normalized: Record<string, string> = {};
    headers.forEach((value, key) => {
      normalized[key] = value;
    });
    return normalized;
  }
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }
  return { ...(headers as Record<string, string>) };
}

async function prepareTransportMode(options: {
  authMode: "local" | "remote";
  devApiKey?: string;
  useProxy?: boolean;
}): Promise<void> {
  vi.unstubAllEnvs();
  vi.stubEnv("GUARDIAN_AUTH_MODE", options.authMode);
  vi.stubEnv("VITE_GUARDIAN_API_KEY", "");
  vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", options.devApiKey ?? "");
  vi.stubEnv("VITE_USE_PROXY", options.useProxy ? "true" : "false");

  delete (window as any).__TAURI_IPC__;
  delete (window as any).__TAURI_INTERNALS__;
  delete (window as any).__CFY_TAURI_CORE__;
  window.sessionStorage.clear();
  window.localStorage.clear();
  setAuthToken(null);
  __resetAuthStateForTests();
  __resetRuntimeApiKeyForTests();

  await initRuntimeConfig({ force: true });
  __resetAuthStateForTests();
}

describe("trusted remote auth transport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("session_auth_header_does_not_require_api_key", async () => {
    await prepareTransportMode({ authMode: "remote" });
    setAuthToken("session-token");

    expect(getAuthToken()).toBe("session-token");
    const headers = normalizeHeaders(buildAuthenticatedFetchInit().headers);

    expect(headers.Authorization ?? headers.authorization).toBe(
      "Bearer session-token"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });

  it("session_token_takes_precedence_over_dev_api_key_in_remote_mode", async () => {
    await prepareTransportMode({
      authMode: "remote",
      devApiKey: "legacy-dev-key",
    });
    setAuthToken("session-token");

    expect(getAuthToken()).toBe("session-token");
    const headers = normalizeHeaders(buildAuthenticatedFetchInit().headers);

    expect(headers.Authorization ?? headers.authorization).toBe(
      "Bearer session-token"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });

  it("api_key_fallback_remains_available_for_local_dev_mode", async () => {
    await prepareTransportMode({
      authMode: "local",
      devApiKey: "legacy-dev-key",
    });

    expect(getDevApiKey()).toBe("legacy-dev-key");
    const headers = normalizeHeaders(buildAuthenticatedFetchInit().headers);

    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe(
      "legacy-dev-key"
    );
    expect(headers.Authorization ?? headers.authorization).toBeUndefined();
  });

  it("remote_mode_does_not_emit_x_api_key_from_browser_env", async () => {
    await prepareTransportMode({
      authMode: "remote",
      devApiKey: "browser-env-key",
    });

    expect(getDevApiKey()).toBe("browser-env-key");
    const state = resolveAuthStateOnBoot();
    const headers = normalizeHeaders(buildAuthenticatedFetchInit());

    expect(state.status).toBe("unauthenticated");
    expect(state.ready).toBe(true);
    expect(headers.Authorization ?? headers.authorization).toBeUndefined();
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });

  it("clearing_auth_state_removes_session_credential", async () => {
    await prepareTransportMode({ authMode: "remote" });
    setAuthToken("session-token");

    expect(window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)).toBe(
      "session-token"
    );

    markAuthUnauthenticatedFrom401();

    const headers = normalizeHeaders(buildAuthenticatedFetchInit());

    expect(window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)).toBeNull();
    expect(getAuthState().status).toBe("unauthenticated");
    expect(getAuthState().ready).toBe(true);
    expect(headers.Authorization ?? headers.authorization).toBeUndefined();
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
  });
});
