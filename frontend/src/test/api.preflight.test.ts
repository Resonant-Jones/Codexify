import { afterEach, describe, expect, it, vi } from "vitest";

import {
  preflightBackendAvailability,
  shouldClassifyBackendOutageExemptionForTests,
} from "@/lib/api";
import { initRuntimeConfig } from "@/lib/runtimeConfig";

describe("backend availability preflight", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("probes the backend configured by runtime config", async () => {
    vi.stubEnv("VITE_GUARDIAN_API_BASE", "http://127.0.0.1:8899");
    await initRuntimeConfig({ force: true });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);

    await expect(preflightBackendAvailability()).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8899/health",
      expect.objectContaining({ credentials: "include" })
    );
  });
});

describe("backend outage fuse classification", () => {
  it("exempts canonical health and catalog probes from the backend outage fuse", () => {
    const exempt = [
      "/health",
      "/health/",
      "/health?probe=1",
      "/health/chat",
      "/health/chat?probe=1",
      "/api/health/llm",
      "/api/health/llm?probe=1",
      "/llm/catalog",
      "/llm/catalog?refresh=1",
    ];
    for (const path of exempt) {
      expect(
        shouldClassifyBackendOutageExemptionForTests(path),
        `expected ${path} to bypass the fuse`
      ).toBe(false);
    }
  });

  it("still applies the fuse to non-canonical chat and asset paths", () => {
    const throttled = [
      "/api/chat/42/complete",
      "/api/threads/1/messages",
      "/api/projects/1",
      "/api/system_docs",
      "/api/ui/session",
      "/api/system_prompt/summary",
    ];
    for (const path of throttled) {
      expect(
        shouldClassifyBackendOutageExemptionForTests(path),
        `expected ${path} to remain subject to the fuse`
      ).toBe(true);
    }
  });
});