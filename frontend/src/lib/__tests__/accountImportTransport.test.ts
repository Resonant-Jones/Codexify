import { afterEach, describe, expect, it, vi } from "vitest";
import api, { uploadOpenAIAccountImportBatch, commitOpenAIAccountImport, fetchOpenAIAccountImportManifest, accountImportUploadTimeoutMs, ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS, ACCOUNT_IMPORT_MAX_UPLOAD_TIMEOUT_MS } from "@/lib/api";

afterEach(() => vi.restoreAllMocks());
describe("bounded account import transport", () => {
  it("sets a finite upload timeout and forwards caller cancellation", async () => {
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: { status: "receiving" } });
    const controller = new AbortController();
    await uploadOpenAIAccountImportBatch("job", [{file: new File(["a"], "a"), relativePath: "export/a"}], controller.signal);
    expect(post).toHaveBeenCalledWith("/api/imports/openai-account/job/files", expect.any(FormData), expect.objectContaining({ timeout: ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS, signal: controller.signal }));
    expect(ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS).toBeGreaterThan(0);
    expect(ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS).toBeLessThanOrEqual(120_000);
  });
  it("bounds commit without adding a client account identity", async () => {
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: {} });
    await commitOpenAIAccountImport("job");
    expect(post).toHaveBeenCalledWith("/api/imports/openai-account/job/commit", undefined, expect.objectContaining({ timeout: ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS }));
  });
  it("budgets larger batches for slow uplinks without allowing an unlimited deadline", async () => {
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: { status: "receiving" } });
    const batchFile = new File(["data"], "big.bin");
    Object.defineProperty(batchFile, "size", { value: 32 * 1024 * 1024 });
    const expected = accountImportUploadTimeoutMs(batchFile.size);
    await uploadOpenAIAccountImportBatch("job", [{ file: batchFile, relativePath: "big.bin" }]);
    expect(expected).toBeGreaterThan(ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS);
    expect(expected).toBeLessThanOrEqual(ACCOUNT_IMPORT_MAX_UPLOAD_TIMEOUT_MS);
    expect(accountImportUploadTimeoutMs(4 * 1024 * 1024 * 1024)).toBe(ACCOUNT_IMPORT_MAX_UPLOAD_TIMEOUT_MS);
    expect(post).toHaveBeenCalledWith("/api/imports/openai-account/job/files", expect.any(FormData), expect.objectContaining({ timeout: expected }));
  });
  it("reads the owner-authorized manifest through normal authenticated transport", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue({ data: { files: [] } });
    expect(await fetchOpenAIAccountImportManifest("job")).toEqual({files: []});
    expect(get).toHaveBeenCalledWith("/api/imports/openai-account/job/manifest", expect.objectContaining({ timeout: ACCOUNT_IMPORT_REQUEST_TIMEOUT_MS }));
  });
  it("assembles bounded owner manifest pages and refuses inconsistent metadata", async () => {
    const first = { job_id: "job", status: "receiving", source_system: "openai",
      total_file_count: 3, total_byte_count: 3,
      files: [{ path: "a", size: 1, sha256: "a".repeat(64) }], next_cursor: 1 };
    const next = { ...first, files: [{ path: "b", size: 1, sha256: "b".repeat(64) }], next_cursor: undefined };
    const get = vi.spyOn(api, "get").mockResolvedValueOnce({ data: first }).mockResolvedValueOnce({ data: next });
    const result = await fetchOpenAIAccountImportManifest("job");
    expect(result.files.map(entry => entry.path)).toEqual(["a", "b"]);
    expect(get).toHaveBeenNthCalledWith(2, "/api/imports/openai-account/job/manifest?cursor=1", expect.any(Object));
    get.mockReset().mockResolvedValueOnce({ data: first })
      .mockResolvedValueOnce({ data: { ...next, job_id: "other" } });
    await expect(fetchOpenAIAccountImportManifest("job")).rejects.toThrow(/pages changed/);
  });
  it("accepts a receiving manifest above the default 20,000-file limit when declared by the server", async () => {
    const total = 20_001;
    const get = vi.spyOn(api, "get").mockImplementation(async (url: string) => {
      const cursor = Number(url.match(/cursor=(\d+)/)?.[1] ?? 0);
      const count = Math.min(512, total - cursor);
      return { data: {
        job_id: "large-job", source_system: "openai", status: "receiving",
        total_file_count: total, total_byte_count: 0,
        files: Array.from({ length: count }, (_, i) => ({
          path: `export/${cursor + i}.txt`, size: 0, sha256: "a".repeat(64),
        })),
        ...(cursor + count < total ? { next_cursor: cursor + count } : {}),
      } };
    });
    const manifest = await fetchOpenAIAccountImportManifest("large-job");
    expect(manifest.files).toHaveLength(total);
    expect(get).toHaveBeenCalledTimes(Math.ceil(total / 512));
  });
});
