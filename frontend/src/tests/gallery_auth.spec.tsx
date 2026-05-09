import { act, render, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import GalleryView from "../components/gallery/GalleryView";
import { ProjectContext } from "../components/layout/ProjectContext";
import { useUploader } from "../hooks/useUploader";
import { setAuthToken } from "../lib/api";
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
    this.result = "data:image/png;base64,ZmFrZQ==";
    this.onload?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
  }

  readAsText(_file: Blob) {
    this.result = "mock text";
    this.onload?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
  }
}

function normalizeHeaders(
  headers: RequestInit["headers"]
): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) {
    const out: Record<string, string> = {};
    headers.forEach((value, key) => {
      out[key] = value;
    });
    return out;
  }
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }
  return { ...(headers as Record<string, string>) };
}

describe("gallery auth", () => {
  afterEach(() => {
    setAuthToken(null);
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("prefers bearer token for gallery list reads", async () => {
    setAuthToken("gallery-token");

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ images: [], count: 0 }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ProjectContext.Provider
        value={{ projectId: "7", setProjectId: vi.fn() }}
      >
        <GalleryView onSelect={vi.fn()} />
      </ProjectContext.Provider>
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const mediaCall = fetchMock.mock.calls.find(([url]) =>
      String(url).startsWith("/api/media/images")
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = normalizeHeaders(init?.headers);
    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer gallery-token"
    );
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
    expect(init?.credentials).toBe("include");
  });

  it("uses dev api key override for gallery uploads when token is absent", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    setAuthToken(null);
    vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", "gallery-dev-key");

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL): Promise<{
        ok: boolean;
        status: number;
        json: () => Promise<unknown>;
      }> => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === resolveBackendUrl("/api/media/upload/image")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              id: "img-1",
              src_url: "/media/images/img-1.png",
              filename: "img-1.png",
            }),
          };
        }
        return { ok: true, status: 200, json: async () => ({}) };
      }
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useUploader({
        onImages: vi.fn(),
        onDocuments: vi.fn(),
        tag: "gallery",
        projectId: 7,
        threadId: 11,
        explicitAuth: true,
      })
    );

    const file = new File(["fake"], "image.png", { type: "image/png" });
    await act(async () => {
      await result.current.handleFiles([file]);
    });

    const mediaCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/media/upload/image")
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = normalizeHeaders(init?.headers);
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("gallery-dev-key");
    expect(headers["Authorization"] ?? headers["authorization"]).toBeUndefined();
    expect(init?.credentials).toBe("include");
  });

  it("reuses an existing project thread for gallery image uploads", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    setAuthToken(null);

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit): Promise<{
        ok: boolean;
        status: number;
        json: () => Promise<unknown>;
      }> => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === "/api/chat/threads" && init?.method === "GET") {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              threads: [
                {
                  id: 44,
                  project_id: 7,
                  title: "General uploads",
                },
              ],
            }),
          };
        }
        if (url === "/api/media/upload/image") {
          const form = init?.body as FormData | undefined;
          expect(form?.get("thread_id")).toBe("44");
          return {
            ok: true,
            status: 200,
            json: async () => ({
              id: "img-2",
              src_url: "/media/images/img-2.png",
              filename: "img-2.png",
            }),
          };
        }
        return { ok: true, status: 200, json: async () => ({}) };
      }
    );
    vi.stubGlobal("fetch", fetchMock);

    const onImages = vi.fn();
    const { result } = renderHook(() =>
      useUploader({
        onImages,
        onDocuments: vi.fn(),
        tag: "gallery",
        projectId: 7,
        explicitAuth: true,
      })
    );

    const file = new File(["fake"], "image.png", { type: "image/png" });
    await act(async () => {
      await result.current.handleFiles([file]);
    });

    expect(
      fetchMock.mock.calls.some(([url]) => url === "/api/chat/threads")
    ).toBe(true);
    expect(onImages).toHaveBeenCalledTimes(1);
  });

  it("creates a project-scoped upload thread when no project thread exists", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    setAuthToken(null);

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit): Promise<{
        ok: boolean;
        status: number;
        json: () => Promise<unknown>;
      }> => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === "/api/chat/threads" && init?.method === "GET") {
          return {
            ok: true,
            status: 200,
            json: async () => ({ threads: [] }),
          };
        }
        if (url === "/api/chat/threads" && init?.method === "POST") {
          expect(JSON.parse(String(init?.body)) as Record<string, unknown>).toMatchObject(
            {
              title: "Gallery uploads",
              project_id: 7,
            }
          );
          return {
            ok: true,
            status: 200,
            json: async () => ({
              ok: true,
              thread_id: 55,
              thread: { id: 55, title: "Gallery uploads" },
            }),
          };
        }
        if (url === "/api/media/upload/image") {
          const form = init?.body as FormData | undefined;
          expect(form?.get("thread_id")).toBe("55");
          return {
            ok: true,
            status: 200,
            json: async () => ({
              id: "img-3",
              src_url: "/media/images/img-3.png",
              filename: "img-3.png",
            }),
          };
        }
        return { ok: true, status: 200, json: async () => ({}) };
      }
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useUploader({
        onImages: vi.fn(),
        onDocuments: vi.fn(),
        tag: "gallery",
        projectId: 7,
        explicitAuth: true,
      })
    );

    const file = new File(["fake"], "image.png", { type: "image/png" });
    await act(async () => {
      await result.current.handleFiles([file]);
    });

    expect(
      fetchMock.mock.calls.some(
        ([url, init]) => url === "/api/chat/threads" && init?.method === "POST"
      )
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some(([url]) => url === "/api/media/upload/image")
    ).toBe(true);
  });

  it("sends no auth header when no token and no dev key are present", async () => {
    setAuthToken(null);

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ images: [], count: 0 }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ProjectContext.Provider
        value={{ projectId: "9", setProjectId: vi.fn() }}
      >
        <GalleryView onSelect={vi.fn()} />
      </ProjectContext.Provider>
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const mediaCall = fetchMock.mock.calls.find(([url]) =>
      String(url).startsWith("/api/media/images")
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = normalizeHeaders(init?.headers);
    expect(headers["Authorization"] ?? headers["authorization"]).toBeUndefined();
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBeUndefined();
    expect(init?.credentials).toBe("include");
  });
});
