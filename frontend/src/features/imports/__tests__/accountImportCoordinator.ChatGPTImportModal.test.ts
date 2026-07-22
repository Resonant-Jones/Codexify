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

describe("account import coordinator continuity", () => {
  beforeEach(() => {
    vi.resetModules();
    window.localStorage.clear();
    apiMocks.preflight.mockReset().mockResolvedValue({ ok: true });
    apiMocks.create.mockReset().mockResolvedValue(job());
    apiMocks.upload.mockReset().mockResolvedValue({
      ...job(),
      uploaded_file_count: 2,
      uploaded_byte_count: 5,
    });
    apiMocks.commit.mockReset().mockResolvedValue(job("queued"));
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
      { total_file_count: 2, total_byte_count: 5 },
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
});
