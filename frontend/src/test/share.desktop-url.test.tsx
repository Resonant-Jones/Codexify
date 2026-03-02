import { fireEvent, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShareButton } from "@/components/ShareButton";
import { initRuntimeConfig } from "@/lib/runtimeConfig";

const invokeMock = vi.fn();

describe("ShareButton desktop public URL", () => {
  beforeEach(async () => {
    localStorage.clear();
    delete (window as any).__TAURI_INTERNALS__;
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    localStorage.setItem("cfy.desktop.sharePublicBaseUrl", "https://public.codexify.test");
    localStorage.setItem("cfy.desktop.backendBaseUrl", "http://127.0.0.1:8888");

    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:8888",
      apiBaseUrl: "http://127.0.0.1:8888/api",
      sseUrl: "http://127.0.0.1:8888/api/events",
      sharePublicBaseUrl: "https://public.codexify.test",
      authMode: "local",
    });

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({ ok: true, url: "/share/abc123" }),
      }))
    );

    await initRuntimeConfig({ force: true });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    delete (window as any).__CFY_TAURI_CORE__;
  });

  it("copies share URL using configured public base URL", async () => {
    const { getByRole } = render(
      <ShareButton targetType="thread" targetId={12} />
    );

    fireEvent.click(getByRole("button", { name: /share/i }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "https://public.codexify.test/share/abc123"
      );
    });
  });
});
