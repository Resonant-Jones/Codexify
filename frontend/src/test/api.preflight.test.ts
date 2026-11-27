import { afterEach, describe, expect, it, vi } from "vitest";

import {
  default as api,
  isBackendOutageActiveForTests,
  normalizeImportRuntimeError,
  preflightBackendAvailability,
  refreshApiBaseUrl,
  createOpenAIAccountImport,
  fetchOpenAIAccountImport,
  fetchOpenAIAccountImportManifest,
  uploadOpenAIAccountImportBatch,
  commitOpenAIAccountImport,
  ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS,
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

describe("backend outage recovery", () => {
  const originalAdapter = api.defaults.adapter;

  afterEach(async () => {
    api.defaults.adapter = async (config) => ({ data: {}, status: 200, statusText: "OK", headers: {}, config });
    await api.get("/health");
    api.defaults.adapter = originalAdapter;
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    await initRuntimeConfig({ force: true });
    refreshApiBaseUrl();
  });

  it.each(["/health", "/health/chat", "/api/health/llm", "/llm/catalog"])(
    "recovers on a successful %s probe and lets the import reach the adapter",
    async (probe) => {
      vi.stubEnv("VITE_ENABLE_REQUEST_GUARD", "false");
      const adapter = vi.fn(async (config: any) => {
        if (config.url.includes("failure")) throw Object.assign(new Error("Network Error"), { config });
        return { data: {}, status: 200, statusText: "OK", headers: {}, config };
      });
      api.defaults.adapter = adapter;
      await expect(api.get("/failure")).rejects.toThrow("Network Error");
      expect(isBackendOutageActiveForTests()).toBe(true);
      await api.get(probe);
      expect(isBackendOutageActiveForTests()).toBe(false);
      await api.post("/api/imports", {});
      expect(adapter).toHaveBeenCalledTimes(3);
    }
  );

  it("does not recover on unrelated success or HTTP failure", async () => {
    vi.stubEnv("VITE_ENABLE_REQUEST_GUARD", "false");
    api.defaults.adapter = async (config) => {
      if (config.url?.includes("failure")) throw Object.assign(new Error("Network Error"), { config });
      if (config.url?.includes("health")) throw Object.assign(new Error("HTTP error"), { config, response: { status: 503 } });
      return { data: {}, status: 200, statusText: "OK", headers: {}, config };
    };
    await expect(api.get("/failure")).rejects.toThrow();
    await api.get("/assets/test.js");
    await expect(api.get("/health")).rejects.toThrow();
    expect(isBackendOutageActiveForTests()).toBe(true);
    const error = await api.post("/api/imports", {}).catch((e) => e);
    expect(error.code).toBe("ERR_BACKEND_OUTAGE_FUSE");
    expect(normalizeImportRuntimeError(error).isRuntimeUnavailable).toBe(false);
  });

  it.each([
    ["/tenant/api", "/tenant/api/health"],
    ["http://127.0.0.1:8899/tenant/api", "http://127.0.0.1:8899/tenant/api/health"],
  ])("recovers a normalized probe with configured API base %s", async (base, normalized) => {
    vi.stubEnv("VITE_ENABLE_REQUEST_GUARD", "false");
    vi.stubEnv("VITE_API_BASE_URL", base);
    await initRuntimeConfig({ force: true });
    refreshApiBaseUrl();
    const adapter = vi.fn(async (config: any) => {
      if (config.url.includes("failure")) throw Object.assign(new Error("Network Error"), { config });
      return { data: {}, status: 200, statusText: "OK", headers: {}, config };
    });
    api.defaults.adapter = adapter;
    await expect(api.get("/failure")).rejects.toThrow();
    await api.get("/health");
    expect(adapter.mock.calls[1][0].url).toBe(base.startsWith("http") ? normalized : "/health");
    if (!base.startsWith("http")) expect(adapter.mock.calls[1][0].baseURL).toBe(base);
    expect(isBackendOutageActiveForTests()).toBe(false);
    await expect(api.get("/failure")).rejects.toThrow();
    await api.get(normalized + "?probe=1");
    expect(isBackendOutageActiveForTests()).toBe(false);
    await api.post("/api/imports", {});
    expect(adapter).toHaveBeenCalledTimes(5);
  });

  it("does not clear an active fuse when an unrelated in-flight request fails", async () => {
    vi.stubEnv("VITE_ENABLE_REQUEST_GUARD", "false");
    let rejectPending!: (error: Error) => void;
    let pendingConfig: any;
    api.defaults.adapter = (config) => {
      if (config.url?.includes("pending")) {
        pendingConfig = config;
        return new Promise((_resolve, reject) => { rejectPending = reject; });
      }
      throw Object.assign(new Error("Network Error"), { config });
    };
    const pending = api.get("/pending").catch((error) => error);
    while (!rejectPending) await Promise.resolve();
    await expect(api.get("/failure")).rejects.toThrow();
    rejectPending(Object.assign(new Error("HTTP error"), { config: pendingConfig, response: { status: 400 } }));
    expect((await pending).response.status).toBe(400);
    expect(isBackendOutageActiveForTests()).toBe(true);
    await expect(api.post("/api/imports", {})).rejects.toMatchObject({ code: "ERR_BACKEND_OUTAGE_FUSE" });
  });

  it("clears the fuse after a successful fetch preflight", async () => {
    api.defaults.adapter = async (config) => { throw Object.assign(new Error("Network Error"), { config }); };
    await expect(api.get("/failure")).rejects.toThrow();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200 }));
    await expect(preflightBackendAvailability()).resolves.toEqual({ ok: true });
    expect(isBackendOutageActiveForTests()).toBe(false);
  });

  it("keeps bounded durable import requests usable when unrelated traffic relatches the fuse", async () => {
    vi.stubEnv("VITE_ENABLE_REQUEST_GUARD", "false");
    const adapter = vi.fn(async (config: any) => {
      if (config.url.includes("failure")) throw Object.assign(new Error("Network Error"), { config });
      return { data: config.url.includes("/manifest") ? { files: [] } : {}, status: 200, statusText: "OK", headers: {}, config };
    });
    api.defaults.adapter = adapter;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200 }));
    await preflightBackendAvailability();
    // A late unrelated failure can arrive during local staged-file hashing.
    await expect(api.get("/failure")).rejects.toThrow();
    expect(isBackendOutageActiveForTests()).toBe(true);
    await createOpenAIAccountImport({ source_system: "openai", total_file_count: 1, total_byte_count: 1 });
    await fetchOpenAIAccountImport("job");
    await fetchOpenAIAccountImportManifest("job");
    await uploadOpenAIAccountImportBatch("job", [{ file: new File(["a"], "a"), relativePath: "export/a" }]);
    await commitOpenAIAccountImport("job");
    const imports = adapter.mock.calls.slice(1).map(([config]) => config);
    expect(imports).toHaveLength(5);
    expect(imports.every(config => config.timeout === ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS && config.withCredentials === true)).toBe(true);
    expect(isBackendOutageActiveForTests()).toBe(true);
    await expect(api.get("/api/chat/threads")).rejects.toMatchObject({ code: "ERR_BACKEND_OUTAGE_FUSE" });
  });

  it.each([401, 403, 409])("preserves import HTTP %s without retrying or clearing the fuse", async (status) => {
    vi.stubEnv("VITE_ENABLE_REQUEST_GUARD", "false");
    const adapter = vi.fn(async (config: any) => {
      if (config.url.includes("failure")) throw Object.assign(new Error("Network Error"), { config });
      throw Object.assign(new Error("Import rejected"), { config, response: { status } });
    });
    api.defaults.adapter = adapter;
    await expect(api.get("/failure")).rejects.toThrow();
    await expect(uploadOpenAIAccountImportBatch("job", [])).rejects.toMatchObject({ response: { status } });
    expect(adapter).toHaveBeenCalledTimes(2);
    expect(isBackendOutageActiveForTests()).toBe(true);
  });

  it("keeps transport, cancellation, HTTP and client guards distinct", () => {
    expect(normalizeImportRuntimeError(new Error("Network Error")).isRuntimeUnavailable).toBe(true);
    for (const code of ["ERR_CANCELED", "ERR_CLIENT_RATE_GUARD", "ERR_BACKEND_OUTAGE_FUSE"]) {
      expect(normalizeImportRuntimeError({ code, message: "Network Error" }).isRuntimeUnavailable).toBe(false);
    }
    expect(normalizeImportRuntimeError({ response: { status: 400, data: { detail: "Invalid import" } } }).isRuntimeUnavailable).toBe(false);
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
      "/health/llm",
      "/api/health",
      "/api/health/chat",
      "/llm/catalog",
      "/api/llm/catalog",
      "http://localhost:8000/api/llm/catalog?refresh=1",
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
      "/api/health/chat/extra",
      "/api/other/health",
    ];
    for (const path of throttled) {
      expect(
        shouldClassifyBackendOutageExemptionForTests(path),
        `expected ${path} to remain subject to the fuse`
      ).toBe(true);
    }
  });
});
