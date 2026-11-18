import { webcrypto, createHash } from "node:crypto";
import { Buffer } from "node:buffer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import api, { normalizeImportRuntimeError, uploadOpenAIAccountImportBatch, waitForAccountImportVerification, ACCOUNT_IMPORT_CHUNK_BYTES, ACCOUNT_IMPORT_HASH_STEP_TIMEOUT_MS, ACCOUNT_IMPORT_BROWSER_HASH_BYTES } from "@/lib/api";

const size = 33 * 1024 * 1024;
function selected(total = size) {
  const read = vi.fn(async () => Buffer.alloc(total, 7).buffer as ArrayBuffer);
  const file = { name: "movie.dat", type: "video/mp4", size: total, arrayBuffer: read,
    slice(start: number, end: number) {
      const value = Buffer.alloc(end-start, 7);
      const blob = new Blob([value], { type: "video/mp4" });
      Object.defineProperty(blob, "arrayBuffer", { value: async () => value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength) as ArrayBuffer });
      return blob;
    },
  } as unknown as File;
  return { item: { file, relativePath: "original/movie.dat" }, read };
}
function receipt(received: number, jobId = "job") {
  return { data: { job: { job_id: jobId, source_system: "openai", status: "receiving", uploaded_file_count: received === size ? 1 : 0 },
    received_bytes: received, complete: received === size } };
}

beforeEach(() => { vi.stubGlobal("crypto", webcrypto); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("bounded same-job file parts", () => {
  it("pins whole identity and preserves original path while sending only bounded parts", async () => {
    const { item } = selected();
    const post = vi.spyOn(api, "post").mockImplementation(async (_url, form: any) => {
      const offset = Number(form.get("offset"));
      expect(form.get("chunk").size).toBeLessThanOrEqual(ACCOUNT_IMPORT_CHUNK_BYTES);
      expect(form.get("relative_path")).toBe("original/movie.dat");
      expect(form.get("file_size")).toBe(String(size));
      expect(form.has("user_id")).toBe(false);
      return receipt(Math.min(offset + ACCOUNT_IMPORT_CHUNK_BYTES, size));
    });
    const job = await uploadOpenAIAccountImportBatch("job", [item]);
    expect(post).toHaveBeenCalledTimes(5);
    expect(job.uploaded_file_count).toBe(1);
    const hashes = post.mock.calls.map(call => (call[1] as FormData).get("file_sha256"));
    expect(new Set(hashes).size).toBe(1);
    expect(hashes[0]).toBe(createHash("sha256").update(new Uint8Array(size).fill(7)).digest("hex"));
    for (const [url, form, config] of post.mock.calls) {
      expect(url).toBe("/api/imports/openai-account/job/file-chunks");
      expect(config).toEqual(expect.objectContaining({ timeout: expect.any(Number) }));
      expect((form as FormData).get("chunk_sha256")).toMatch(/^[a-f0-9]{64}$/);
    }
  });

  it("reconciles an already stored prefix on replay without generating another logical identity", async () => {
    const { item } = selected();
    const post = vi.spyOn(api, "post").mockImplementation(async (_url, form: any) => {
      const offset = Number(form.get("offset"));
      return receipt(offset === 0 ? 2 * ACCOUNT_IMPORT_CHUNK_BYTES : Math.min(offset + ACCOUNT_IMPORT_CHUNK_BYTES, size));
    });
    await uploadOpenAIAccountImportBatch("job", [item]);
    expect(post.mock.calls.map(call => Number((call[1] as FormData).get("offset")))).toEqual([0, 16777216, 25165824, 33554432]);
  });

  it("hashes 129 MiB through bounded parts without allocating the entire file", async () => {
    const large = ACCOUNT_IMPORT_BROWSER_HASH_BYTES + 1024 * 1024;
    const { item, read } = selected(large);
    const post = vi.spyOn(api, "post").mockImplementation(async (_url, form: any, config: any) => {
      const offset = Number(form.get("offset"));
      const next = Math.min(offset + ACCOUNT_IMPORT_CHUNK_BYTES, large);
      expect(config.timeout).toBeGreaterThanOrEqual(120_000);
      if (next - offset === ACCOUNT_IMPORT_CHUNK_BYTES) expect(config.timeout).toBeGreaterThan(120_000);
      return { data: { job: { job_id: "job", status: "receiving", uploaded_file_count: next === large ? 1 : 0 }, received_bytes: next, complete: next === large } };
    });
    const complete = await uploadOpenAIAccountImportBatch("job", [item]);
    expect(complete.uploaded_file_count).toBe(1);
    expect(post).toHaveBeenCalledTimes(17);
    expect(read).not.toHaveBeenCalled();
  });

  it("times out a native read once and prevents a late completion from POSTing", async () => {
    vi.useFakeTimers();
    const { item, read } = selected();
    let finish!: (value: ArrayBuffer) => void;
    read.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const post = vi.spyOn(api, "post");
    const attempt = uploadOpenAIAccountImportBatch("job", [item]);
    const rejected = expect(attempt).rejects.toThrow(/Local export verification/);
    await vi.advanceTimersByTimeAsync(ACCOUNT_IMPORT_HASH_STEP_TIMEOUT_MS + 1);
    expect(post).not.toHaveBeenCalled();
    await rejected; // The API rejects at the deadline, before native settlement.
    let drained = false;
    const cleanup = waitForAccountImportVerification().then(() => { drained = true; });
    await Promise.resolve();
    expect(drained).toBe(false);
    await expect(uploadOpenAIAccountImportBatch("job", [item])).rejects.toThrow(/still finishing/);
    expect(read).toHaveBeenCalledTimes(1);
    finish(new ArrayBuffer(0));
    await cleanup;
    const localError = await attempt.catch(error => error);
    expect(normalizeImportRuntimeError(localError).isRuntimeUnavailable).toBe(false);
    expect(read).toHaveBeenCalledTimes(1); expect(post).not.toHaveBeenCalled();
  });

  it("stops after abort without a late native hash triggering a request", async () => {
    const { item, read } = selected();
    let finish!: (value: ArrayBuffer) => void;
    read.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const post = vi.spyOn(api, "post"); const controller = new AbortController();
    const attempt = uploadOpenAIAccountImportBatch("job", [item], controller.signal);
    const rejected = expect(attempt).rejects.toThrow(/Local export verification/);
    await vi.waitFor(() => expect(read).toHaveBeenCalledTimes(1));
    controller.abort();
    await rejected;
    await expect(uploadOpenAIAccountImportBatch("job", [item])).rejects.toThrow(/still finishing/);
    expect(read).toHaveBeenCalledTimes(1);
    finish(new ArrayBuffer(0));
    await waitForAccountImportVerification();
    await Promise.resolve(); expect(post).not.toHaveBeenCalled();
  });

  it("keeps server conflict and authentication responses intact without automatic replay", async () => {
    const { item } = selected(); const error = { response: { status: 409 } };
    const post = vi.spyOn(api, "post").mockRejectedValue(error);
    await expect(uploadOpenAIAccountImportBatch("job", [item])).rejects.toBe(error);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("refuses wrong-job or impossible-progress receipts", async () => {
    const { item } = selected();
    const post = vi.spyOn(api, "post").mockResolvedValue(receipt(ACCOUNT_IMPORT_CHUNK_BYTES, "other-job"));
    await expect(uploadOpenAIAccountImportBatch("job", [item])).rejects.toThrow(/Invalid bounded upload receipt/);
    expect(post).toHaveBeenCalledTimes(1);
  });
});
