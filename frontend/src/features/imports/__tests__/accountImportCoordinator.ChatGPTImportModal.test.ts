import { waitFor } from "@testing-library/react";
import { createHash } from "node:crypto";
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
      /no original complete-export fingerprint/
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
  const contentHash = (value: string) => createHash("sha256").update(value).digest("hex");
  const selectionHash = (entries: Array<[string, number, string]>, sourceSystem = "openai") => {
    const aggregate = createHash("sha256").update(`cfy-account-import-selection:v1\n${sourceSystem}\n`);
    for (const entry of [...entries].sort((a, b) => a[0].localeCompare(b[0]))) {
      aggregate.update(JSON.stringify(entry) + "\n");
    }
    return aggregate.digest("hex");
  };
  const defaultFingerprint = () => selectionHash([
    ["export/conversations.json", 2, contentHash("[]")],
    ["export/image.png", 3, contentHash("png")],
  ]);
  const file = (name: string, content: string) => {
    const value = new File([content], name);
    Object.defineProperty(value, "arrayBuffer", { value: async () => new TextEncoder().encode(content).buffer });
    return { file: value, relativePath: `export/${name}` };
  };
  async function restored(selectionFingerprint = defaultFingerprint()) {
    const { webcrypto } = await import("node:crypto");
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
    window.localStorage.setItem("cfy.accountImport:v1", JSON.stringify({ v: 1, jobId: "job-restore", status: "receiving", sourceSystem: "openai", selectionFingerprint }));
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
  it("rejects a same-size replacement of an unstaged file before sending any bytes", async () => {
    const coordinator = await restored();
    await expect(coordinator.startOpenAIAccountImport([
      file("conversations.json", "[]"), file("image.png", "bad"),
    ])).rejects.toThrow(/content or file paths differ/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("rejects a renamed unstaged file with the same byte count", async () => {
    const coordinator = await restored();
    await expect(coordinator.startOpenAIAccountImport([
      file("conversations.json", "[]"), file("other.png", "png"),
    ])).rejects.toThrow(/content or file paths differ/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("preserves only a SHA-256 selection fingerprint before initial upload", async () => {
    const coordinator = await import("@/features/imports/accountImportCoordinator");
    apiMocks.upload.mockRejectedValue({ response: { status: 403 } });
    await expect(coordinator.startOpenAIAccountImport([
      file("conversations.json", "[]"), file("image.png", "png"),
    ])).rejects.toBeDefined();
    const state = JSON.parse(window.localStorage.getItem("cfy.accountImport:v1") || "{}");
    expect(state.selectionFingerprint).toBe(defaultFingerprint());
    expect(state.jobId).toBe("job-restore");
    expect(JSON.stringify(state)).not.toContain("conversations.json");
    expect(JSON.stringify(state)).not.toContain("image.png");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("does not silently resume a legacy receiving job without an original fingerprint", async () => {
    const coordinator = await restored(null as unknown as string);
    await expect(coordinator.startOpenAIAccountImport([
      file("conversations.json", "[]"), file("image.png", "png"),
    ])).rejects.toThrow(/lacks complete-export verification/);
    expect(apiMocks.create).not.toHaveBeenCalled();
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    expect(JSON.parse(window.localStorage.getItem("cfy.accountImport:v1") || "{}").jobId).toBe("job-restore");
    expect(coordinator.getAccountImportCoordinatorSnapshot().error).not.toMatch(/discard|start again/);
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("clears the receiving browser job if its owner-scoped server lookup returns 404", async () => {
    const coordinator = await restored();
    apiMocks.fetch.mockRejectedValueOnce({ response: { status: 404 } });
    await expect(coordinator.startOpenAIAccountImport([
      file("conversations.json", "[]"), file("image.png", "png"),
    ])).rejects.toBeDefined();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job).toBeNull();
    expect(coordinator.getAccountImportCoordinatorSnapshot().error).toMatch(/stale browser reference was cleared/);
    expect(window.localStorage.getItem("cfy.accountImport:v1")).toBeNull();
    const retained = JSON.parse(window.localStorage.getItem("cfy.accountImport:unavailable:v1") || "[]");
    expect(JSON.parse(retained[0])).toMatchObject({ jobId: "job-restore", selectionFingerprint: defaultFingerprint() });
    expect(apiMocks.create).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("retains an unavailable checkpoint on manifest 404 without creating another job", async () => {
    const coordinator = await restored();
    apiMocks.manifest.mockRejectedValueOnce({ response: { status: 404 } });
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toBeDefined();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job).toBeNull();
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.create).not.toHaveBeenCalled();
    const retained = JSON.parse(window.localStorage.getItem("cfy.accountImport:unavailable:v1") || "[]");
    expect(JSON.parse(retained[0]).jobId).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("does not look up or resume a checkpoint belonging to a different server", async () => {
    window.localStorage.setItem("cfy.accountImport:v1", JSON.stringify({ v: 1, jobId: "job-restore", status: "receiving", sourceSystem: "openai", selectionFingerprint: defaultFingerprint(), server: "https://original.example/api" }));
    const coordinator = await import("@/features/imports/accountImportCoordinator");
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed");
    expect(apiMocks.fetch).not.toHaveBeenCalled();
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/different server/);
    expect(apiMocks.create).not.toHaveBeenCalled();
    expect(JSON.parse(window.localStorage.getItem("cfy.accountImport:v1") || "{}").server).toBe("https://original.example/api");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("retains the active receiving pointer if archival storage is unavailable", async () => {
    const coordinator = await restored();
    const set = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("storage unavailable"); });
    apiMocks.fetch.mockRejectedValueOnce({ response: { status: 404 } });
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toBeDefined();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    expect(JSON.parse(window.localStorage.getItem("cfy.accountImport:v1") || "{}").jobId).toBe("job-restore");
    expect(apiMocks.create).not.toHaveBeenCalled();
    set.mockRestore();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("keeps an idle receiving status event in resumable failed state", async () => {
    const coordinator = await restored();
    window.dispatchEvent(new CustomEvent("cfy:account-import:status", { detail: { job_id: "job-restore" } }));
    await waitFor(() => expect(apiMocks.fetch).toHaveBeenCalledTimes(2));
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed");
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("shows aggregate progress and times out an unreadable selected file without uploading", async () => {
    const coordinator = await restored();
    const stuck = file("conversations.json", "[]");
    let finishRead!: (value: ArrayBuffer) => void;
    const selected = { ...stuck, file: { size: 2, arrayBuffer: () => new Promise<ArrayBuffer>(resolve => { finishRead = resolve; }) } as File };
    vi.useFakeTimers();
    const result = coordinator.startOpenAIAccountImport([selected, file("image.png", "png")]);
    const rejected = expect(result).rejects.toThrow(/timed out while reading/);
    await vi.waitFor(() => expect(coordinator.getAccountImportCoordinatorSnapshot().verification?.stage).toBe("reading"));
    expect(coordinator.getAccountImportCoordinatorSnapshot().verification).toMatchObject({ completed: 0, total: 2, bytes: 0, totalBytes: 5 });
    await vi.advanceTimersByTimeAsync(coordinator.ACCOUNT_IMPORT_VERIFY_STEP_TIMEOUT_MS);
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed");
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/already active/);
    finishRead(new TextEncoder().encode("[]").buffer);
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
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed");
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/already active/);
    finish(new ArrayBuffer(32));
    await rejected;
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe("failed");
    coordinator.resetAccountImportCoordinatorForTests();
    vi.useRealTimers();
  });
  it("stops a pending local read on reset without waiting for its deadline", async () => {
    const coordinator = await restored();
    let finishRead!: (value: ArrayBuffer) => void;
    const selected = { relativePath: "export/conversations.json", file: { size: 2, arrayBuffer: () => new Promise<ArrayBuffer>(resolve => { finishRead = resolve; }) } as File };
    const result = coordinator.startOpenAIAccountImport([selected, file("image.png", "png")]);
    const rejected = expect(result).rejects.toThrow(/stopped/);
    await waitFor(() => expect(coordinator.getAccountImportCoordinatorSnapshot().verification?.stage).toBe("reading"));
    coordinator.clearAccountImportCoordinatorResult();
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/already active/);
    finishRead(new TextEncoder().encode("[]").buffer);
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
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "{}"), file("image.png", "png")])).rejects.toThrow(/differ|conflict/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    expect(apiMocks.create).not.toHaveBeenCalled();
    expect(coordinator.getAccountImportCoordinatorSnapshot().job?.job_id).toBe("job-restore");
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("rejects mismatched declared totals before uploading", async () => {
    const coordinator = await restored();
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]")])).rejects.toThrow(/does not match|differ/);
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
  it("rejects a staged entry whose declared size conflicts with the selected file", async () => {
    const coordinator = await restored();
    apiMocks.manifest.mockResolvedValue({ ...job(), files: [{ path: "export/conversations.json", size: 129 * 1024 * 1024, sha256: "a".repeat(64) }] });
    await expect(coordinator.startOpenAIAccountImport([file("conversations.json", "[]"), file("image.png", "png")])).rejects.toThrow(/conflicts with staged files/);
    expect(apiMocks.upload).not.toHaveBeenCalled();
    expect(apiMocks.commit).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("rejects large files without bounded-slice support before creating a job", async () => {
    const coordinator = await import("@/features/imports/accountImportCoordinator");
    const oversized = { relativePath: "export/big.bin", file: { size: 129 * 1024 * 1024 } as File };
    await expect(coordinator.startOpenAIAccountImport([oversized])).rejects.toThrow(/bounded file slices/);
    expect(apiMocks.preflight).not.toHaveBeenCalled();
    expect(apiMocks.create).not.toHaveBeenCalled();
    expect(apiMocks.upload).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("refuses files beyond the backend limit even when bounded slices are available", async () => {
    const coordinator = await import("@/features/imports/accountImportCoordinator");
    const oversized = { relativePath: "export/too-large.bin", file: { size: 2 * 1024 * 1024 * 1024 + 1, slice: vi.fn() } as unknown as File };
    await expect(coordinator.startOpenAIAccountImport([oversized])).rejects.toThrow(/2 GiB/);
    expect(apiMocks.create).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("resumes a staged 129 MiB file with incremental hashing and 8 MiB reads", async () => {
    const { createHash } = await import("node:crypto");
    const chunk = new Uint8Array(1024 * 1024).fill(97);
    const largeSize = 129 * chunk.length;
    const expectedHash = createHash("sha256");
    for (let i = 0; i < 129; i += 1) expectedHash.update(chunk);
    const stagedHash = expectedHash.digest("hex");
    const largeFingerprint = selectionHash([
      ["export/large.bin", largeSize, stagedHash],
      ["export/image.png", 3, contentHash("png")],
    ]);
    const coordinator = await restored(largeFingerprint);
    let readCalls = 0;
    const large = {
      relativePath: "export/large.bin",
      file: {
        size: largeSize,
        slice: (start: number, end: number) => {
          readCalls += 1;
          if (end - start > 8 * 1024 * 1024) throw new Error("oversized slice");
          return { arrayBuffer: async () => new Uint8Array(end - start).fill(97).buffer };
        },
      } as unknown as File,
    };
    apiMocks.fetch.mockResolvedValue({ ...job(), total_byte_count: largeSize + 3 });
    apiMocks.manifest.mockResolvedValue({
      ...job(), total_byte_count: largeSize + 3,
      files: [{ path: large.relativePath, size: largeSize, sha256: stagedHash }],
    });
    const missing = file("image.png", "png");
    await coordinator.startOpenAIAccountImport([large, missing]);
    expect(readCalls).toBe(34);
    expect(apiMocks.upload).toHaveBeenCalledWith("job-restore", [missing], expect.any(AbortSignal));
    expect(apiMocks.create).not.toHaveBeenCalled();
    coordinator.resetAccountImportCoordinatorForTests();
  });
  it("refuses truncated large-file slices without uploading or committing", async () => {
    const largeSize = 129 * 1024 * 1024;
    const coordinator = await restored(selectionHash([
      ["export/large.bin", largeSize, "a".repeat(64)],
      ["export/image.png", 3, contentHash("png")],
    ]));
    const selected = {
      relativePath: "export/large.bin",
      file: {
        size: largeSize,
        slice: () => ({ arrayBuffer: async () => new Uint8Array([97]).buffer }),
      } as unknown as File,
    };
    apiMocks.fetch.mockResolvedValue({ ...job(), total_byte_count: largeSize + 3 });
    apiMocks.manifest.mockResolvedValue({
      ...job(), total_byte_count: largeSize + 3,
      files: [{ path: selected.relativePath, size: largeSize, sha256: "a".repeat(64) }],
    });
    await expect(coordinator.startOpenAIAccountImport([selected, file("image.png", "png")])).rejects.toThrow(/conflicts with staged files/);
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
