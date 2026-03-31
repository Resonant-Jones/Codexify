import { renderHook, waitFor } from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const runtimeState = vi.hoisted(() => ({
  invokeTauriCommandMock: vi.fn(),
  tauriRuntime: false,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
  getRuntimeConfigSync: () => ({
    mode: runtimeState.tauriRuntime ? "tauri" : "web",
    backendBaseUrl: "http://backend.test",
    apiBaseUrl: "http://backend.test/api",
    sseUrl: "http://backend.test/api/events",
    sharePublicBaseUrl: "http://share.test",
    authMode: "local",
  }),
  isTauriRuntime: () => runtimeState.tauriRuntime,
  invokeTauriCommand: runtimeState.invokeTauriCommandMock,
}));

import {
  __resetDesktopMediaCacheForTests,
  useRenderableMediaSrc,
} from "@/hooks/useRenderableMediaSrc";

type DeferredPromise<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T | PromiseLike<T>) => void;
};

function deferred<T>(): DeferredPromise<T> {
  let resolve!: DeferredPromise<T>["resolve"];
  let reject!: DeferredPromise<T>["reject"];
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, reject, resolve };
}

describe("useRenderableMediaSrc", () => {
  const createObjectURLMock = vi.fn();
  const revokeObjectURLMock = vi.fn();

  beforeEach(() => {
    runtimeState.tauriRuntime = false;
    runtimeState.invokeTauriCommandMock.mockReset();
    createObjectURLMock.mockReset();
    revokeObjectURLMock.mockReset();
    createObjectURLMock
      .mockReturnValueOnce("blob:renderable-1")
      .mockReturnValueOnce("blob:renderable-2");
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURLMock,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURLMock,
    });
  });

  afterEach(() => {
    __resetDesktopMediaCacheForTests();
    runtimeState.tauriRuntime = false;
  });

  it("keeps direct normalized URLs outside the desktop runtime", () => {
    const { result } = renderHook(() =>
      useRenderableMediaSrc("/media/images/right.png?sig=abc123#viewer")
    );

    expect(result.current).toEqual({
      src: "http://backend.test/media/images/right.png?sig=abc123#viewer",
      status: "ready",
      isBackendOwned: true,
    });
    expect(runtimeState.invokeTauriCommandMock).not.toHaveBeenCalled();
  });

  it("fetches backend-owned media through the desktop command in Tauri", async () => {
    runtimeState.tauriRuntime = true;
    runtimeState.invokeTauriCommandMock.mockResolvedValue({
      contentType: "image/png",
      bytesBase64: "aGVsbG8=",
      sizeBytes: 5,
    });

    const { result } = renderHook(() =>
      useRenderableMediaSrc(
        "http://backend.test/media/images/right.png?sig=abc123#viewer"
      )
    );

    await waitFor(() => expect(result.current.status).toBe("ready"));

    expect(runtimeState.invokeTauriCommandMock).toHaveBeenCalledWith(
      "desktop_fetch_media",
      {
        path: "/media/images/right.png",
      }
    );
    expect(result.current).toEqual({
      src: "blob:renderable-1",
      status: "ready",
      isBackendOwned: true,
    });
  });

  it("passes through external images even in Tauri", () => {
    runtimeState.tauriRuntime = true;

    const { result } = renderHook(() =>
      useRenderableMediaSrc("https://cdn.example.com/image.png?sig=abc123")
    );

    expect(result.current).toEqual({
      src: "https://cdn.example.com/image.png?sig=abc123",
      status: "ready",
      isBackendOwned: false,
    });
    expect(runtimeState.invokeTauriCommandMock).not.toHaveBeenCalled();
  });

  it("maps structured desktop fetch errors to a boring error state", async () => {
    runtimeState.tauriRuntime = true;
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    runtimeState.invokeTauriCommandMock.mockRejectedValue({
      kind: "too_large",
      detail: "Desktop media fetch exceeded limit.",
    });

    const { result } = renderHook(() =>
      useRenderableMediaSrc("/media/images/huge.png?sig=abc123")
    );

    await waitFor(() => expect(result.current.status).toBe("error"));

    expect(result.current).toEqual({
      src: "",
      status: "error",
      isBackendOwned: true,
    });
    expect(runtimeState.invokeTauriCommandMock).toHaveBeenCalledTimes(1);
    expect(debugSpy).toHaveBeenCalledWith("[desktop-media]", {
      path: "/media/images/huge.png",
      kind: "too_large",
      detail: "Desktop media fetch exceeded limit.",
    });
    debugSpy.mockRestore();
  });

  it("dedupes in-flight desktop fetches and revokes blob URLs during cache teardown", async () => {
    runtimeState.tauriRuntime = true;
    const pendingFetch = deferred<{
      contentType: string;
      bytesBase64: string;
      sizeBytes: number;
    }>();
    runtimeState.invokeTauriCommandMock.mockReturnValueOnce(pendingFetch.promise);

    const first = renderHook(() =>
      useRenderableMediaSrc("/media/images/shared.png?sig=abc123")
    );
    const second = renderHook(() =>
      useRenderableMediaSrc("/media/images/shared.png?sig=abc123")
    );

    await waitFor(() =>
      expect(runtimeState.invokeTauriCommandMock).toHaveBeenCalledTimes(1)
    );

    pendingFetch.resolve({
      contentType: "image/png",
      bytesBase64: "aGVsbG8=",
      sizeBytes: 5,
    });

    await waitFor(() => expect(first.result.current.status).toBe("ready"));
    await waitFor(() => expect(second.result.current.status).toBe("ready"));

    expect(first.result.current.src).toBe("blob:renderable-1");
    expect(second.result.current.src).toBe("blob:renderable-1");

    first.unmount();
    second.unmount();
    __resetDesktopMediaCacheForTests();

    expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:renderable-1");
  });
});
