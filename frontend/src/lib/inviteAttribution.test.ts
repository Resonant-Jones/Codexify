import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createInviteAttributionResolver,
  extractInviteTokenFromHash,
} from "./inviteAttribution";

describe("invite attribution bootstrap", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/home");
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("recognizes only the exact invite fragment and decodes it", () => {
    expect(extractInviteTokenFromHash("#invite=abc%2F123")).toBe("abc/123");
    expect(extractInviteTokenFromHash("#other=abc")).toBeNull();
    expect(extractInviteTokenFromHash("#invite=abc&other=123")).toBeNull();
  });

  it("removes the fragment before posting the token in JSON", async () => {
    window.history.replaceState(null, "", "/home?tab=welcome#invite=abc%2F123");
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(window.location.hash).toBe("");
      expect(url).toBe("/api/account-observability/invites/resolve");
      expect(url).not.toContain("abc");
      expect(init?.credentials).toBe("include");
      expect(init?.method).toBe("POST");
      expect(init?.headers).toEqual({ "Content-Type": "application/json" });
      expect(JSON.parse(String(init?.body))).toEqual({ token: "abc/123" });
      return new Response(null, { status: 200 });
    });
    const resolver = createInviteAttributionResolver(window, fetchImpl);

    await resolver();

    expect(window.location.pathname + window.location.search).toBe(
      "/home?tab=welcome"
    );
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("ignores unrelated fragments without touching storage or making a request", async () => {
    window.history.replaceState(null, "", "/home#section-2");
    window.localStorage.setItem("sentinel", "local");
    window.sessionStorage.setItem("sentinel", "session");
    const fetchImpl = vi.fn();
    const resolver = createInviteAttributionResolver(window, fetchImpl);

    await resolver();

    expect(window.location.hash).toBe("#section-2");
    expect(window.localStorage.getItem("sentinel")).toBe("local");
    expect(window.sessionStorage.getItem("sentinel")).toBe("session");
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("does not log or persist the token", async () => {
    const token = "secret-token-value";
    window.history.replaceState(null, "", `/#invite=${token}`);
    const consoleSpy = vi.spyOn(console, "log");
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    const resolver = createInviteAttributionResolver(window, fetchImpl);

    await resolver();

    expect(consoleSpy).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(consoleSpy.mock.calls.flat().join(" ")).not.toContain(token);
  });

  it("treats resolution failure as non-fatal and executes once", async () => {
    window.history.replaceState(null, "", "/#invite=abc");
    const fetchImpl = vi.fn().mockRejectedValue(new Error("network down"));
    const resolver = createInviteAttributionResolver(window, fetchImpl);

    await expect(resolver()).resolves.toBeUndefined();
    await resolver();

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe("");
  });
});
