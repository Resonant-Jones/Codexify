import { waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  preflight: vi.fn(),
  create: vi.fn(),
  upload: vi.fn(),
  commit: vi.fn(),
  fetch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  preflightBackendAvailability: apiMocks.preflight,
  createOpenAIAccountImport: apiMocks.create,
  uploadOpenAIAccountImportBatch: apiMocks.upload,
  commitOpenAIAccountImport: apiMocks.commit,
  fetchOpenAIAccountImport: apiMocks.fetch,
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

  it("keeps account scope through create, transfer, commit, and polling", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
      { file: new File(["png"], "image.png"), relativePath: "export/media/image.png" },
    ];

    await coordinator.startOpenAIAccountImport(files, "account-a");

    expect(apiMocks.create).toHaveBeenCalledWith(
      {
        total_file_count: 2,
        total_byte_count: 5,
        source_system: "openai",
      },
      "account-a"
    );
    expect(apiMocks.upload).toHaveBeenCalledWith(
      "job-restore",
      files,
      "account-a"
    );
    expect(apiMocks.commit).toHaveBeenCalledWith("job-restore", "account-a");
    expect(coordinator.getAccountImportCoordinatorSnapshot().phase).toBe(
      "accepted"
    );
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("explicitly serializes source_system=anthropic when requested", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
    ];

    await coordinator.startOpenAIAccountImport(files, "account-anthropic", "anthropic");

    expect(apiMocks.create).toHaveBeenCalledWith(
      {
        total_file_count: 1,
        total_byte_count: 2,
        source_system: "anthropic",
      },
      "account-anthropic"
    );
    expect(apiMocks.upload).toHaveBeenCalledWith(
      "job-restore",
      files,
      "account-anthropic"
    );
    expect(apiMocks.commit).toHaveBeenCalledWith("job-restore", "account-anthropic");
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

    await coordinator.startOpenAIAccountImport(files, "account-a", "openai");

    await expect(
      coordinator.startOpenAIAccountImport(files, "account-a", "anthropic")
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
    expect(apiMocks.fetch).toHaveBeenCalledWith(
      "legacy-source",
      undefined
    );
    coordinator.resetAccountImportCoordinatorForTests();
  });

  it("does not assign canonical conversation origin_system on the Web", async () => {
    const coordinator = await import(
      "@/features/imports/accountImportCoordinator"
    );
    const files = [
      { file: new File(["[]"], "conversations.json"), relativePath: "export/conversations.json" },
    ];
    await coordinator.startOpenAIAccountImport(files, "account-a", "anthropic");
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
    expect(apiMocks.fetch).toHaveBeenCalledWith("job-restore", undefined);
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
    expect(apiMocks.fetch).toHaveBeenCalledWith("stale-404-job", undefined);

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
