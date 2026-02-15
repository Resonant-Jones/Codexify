import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import api, { setAuthToken } from "@/lib/api";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
  checkAuthGate,
  getAuthState,
} from "@/lib/authState";

describe("auth gate", () => {
  const originalAdapter = api.defaults.adapter;

  beforeEach(() => {
    __resetAuthStateForTests();
    setAuthToken(null);
  });

  afterEach(() => {
    api.defaults.adapter = originalAdapter;
    vi.restoreAllMocks();
  });

  it("blocks protected calls for unknown and unauthenticated states", () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});

    expect(
      checkAuthGate(
        { status: "unknown", ready: false },
        "session hydrate"
      )
    ).toBe(false);
    expect(
      checkAuthGate(
        { status: "unauthenticated", ready: true },
        "threads load"
      )
    ).toBe(false);
    expect(
      checkAuthGate(
        { status: "authenticated", ready: true, token: "token-1" },
        "documents list load"
      )
    ).toBe(true);

    expect(debugSpy).toHaveBeenCalled();
  });

  it("first 401 transitions auth state to unauthenticated once", async () => {
    const infoSpy = vi.spyOn(console, "info").mockImplementation(() => {});
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "seed-token",
    });

    api.defaults.adapter = async (config) =>
      Promise.reject({
        config,
        response: {
          data: { detail: "Unauthorized" },
          status: 401,
          statusText: "Unauthorized",
          headers: {},
          config,
        },
      });

    await expect(api.get("/chat/threads")).rejects.toBeTruthy();
    expect(getAuthState().status).toBe("unauthenticated");
    expect(getAuthState().ready).toBe(true);

    await expect(api.get("/chat/threads")).rejects.toBeTruthy();
    const authTransitionLogs = infoSpy.mock.calls.filter((call) =>
      String(call[0]).includes("[auth] received 401")
    );
    expect(authTransitionLogs).toHaveLength(1);
  });
});
