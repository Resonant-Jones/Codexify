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

describe("auth state", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "");
    vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", "");
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
