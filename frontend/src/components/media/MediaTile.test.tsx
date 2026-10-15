import { fireEvent, render, screen } from "@testing-library/react";
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

  it("preserves the three-region document tile layout contract", () => {
    render(
      <DocumentTile
        file={{
          name: "Quarterly Plan.pdf",
          ext: "pdf",
          embeddingStatus: "processing",
          provenanceLabel: "Uploaded document",
        }}
      />
    );

    const tile = screen.getByLabelText("Quarterly Plan.pdf");
    const content = tile.querySelector('[data-slot="document-tile"]');
    const identity = tile.querySelector('[data-slot="document-tile-identity"]');
    const filename = tile.querySelector('[data-slot="document-tile-filename"]');
    const metadata = tile.querySelector('[data-slot="document-tile-metadata"]');
    const name = tile.querySelector('[data-slot="document-tile-name"]');
    const extension = tile.querySelector('[data-slot="document-tile-extension"]');
    const status = tile.querySelector('[data-slot="document-tile-status"]');
    const icon = tile.querySelector('[data-slot="document-tile-icon"]');
    const provenance = tile.querySelector('[data-slot="document-tile-provenance"]');

    expect(tile).toHaveClass("rounded-[var(--tile-radius)]");
    expect(tile).toHaveStyle("border-radius: var(--tile-radius)");
    expect((tile as HTMLElement).style.getPropertyValue("--tile-size")).toBe("112px");
    expect(content).toHaveClass("grid", "h-full");
    expect(content).toHaveStyle({ gridTemplateRows: "minmax(0, 1fr) 28px 30px" });
    expect(Array.from(content!.children).filter((child) => child.hasAttribute("data-slot")))
      .toEqual([identity, filename, metadata]);
    for (const region of [identity, filename, metadata]) {
      expect(region).toHaveClass("min-h-0", "min-w-0", "overflow-hidden");
    }
    expect(identity).toContainElement(icon);
    expect(identity).toContainElement(status);
    expect(status).toHaveTextContent("Processing");
    expect(icon).toHaveClass("shrink-0");
    expect(filename).toContainElement(name);
    expect(name).toHaveTextContent(/^Quarterly Plan$/);
    expect(name).toHaveAttribute("title", "Quarterly Plan.pdf");
    expect(name).toHaveClass("line-clamp-2", "max-h-7", "leading-[14px]");
    expect(name).toHaveStyle({ overflowWrap: "break-word" });
    expect(metadata).toContainElement(extension);
    expect(metadata).toContainElement(provenance);
    expect(provenance).toHaveClass("truncate");
    expect(extension).toHaveTextContent(".pdf");
    expect(icon?.querySelector("svg")).toHaveStyle({ color: "#ef4444" });
    expect(metadata).toHaveStyle({ background: "#ef4444", color: "#111827" });
  });

  it("bounds a long filename independently of provenance and preserves custom extension colors", () => {
    window.localStorage.setItem("cfy.extColors", JSON.stringify({ md: "#123456" }));
    const baseName = "A very long document name with several words and an_unusually_long_unbroken_identifier";
    render(<DocumentTile file={{ name: `${baseName}.md`, provenanceLabel: "Generated from a long source description" }} />);

    const tile = screen.getByLabelText(`${baseName}.md`);
    const name = tile.querySelector('[data-slot="document-tile-name"]');
    const metadata = tile.querySelector('[data-slot="document-tile-metadata"]');
    expect(name).toHaveTextContent(baseName);
    expect(name).toHaveAttribute("title", `${baseName}.md`);
    expect(name).toHaveClass("line-clamp-2", "max-h-7", "leading-[14px]", "text-[11px]");
    expect(name).toHaveStyle({ overflowWrap: "break-word" });
    expect(metadata).not.toContainElement(name);
    expect(metadata).toHaveTextContent(".md");
    expect(metadata).toHaveStyle({ background: "#123456", color: "#ffffff" });
    expect(tile.querySelector('[data-slot="document-tile-icon"] svg')).toHaveStyle({ color: "#123456" });
  });

  it("preserves primary click and uploaded document context actions", () => {
    const onClick = vi.fn();
    render(<DocumentTile file={{ id: "doc-1", name: "Plan.pdf", src_url: "/media/plan.pdf" }} onClick={onClick} />);
    const tile = screen.getByRole("button", { name: "Plan.pdf" });
    fireEvent.click(tile);
    expect(onClick).toHaveBeenCalledTimes(1);
    fireEvent.contextMenu(tile);
    expect(screen.getByRole("menu", { name: "Plan.pdf actions" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Delete" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitem", { name: "Download" }));
    expect(downloadAssetMock).toHaveBeenCalledWith({ url: "/media/plan.pdf", filename: "Plan.pdf" });
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
