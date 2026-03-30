import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const {
  invokeTauriCommandMock,
  deleteAssetMock,
  downloadAssetMock,
  setTauriRuntime,
  getTauriRuntime,
} =
  vi.hoisted(() => {
    const state = {
      invokeTauriCommandMock: vi.fn(),
      deleteAssetMock: vi.fn(),
      downloadAssetMock: vi.fn(),
      tauriRuntime: false,
    };

    return {
      invokeTauriCommandMock: state.invokeTauriCommandMock,
      deleteAssetMock: state.deleteAssetMock,
      downloadAssetMock: state.downloadAssetMock,
      setTauriRuntime: (value: boolean) => {
        state.tauriRuntime = value;
      },
      getTauriRuntime: () => state.tauriRuntime,
    };
  });

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
  getRuntimeConfigSync: () => ({
    mode: getTauriRuntime() ? "tauri" : "web",
    backendBaseUrl: "http://backend.test",
    apiBaseUrl: "http://backend.test/api",
    sseUrl: "http://backend.test/api/events",
    sharePublicBaseUrl: "http://share.test",
    authMode: "local",
  }),
  isTauriRuntime: () => getTauriRuntime(),
  invokeTauriCommand: invokeTauriCommandMock,
}));

vi.mock("@/lib/assetActions", () => ({
  deleteAsset: deleteAssetMock,
  downloadAsset: downloadAssetMock,
  notifyAssetActionError: vi.fn(),
  resolveAssetDownloadUrl: (url?: string) => url || "",
}));

import DocumentTile from "@/components/documents/DocumentTile";
import MediaTile from "@/components/media/MediaTile";

describe("MediaTile desktop media rendering", () => {
  afterEach(() => {
    setTauriRuntime(false);
    invokeTauriCommandMock.mockReset();
    deleteAssetMock.mockReset();
    downloadAssetMock.mockReset();
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders backend-owned gallery media through the desktop fetch contract in Tauri", async () => {
    setTauriRuntime(true);
    invokeTauriCommandMock.mockResolvedValue({
      contentType: "image/png",
      bytesBase64: "aGVsbG8=",
      sizeBytes: 5,
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:gallery-image"),
    });

    render(
      <MediaTile
        id="gallery-media"
        src="/media/images/gallery-tauri.png?sig=abc123#viewer"
        alt="Gallery image"
      />
    );

    const image = await screen.findByRole("img", { name: "Gallery image" });
    expect(image).toHaveAttribute("src", "blob:gallery-image");
    expect(invokeTauriCommandMock).toHaveBeenCalledWith(
      "desktop_fetch_media",
      { path: "/media/images/gallery-tauri.png" }
    );
  });

  it("preserves the restored document tile layout contract", () => {
    render(
      <DocumentTile
        file={{
          name: "Quarterly Plan.pdf",
          ext: "pdf",
          embeddingStatus: "processing",
        }}
      />
    );

    const tile = screen.getByLabelText("Quarterly Plan.pdf");
    const body = tile.querySelector('[data-slot="document-tile-body"]');
    const footer = tile.querySelector('[data-slot="document-tile-footer"]');
    const name = tile.querySelector('[data-slot="document-tile-name"]');
    const extension = tile.querySelector('[data-slot="document-tile-extension"]');
    const statusWrap = tile.querySelector('[data-slot="document-tile-status-wrap"]');
    const status = tile.querySelector('[data-slot="document-tile-status"]');
    const icon = body?.querySelector("svg");

    expect(tile).toHaveClass("rounded-[var(--tile-radius)]");
    expect(tile).toHaveStyle("border-radius: var(--tile-radius)");

    expect(body).toHaveClass("items-center", "justify-center");
    expect(footer).toHaveClass("min-h-[54px]", "items-center", "justify-center", "text-center");
    expect(name).toHaveTextContent("Quarterly Plan");
    expect(extension).toHaveTextContent(".pdf");

    expect(statusWrap).toHaveClass("justify-center");
    expect(status).toHaveTextContent("Processing");
    expect(icon).toHaveStyle({ color: "#ef4444" });
    expect(footer).toHaveStyle({ background: "#ef4444" });
  });
});
