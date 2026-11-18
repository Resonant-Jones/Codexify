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
});
