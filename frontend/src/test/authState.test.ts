import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  __resetAuthStateForTests,
  resolveAuthStateOnBoot,
  syncAuthStateFromCredentials,
  getAuthState,
} from "@/lib/authState";
import {
  clearRuntimeApiKey,
  __resetRuntimeApiKeyForTests,
  __setRuntimeApiKeyForTests,
} from "@/lib/runtimeAuth";
import { initRuntimeConfig } from "@/lib/runtimeConfig";

describe("auth state", () => {
  beforeEach(async () => {
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "");
    vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", "");
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "");
    vi.stubEnv("GUARDIAN_AUTH_MODE", "");
    await initRuntimeConfig({ force: true });
    __resetAuthStateForTests();
    __resetRuntimeApiKeyForTests();
    delete (window as any).__TAURI_IPC__;
    delete (window as any).__TAURI_INTERNALS__;
    window.sessionStorage.clear();
  });

  it("treats the packaged desktop runtime key as authenticated", () => {
    (window as any).__TAURI_IPC__ = {};
    __setRuntimeApiKeyForTests("desktop-runtime-key");

    const state = resolveAuthStateOnBoot();

    expect(state.status).toBe("authenticated");
    expect(state.ready).toBe(true);
    expect(getAuthState().status).toBe("authenticated");
  });

  it("falls back to the legacy VITE_GUARDIAN_API_KEY in local development", () => {
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "legacy-dev-key");

    const state = resolveAuthStateOnBoot();

    expect(state.status).toBe("authenticated");
    expect(state.ready).toBe(true);
  });

  it("does not treat local dev keys as authenticated in remote auth mode", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "legacy-dev-key");
    __setRuntimeApiKeyForTests("desktop-runtime-key");
    await initRuntimeConfig({ force: true });

    const state = resolveAuthStateOnBoot();

    expect(state.status).toBe("unauthenticated");
    expect(state.ready).toBe(true);
    expect(getAuthState().status).toBe("unauthenticated");
  });

  it("treats a stored session token as authenticated in remote auth mode", async () => {
    vi.stubEnv("VITE_GUARDIAN_AUTH_MODE", "remote");
    await initRuntimeConfig({ force: true });
    window.sessionStorage.setItem("guardian.auth.token", "session-jwt");

    const state = resolveAuthStateOnBoot();

    expect(state.status).toBe("authenticated");
    expect(state.ready).toBe(true);
    expect(state.token).toBe("session-jwt");
  });

  it("stays pending while desktop runtime auth is still hydrating", () => {
    (window as any).__TAURI_IPC__ = {};

    const state = resolveAuthStateOnBoot();

    expect(state.status).toBe("unknown");
    expect(state.ready).toBe(false);
  });

  it("becomes unauthenticated once hydration resolves and no key is present", () => {
    clearRuntimeApiKey();

    const state = syncAuthStateFromCredentials();

    expect(state.status).toBe("unauthenticated");
    expect(state.ready).toBe(true);
  });
});
