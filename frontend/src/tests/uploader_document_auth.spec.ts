import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useUploader } from "../hooks/useUploader";

class MockFileReader {
  result: string | ArrayBuffer | null = null;

  onload:
    | ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown)
    | null = null;

  onerror:
    | ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown)
    | null = null;

  readAsDataURL(_file: Blob) {
    this.result = "data:text/plain;base64,ZmFrZQ==";
    this.onload?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
  }

  readAsText(_file: Blob) {
    this.result = "mock text";
    this.onload?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
  }
}

function installFetchMock() {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL): Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }> => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/media/upload/document") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: "doc-1",
            src_url: "/media/documents/doc-1.txt",
            filename: "doc-1.txt",
          }),
        };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({}),
      };
    }
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function uploadDocument() {
  const onImages = vi.fn();
  const onDocuments = vi.fn();

  const { result } = renderHook(() =>
    useUploader({
      onImages,
      onDocuments,
      projectId: 7,
      threadId: 11,
    })
  );

  const file = new File(["hello"], "notes.txt", { type: "text/plain" });
  await act(async () => {
    await result.current.handleFiles([file]);
  });

  expect(onDocuments).toHaveBeenCalledTimes(1);
}

describe("useUploader auth headers", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("adds X-API-Key on document upload in non-proxy mode", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "false");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "non-proxy-key");

    const fetchMock = installFetchMock();
    await uploadDocument();

    const mediaCall = fetchMock.mock.calls.find(
      ([url]) => url === "/api/media/upload/document"
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("non-proxy-key");
  });

  it("does not add X-API-Key on document upload in proxy mode", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "true");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "proxy-key");

    const fetchMock = installFetchMock();
    await uploadDocument();

    const mediaCall = fetchMock.mock.calls.find(
      ([url]) => url === "/api/media/upload/document"
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-API-Key"]).toBeUndefined();
  });
});
