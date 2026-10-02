import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import api, { getAuthToken, setAuthToken } from "@/lib/api";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
  checkAuthGate,
  getAuthState,
} from "@/lib/authState";
import {
  ACCOUNT_AUTH_FAILURE_CODES,
  ACCOUNT_AUTH_FAILURE_HEADER,
} from "@/contracts/runtimeTokens";

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

  it("does not invalidate account auth on an unclassified 401", async () => {
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "seed-token",
    });
    setAuthToken("seed-token");

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
    expect(getAuthState().status).toBe("authenticated");
    expect(getAuthState().ready).toBe(true);
    expect(getAuthToken()).toBe("seed-token");
    expect(window.sessionStorage.getItem("guardian.auth.token")).toBe(
      "seed-token"
    );
  });

  it("invalidates the account session only on the explicit account-auth signal", async () => {
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "seed-token",
    });
    setAuthToken("seed-token");

    api.defaults.adapter = async (config) =>
      Promise.reject({
        config,
        response: {
          data: { detail: "Account session required" },
          status: 401,
          statusText: "Unauthorized",
          headers: {
            [ACCOUNT_AUTH_FAILURE_HEADER.toLowerCase()]:
              ACCOUNT_AUTH_FAILURE_CODES.SESSION_INVALID,
          },
          config,
        },
      });

    await expect(api.get("/chat/threads")).rejects.toBeTruthy();
    expect(getAuthState().status).toBe("unauthenticated");
    expect(getAuthState().ready).toBe(true);
    expect(getAuthToken()).toBeNull();
    expect(window.sessionStorage.getItem("guardian.auth.token")).toBeNull();
  });
});
