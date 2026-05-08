import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useUploader } from "../hooks/useUploader";
import { resolveBackendUrl } from "../lib/runtimeConfig";

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
      if (url === resolveBackendUrl("/api/media/upload/document")) {
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

async function uploadDocument(
  opts: { projectId?: number; threadId?: number } = {}
) {
  const onImages = vi.fn();
  const onDocuments = vi.fn();

  const hasProjectId = Object.prototype.hasOwnProperty.call(opts, "projectId");
  const hasThreadId = Object.prototype.hasOwnProperty.call(opts, "threadId");

  const { result } = renderHook(() =>
    useUploader({
      onImages,
      onDocuments,
      projectId: hasProjectId ? opts.projectId : 7,
      threadId: hasThreadId ? opts.threadId : 11,
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
    localStorage.clear();
  });

  it("adds X-API-Key on document upload in non-proxy mode", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "false");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "non-proxy-key");

    const fetchMock = installFetchMock();
    await uploadDocument();

    const mediaCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/media/upload/document")
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("non-proxy-key");
  });

  it("adds X-API-Key on document upload in proxy mode when a local key is configured", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "true");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "proxy-key");

    const fetchMock = installFetchMock();
    await uploadDocument();

    const mediaCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/media/upload/document")
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("proxy-key");
  });

  it("uploads documents without thread context when project_id is present", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "false");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "non-proxy-key");

    const fetchMock = installFetchMock();
    await uploadDocument({ projectId: 7, threadId: undefined });

    const mediaCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/media/upload/document")
    );
    expect(mediaCall).toBeDefined();
  });

  it("mounts a file input in the DOM before opening the picker", () => {
    const appendSpy = vi.spyOn(document.body, "appendChild");
    const clickSpy = vi
      .spyOn(HTMLInputElement.prototype, "click")
      .mockImplementation(() => {});

    const { result } = renderHook(() =>
      useUploader({
        onImages: vi.fn(),
        onDocuments: vi.fn(),
        projectId: 7,
        threadId: 11,
      })
    );

    act(() => {
      result.current.pick();
    });

    expect(
      appendSpy.mock.calls.some(([node]) => node instanceof HTMLInputElement)
    ).toBe(true);
    const appended = appendSpy.mock.calls.find(
      ([node]) => node instanceof HTMLInputElement
    )?.[0] as HTMLInputElement | undefined;
    expect(appended).toBeInstanceOf(HTMLInputElement);
    expect(appended?.type).toBe("file");
    expect(appended?.multiple).toBe(true);
    expect(appended?.accept).toContain(".png");
    expect(appended?.accept).toContain(".pdf");
    expect(clickSpy).toHaveBeenCalledTimes(1);

    appended?.remove();
    appendSpy.mockRestore();
    clickSpy.mockRestore();
  });
});

describe("useUploader trusted general project storage", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("ignores stale stored general project ids until trust is established", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "false");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "non-proxy-key");

    localStorage.setItem("cfy.generalProjectId", "1");
    localStorage.setItem("cfy.defaultProjectId", "1");
    localStorage.removeItem("cfy.generalProjectIdTrusted");

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL): Promise<{
        ok: boolean;
        status: number;
        json: () => Promise<unknown>;
      }> => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === resolveBackendUrl("/api/projects")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              projects: [
                {
                  id: 7,
                  name: "General",
                },
              ],
            }),
          };
        }
        if (url === resolveBackendUrl("/api/media/upload/document")) {
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

    await uploadDocument({ projectId: undefined, threadId: undefined });

    expect(
      fetchMock.mock.calls.some(
        ([url]) => String(url) === resolveBackendUrl("/api/projects")
      )
    ).toBe(true);

    const uploadCall = fetchMock.mock.calls.find(
      ([url]) => String(url) === resolveBackendUrl("/api/media/upload/document")
    );
    const form = uploadCall?.[1]?.body as FormData | undefined;
    expect(form?.get("project_id")).toBe("7");
    expect(form?.get("projectId")).toBe("7");
    expect(localStorage.getItem("cfy.generalProjectIdTrusted")).toBeNull();
  });

  it("uses trusted stored general project ids when the trust marker is present", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "false");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "proxy-key");

    localStorage.setItem("cfy.generalProjectId", "1");
    localStorage.setItem("cfy.defaultProjectId", "1");
    localStorage.setItem("cfy.generalProjectIdTrusted", "1");

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL): Promise<{
        ok: boolean;
        status: number;
        json: () => Promise<unknown>;
      }> => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === resolveBackendUrl("/api/projects")) {
          return {
            ok: false,
            status: 500,
            json: async () => ({}),
          };
        }
        if (url === resolveBackendUrl("/api/media/upload/document")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              id: "doc-2",
              src_url: "/media/documents/doc-2.txt",
              filename: "doc-2.txt",
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

    await uploadDocument({ projectId: undefined, threadId: undefined });

    expect(
      fetchMock.mock.calls.some(
        ([url]) => String(url) === resolveBackendUrl("/api/projects")
      )
    ).toBe(false);

    const uploadCall = fetchMock.mock.calls.find(
      ([url]) => String(url) === resolveBackendUrl("/api/media/upload/document")
    );
    const form = uploadCall?.[1]?.body as FormData | undefined;
    expect(form?.get("project_id")).toBe("1");
    expect(form?.get("projectId")).toBe("1");
  });
});
