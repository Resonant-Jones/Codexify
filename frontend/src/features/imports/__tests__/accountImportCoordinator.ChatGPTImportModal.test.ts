import { waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  preflight: vi.fn(),
  create: vi.fn(),
  upload: vi.fn(),
  commit: vi.fn(),
  fetch: vi.fn(),
  manifest: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  preflightBackendAvailability: apiMocks.preflight,
  createOpenAIAccountImport: apiMocks.create,
  uploadOpenAIAccountImportBatch: apiMocks.upload,
  commitOpenAIAccountImport: apiMocks.commit,
  fetchOpenAIAccountImport: apiMocks.fetch,
  fetchOpenAIAccountImportManifest: apiMocks.manifest,
  normalizeImportRuntimeError: (error: unknown) => ({
    message: error instanceof Error ? error.message : "Import failed",
    technicalDetail: null,
  }),
}));

function job(status: "receiving" | "queued" = "receiving") {
  return {
    job_id: "job-restore",
    source_system: "openai",
    status,
    total_file_count: 2,
    total_byte_count: 5,
    uploaded_file_count: status === "receiving" ? 0 : 2,
    uploaded_byte_count: status === "receiving" ? 0 : 5,
    imported_thread_count: 0,
    imported_message_count: 0,
    imported_media_count: 0,
    duplicate_count: 0,
    skipped_count: 0,
    warning_count: 0,
    failure_count: 0,
    warning_details: [],
    error_details: [],
  };
}

function jobForSource(sourceSystem: "openai" | "anthropic") {
  return {
    ...job(),
    source_system: sourceSystem,
  };
}

