import { act, render, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import GalleryView from "../components/gallery/GalleryView";
import { ProjectContext } from "../components/layout/ProjectContext";
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
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("authenticates gallery list reads explicitly", async () => {
    vi.stubEnv("VITE_USE_PROXY", "true");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "gallery-key");

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
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("gallery-key");
    expect(init?.credentials).toBe("include");
  });

  it("authenticates gallery uploads explicitly", async () => {
    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubEnv("VITE_USE_PROXY", "true");
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "gallery-key");

    const fetchMock = vi.fn(
      async (input: RequestInfo | URL): Promise<{
        ok: boolean;
        status: number;
        json: () => Promise<unknown>;
      }> => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === "/api/media/upload/image") {
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

    const mediaCall = fetchMock.mock.calls.find(
      ([url]) => url === "/api/media/upload/image"
    );
    expect(mediaCall).toBeDefined();
    const init = mediaCall?.[1] as RequestInit | undefined;
    const headers = normalizeHeaders(init?.headers);
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("gallery-key");
    expect(init?.credentials).toBe("include");
  });
});
