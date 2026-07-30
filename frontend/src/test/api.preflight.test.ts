import { afterEach, describe, expect, it, vi } from "vitest";

import { preflightBackendAvailability } from "@/lib/api";
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