describe("account import coordinator continuity", () => {
  beforeEach(() => {
    vi.resetModules();
    Object.defineProperty(navigator, "locks", { configurable: true, value: {
      request: vi.fn(async (_name, _options, callback) => callback({ name: "test" })),
    } });
    apiMocks.manifest.mockReset();
    window.localStorage.clear();
    apiMocks.preflight.mockReset().mockResolvedValue({ ok: true });
    apiMocks.create.mockReset().mockImplementation((declaration: {
      source_system?: "openai" | "anthropic";
    }) =>
      jobForSource(
        declaration?.source_system === "anthropic" ? "anthropic" : "openai"
      )
    );
    apiMocks.upload.mockReset().mockImplementation((jobId: string) => ({
      ...job(),
      job_id: jobId,
      uploaded_file_count: 2,
      uploaded_byte_count: 5,
    }));
    apiMocks.commit.mockReset().mockImplementation((jobId: string) => ({
      ...job("queued"),
      job_id: jobId,
    }));
    apiMocks.fetch.mockReset().mockResolvedValue(job("queued"));
  });

  it("keeps account identity out of create, transfer, commit, and polling", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
      { file: new File(["png"], "image.png"), relativePath: "export/media/image.png" },
    ];

    await coordinator.startOpenAIAccountImport(files);

    expect(apiMocks.create).toHaveBeenCalledWith({
      total_file_count: 2,
      total_byte_count: 5,
      source_system: "openai",
    });
    expect(apiMocks.upload).toHaveBeenCalledWith("job-restore", files, expect.any(AbortSignal));
    expect(apiMocks.commit).toHaveBeenCalledWith("job-restore");
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe(
      "accepted"
    );
    await new Promise((resolve) => setTimeout(resolve, 1600));
    expect(apiMocks.fetch).toHaveBeenCalledWith("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("explicitly serializes source_system=anthropic when requested", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
    ];

    await coordinator.startOpenAIAccountImport(files, "anthropic");

    expect(apiMocks.create).toHaveBeenCalledWith({
      total_file_count: 1,
      total_byte_count: 2,
      source_system: "anthropic",
    });
    expect(apiMocks.upload).toHaveBeenCalledWith("job-restore", files, expect.any(AbortSignal));
    expect(apiMocks.commit).toHaveBeenCalledWith("job-restore");
    // The request contract is the authoritative surface for this test: the
    // create call must explicitly serialize source_system="anthropic".
    const createCall = apiMocks.create.mock.calls[0]?.[0] as Record<
      string,
      unknown
    >;
    expect(createCall?.source_system).toBe("anthropic");
    expect("origin_system" in createCall).toBe(false);
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("refuses to start a different source while another is active", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
    ];

    await coordinator.startOpenAIAccountImport(files, "openai");

    await expect(
      coordinator.startOpenAIAccountImport(files, "anthropic")
    ).rejects.toThrow(/already active for openai/);
    expect(apiMocks.create).toHaveBeenCalledTimes(1);
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("restores the persisted source_system across transient UI states", async () => {
    window.localStorage.setItem(
      "cfy.accountImport:v1",
      JSON.stringify({
        v: 1,
        jobId: "anthropic-restore",
        status: "queued",
        sourceSystem: "anthropic",
      })
    );
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    expect(
      coordinator.getAccountImportCoordinatorSnapshot().job?.source_system
    ).toBe("anthropic");
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("rejects a noncanonical persisted source without surfacing it", async () => {
    window.localStorage.setItem(
      "cfy.accountImport:v1",
      JSON.stringify({
        v: 1,
        jobId: "legacy-source",
        status: "queued",
        sourceSystem: "claude",
      })
    );
    apiMocks.fetch.mockResolvedValue({
      ...job("queued"),
      job_id: "legacy-source",
      source_system: "anthropic",
    });
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    const initialSnapshot = coordinator.getAccountImportCoordinatorSnapshot();
    expect(initialSnapshot.job?.source_system).toBeUndefined();
    // Server fetch re-establishes canonical source-of-truth.
    await waitFor(() =>
      expect(coordinator.getAccountImportCoordinatorSnapshot().job?.source_system).toBe(
        "anthropic"
      )
    );
    expect(apiMocks.fetch).toHaveBeenCalledWith("legacy-source");
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("does not assign canonical conversation origin_system on the Web", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
    ];
    await coordinator.startOpenAIAccountImport(files, "anthropic");
    const call = apiMocks.create.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(call).toBeDefined();
    expect("origin_system" in call).toBe(false);
    // The coordinator itself must not invent an origin_system either.
    const snapshot = coordinator.getAccountImportCoordinatorSnapshot();
    expect("origin_system" in (snapshot.job as object)).toBe(false);
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("normalizes decomposed Unicode paths before staging", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    expect(coordinator.normalizeBrowserRelativePath("media/cafe\u0301.png")).toBe(
      "media/café.png"
    );
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("checks server truth before treating a cached receiving job as unfinished", async () => {
    window.localStorage.setItem(
      "cfy.accountImport:v1",
      JSON.stringify({ v: 1, jobId: "job-restore", status: "receiving" })
    );
    apiMocks.fetch.mockResolvedValue(job("queued"));
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    coordinator.getAccountImportCoordinatorSnapshot();

    await waitFor(() =>
      expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe(
        "accepted"
      )
    );
    expect(apiMocks.fetch).toHaveBeenCalledWith("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("stops polling and clears stale reference on HTTP 404", async () => {
    vi.useFakeTimers();

    window.localStorage.setItem(
      "cfy.accountImport:v1",
      JSON.stringify({ v: 1, jobId: "stale-404-job", status: "queued" })
    );

    apiMocks.fetch.mockRejectedValue({
      response: { status: 404 },
    });

    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    coordinator.getAccountImportCoordinatorSnapshot();

    await vi.runAllTimersAsync();

    const snap = coordinator.getAccountImportCoordinatorSnapshot();
    expect(snap.phase).toBe("failed");
    expect(snap.job).toBeNull();
    expect(snap.error).toMatch(/no longer available/);
    expect(snap.error).not.toContain("[object Object]");
    expect(snap.technicalDetail).toMatch(/HTTP 404/);
    expect(snap.technicalDetail).toMatch(/stale-404-job/);

    expect(window.localStorage.getItem("cfy.accountImport:v1")).toBeNull();
    expect(apiMocks.fetch).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetch).toHaveBeenCalledWith("stale-404-job");

    // Advance well past multiple polling intervals — no further calls.
    await vi.advanceTimersByTimeAsync(5000);
    expect(apiMocks.fetch).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("reports a genuinely unfinished restored transfer without claiming acceptance", async () => {
    window.localStorage.setItem(
      "cfy.accountImport:v1",
      JSON.stringify({ v: 1, jobId: "job-restore", status: "receiving" })
    );
    apiMocks.fetch.mockResolvedValue(job("receiving"));
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    coordinator.getAccountImportCoordinatorSnapshot();

    await waitFor(() =>
      expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe(
        "failed"
      )
    );
    expect(coordinator.getAccountImportCoordinatorSnapshot().error).toMatch(
      /before server queue acceptance/
    );
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("renders a zero-write terminal result as failed, not completed", async () => {
    window.localStorage.setItem(
      "cfy.accountImport:v1",
      JSON.stringify({ v: 1, jobId: "zero-write-job", status: "queued" })
    );
    apiMocks.fetch.mockResolvedValue({
      ...job("queued"),
      job_id: "zero-write-job",
      status: "failed",
      error_details: [
        {
          code: "account_import_no_committed_entities",
          message:
            "The export finished processing, but no canonical entities were committed.",
        },
      ],
    });
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );

    coordinator.getAccountImportCoordinatorSnapshot();

    await waitFor(() =>
      expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe(
        "failed"
      )
    );
    const snap = coordinator.getAccountImportCoordinatorSnapshot();
    expect(snap.error).toMatch(/no canonical entities were committed/);
    expect(snap.phase).not.toBe("completed");
    coordinator.resetAccountImportCoordinatorForTests();
  });
});


describe("account import same-job recovery", () => {
  const file = (name: string, content: string) => {
    const value = new File([content], name);
    Object.defineProperty(value, "arrayBuffer", { value: async () => new TextEncoder().encode(content).buffer });
    return { file: value, relativePath: `export/${name}` };
  };
  async function restored() {
    const { webcrypto } = await import("node:crypto");
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
    window.localStorage.setItem("cfy.accountImport:v1", JSON.stringify({ v: 1, jobId: "job-restore", status: "receiving", sourceSystem: "openai" }));
    apiMocks.fetch.mockResolvedValue(job());
    const coordinator = await import("@/features/imports/accountImportCoordinator");
    coordinator.getAccountImportCoordinatorSnapshot();
    await waitFor(() => expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed"));
    return coordinator;
  }
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    window.localStorage.clear();
    Object.defineProperty(navigator, "locks", { configurable: true, value: {
      request: vi.fn(async (_name, _options, callback) => callback({ name: "test" })),
    } });
    apiMocks.preflight.mockReset().mockResolvedValue({ ok: true });
    apiMocks.create.mockReset().mockResolvedValue(job());
    apiMocks.upload.mockReset().mockResolvedValue({ ...job(), uploaded_file_count: 2, uploaded_byte_count: 5 });
    apiMocks.commit.mockReset().mockResolvedValue(job("queued"));
    apiMocks.manifest.mockReset().mockResolvedValue({
      ...job(), files: [{ path: "export/conversations.json", size: 2,
        sha256: "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945" }],
    });
  });
  it("verifies hashes and uploads only missing files into the same job", async () => {
    const coordinator = await restored();
    const missing = file("image.png", "png");
    await coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), missing]);
    expect(apiMocks.create).not.toHaveBeenCalled();
    expect(apiMocks.upload).toHaveBeenCalledWith("job-restore", [missing], expect.any(AbortSignal));
    expect(apiMocks.commit).toHaveBeenCalledTimes(1);
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("shows aggregate progress and times out an unreadable selected file without uploading", async () => {
    const coordinator = await restored();
    const stuck = file("conversations.json", "[]");
    // Use a file-like wrapper to model a browser file read that never resolves.
    const selected = { ...stuck, file: { size: 2, arrayBuffer: () => new Promise<ArrayBuffer>(() => {}) } as File };
    vi.useFakeTimers();
    const result = coordinator.startOpenAIAccountImport([selected, file("image.png", "png")]);
    const rejected = expect(result).rejects.toThrow(/timed out while reading/);
    await vi.waitFor(() => expect(coordinator.getAccountImportCoordinatorSnapshot().verification?.stage).toBe("reading"));
    expect(coordinator.getAccountImportCoordinatorSnapshot().verification).toMatchObject({ completed: 0, total: 1, bytes: 0, totalBytes: 2 });
    await vi.advanceTimersByTimeAsync(coordinator.ACCOUNT_IMPORT_VERIFY_STEP_TIMEOUT_MS);
    await rejected;
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
    vi.useRealTimers();
  });
  it("times out hashing and ignores its late completion", async () => {
    const coordinator = await restored();
    let finish!: (value: ArrayBuffer) => void;
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: { subtle: { digest: () => new Promise<ArrayBuffer>(resolve => { finish = resolve; }) } } });
    vi.useFakeTimers();
    const result = coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")]);
    const rejected = expect(result).rejects.toThrow(/timed out while hashing/);
    await vi.waitFor(() => expect(coordinator.getAccountImportCoordinatorSnapshot().verification?.stage).toBe("hashing"));
    await vi.advanceTimersByTimeAsync(coordinator.ACCOUNT_IMPORT_VERIFY_STEP_TIMEOUT_MS);
    await rejected;
    finish(new ArrayBuffer(32));
    await Promise.resolve();
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed");
    coordinator.resetAccountImportCoordinatorForTests();
    vi.useRealTimers();
  });
  it("stops a pending local read on reset without waiting for its deadline", async () => {
    const coordinator = await restored();
    const selected = { relativePath: "export/conversations.json", file: { size: 2, arrayBuffer: () => new Promise<ArrayBuffer>(() => {}) } as File };
    const result = coordinator.startOpenAIAccountImport([selected, file("image.png", "png")]);
    const rejected = expect(result).rejects.toThrow(/stopped/);
    await waitFor(() => expect(coordinator.getAccountImportCoordinatorSnapshot().verification?.stage).toBe("reading"));
    coordinator.clearAccountImportCoordinatorResult();
    await rejected;
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("idle");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("redacts local file errors and retains the staged job", async () => {
    const coordinator = await restored();
    const selected = { relativePath: "export/conversations.json", file: { size: 2, arrayBuffer: () => Promise.reject(new Error("private filename or payload")) } as File };
    await expect(coordinator.startOpenAIAccountImport([selected, file("image.png", "png")])).rejects.toThrow(/failed while reading/);
    expect(coordinator.getAccountImportCoordinatorSnapshot().error).not.toContain("private filename");
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("rejects changed content before uploading or committing", async () => {
    const coordinator = await restored();
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "{}"), file("image.png", "png")])).rejects.toThrow(/conflicts/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(apiMocks.create).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("rejects mismatched declared totals before uploading", async () => {
    const coordinator = await restored();
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]")])).rejects.toThrow(/does not match/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("does not acquire a competing tab's transfer", async () => {
    const coordinator = await restored();
    vi.mocked(navigator.locks.request).mockImplementation(async (_name, _options, callback: any) => callback(null));
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/another tab/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("reconciles and retries one transient failed batch without creating a job", async () => {
    const coordinator = await restored();
    vi.useFakeTimers();
    apiMocks.upload.mockRejectedValueOnce({ code: "ECONNABORTED" });
    const result = coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")]);
    // Hashing uses native crypto; yield to its worker before advancing timers.
    await vi.waitFor(() => expect(apiMocks.upload).toHaveBeenCalledTimes(1));
    await vi.advanceTimersByTimeAsync(1100);
    await result;
    expect(apiMocks.upload).toHaveBeenCalledTimes(2);
    expect(apiMocks.create).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
    vi.useRealTimers();
  });
  it("does not retry an authorization refusal", async () => {
    const coordinator = await restored();
    apiMocks.upload.mockRejectedValue({ response: { status: 403 } });
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toBeDefined();
    expect(apiMocks.upload).toHaveBeenCalledTimes(1);
    expect(apiMocks.commit).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("stops after a bounded number of transient retries and retains the job", async () => {
    const coordinator = await restored();
    vi.useFakeTimers();
    apiMocks.upload.mockRejectedValue({ code: "ECONNABORTED" });
    const result = coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")]);
    const rejected = expect(result).rejects.toBeDefined();
    await vi.waitFor(() => expect(apiMocks.upload).toHaveBeenCalledTimes(1));
    await vi.advanceTimersByTimeAsync(3500);
    await rejected;
    expect(apiMocks.upload).toHaveBeenCalledTimes(3);
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
    vi.useRealTimers();
  });
  it("blocks unbounded browser hash allocation before any write", async () => {
    const coordinator = await restored();
    apiMocks.manifest.mockResolvedValue({ ...job(), files: [{ path: "export/conversations.json", size: 129 * 1024 * 1024, sha256: "a".repeat(64) }] });
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/safe verification limit/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("reads back a lost commit response without submitting a second commit", async () => {
    const coordinator = await restored();
    apiMocks.commit.mockRejectedValue({ code: "ECONNABORTED" });
    apiMocks.fetch.mockResolvedValueOnce(job()).mockResolvedValueOnce(job("queued"));
    await coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")]);
    expect(apiMocks.commit).toHaveBeenCalledTimes(1);
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("accepted");
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("aborts the active request on reset and ignores a late response", async () => {
    const coordinator = await restored();
    let finish: (value: unknown) => void = () => {};
    apiMocks.upload.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    const result = coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")]);
    const rejected = expect(result).rejects.toThrow(/stopped/);
    await waitFor(() => expect(apiMocks.upload).toHaveBeenCalledTimes(1));
    const signal = apiMocks.upload.mock.calls[0][2] as AbortSignal;
    coordinator.clearAccountImportCoordinatorResult();
    expect(signal.aborted).toBe(true);
    finish(job());
    await rejected;
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("idle");
    expect(apiMocks.commit).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("surfaces unsupported transfer coordination without dispatch", async () => {
    const coordinator = await restored();
    Object.defineProperty(navigator, "locks", { configurable: true, value: undefined });
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/Web Locks/);
    expect(coordinator.getAccountImportCoordinatorSnapshot().error).toMatch(/Web Locks/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });

});
