import { afterEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import {
  copyTextWithFallback,
  createShareLink,
  ShareLinkApiError,
} from "@/lib/share-links";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

afterEach(() => {
  vi.clearAllMocks();
  document.body.innerHTML = "";
});

describe("createShareLink", () => {
  it("posts the thread share contract exactly once per call", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        ok: true,
        token: "tok-1",
        url: "/share/tok-1",
        expires_at: null,
      },
    });
    const result = await createShareLink("thread", 42);
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith("/api/share", {
      target_type: "thread",
      target_id: 42,
    });
    expect(result.token).toBe("tok-1");
  });

  it("posts the document share contract", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { ok: true, token: "dt", url: "/share/dt", expires_at: null },
    });
    await createShareLink("document", 7);
    expect(api.post).toHaveBeenCalledWith("/api/share", {
      target_type: "document",
      target_id: 7,
    });
  });

  it("forwards optional expiry only when positive", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { ok: true, token: "t", url: "/share/t", expires_at: null },
    });
    await createShareLink("thread", 1, 7);
    expect(api.post).toHaveBeenCalledWith("/api/share", {
      target_type: "thread",
      target_id: 1,
      expires_in_days: 7,
    });
    await createShareLink("thread", 1, null);
    expect(api.post).toHaveBeenLastCalledWith("/api/share", {
      target_type: "thread",
      target_id: 1,
    });
  });

  it("wraps failures as ShareLinkApiError with status", async () => {
    vi.mocked(api.post).mockRejectedValue({
      response: { status: 404 },
      message: "not found",
    });
    await expect(createShareLink("thread", 999)).rejects.toBeInstanceOf(
      ShareLinkApiError
    );
    await expect(createShareLink("thread", 999)).rejects.toMatchObject({
      status: 404,
    });
  });
});

describe("copyTextWithFallback", () => {
  it("prefers navigator.clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    expect(await copyTextWithFallback("https://x/share/1")).toBe("clipboard");
    expect(writeText).toHaveBeenCalledWith("https://x/share/1");
  });

  it("falls back to execCommand when clipboard rejects", async () => {
    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
      configurable: true,
    });
    const exec = vi.fn(() => true);
    Object.defineProperty(document, "execCommand", {
      value: exec,
      configurable: true,
    });
    expect(await copyTextWithFallback("url-2")).toBe("execCommand");
    expect(exec).toHaveBeenCalledWith("copy");
  });

  it("falls back to prompt when everything else is unavailable", async () => {
    Object.defineProperty(window.navigator, "clipboard", {
      value: undefined,
      configurable: true,
    });
    Object.defineProperty(document, "execCommand", {
      value: undefined,
      configurable: true,
    });
    const prompt = vi.fn();
    vi.stubGlobal("prompt", prompt);
    expect(await copyTextWithFallback("url-3")).toBe("prompt");
    expect(prompt).toHaveBeenCalledWith("Copy link:", "url-3");
    vi.unstubAllGlobals();
  });

  it("returns none when no copy mechanism exists", async () => {
    Object.defineProperty(window.navigator, "clipboard", {
      value: undefined,
      configurable: true,
    });
    Object.defineProperty(document, "execCommand", {
      value: undefined,
      configurable: true,
    });
    vi.stubGlobal("prompt", undefined);
    expect(await copyTextWithFallback("url-4")).toBe("none");
    vi.unstubAllGlobals();
  });
});
