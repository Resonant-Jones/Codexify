import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { downloadAsset, deleteAsset } = vi.hoisted(() => ({
  downloadAsset: vi.fn(),
  deleteAsset: vi.fn(),
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
}));

vi.mock("@/lib/assetActions", () => ({
  downloadAsset,
  deleteAsset,
  notifyAssetActionError: vi.fn(),
  resolveAssetDownloadUrl: (url?: string) => url || "",
}));

import DocumentTile from "@/components/documents/DocumentTile";
import MediaTile from "@/components/media/MediaTile";

describe("asset context menu", () => {
  beforeEach(() => {
    downloadAsset.mockReset();
    deleteAsset.mockReset();
  });

  it("opens and dismisses the shared document menu from right-click", () => {
    render(
      <DocumentTile
        file={{
          id: "doc-1",
          name: "Quarterly Plan.pdf",
          ext: "pdf",
          src_url: "/media/documents/doc-1.pdf",
        }}
      />
    );

    fireEvent.contextMenu(screen.getByLabelText("Quarterly Plan.pdf"));
    expect(
      screen.getByRole("menu", { name: "Quarterly Plan.pdf actions" })
    ).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(
      screen.queryByRole("menu", { name: "Quarterly Plan.pdf actions" })
    ).not.toBeInTheDocument();
  });

  it("routes document download and delete through shared asset helpers", async () => {
    const onDeleted = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <DocumentTile
        file={{
          id: "doc-1",
          name: "Quarterly Plan.pdf",
          ext: "pdf",
          src_url: "/media/documents/doc-1.pdf",
        }}
        onDeleted={onDeleted}
      />
    );

    fireEvent.contextMenu(screen.getByLabelText("Quarterly Plan.pdf"));
    fireEvent.click(screen.getByRole("menuitem", { name: "Download" }));

    await waitFor(() =>
      expect(downloadAsset).toHaveBeenCalledWith({
        url: "/media/documents/doc-1.pdf",
        filename: "Quarterly Plan.pdf",
      })
    );

    fireEvent.contextMenu(screen.getByLabelText("Quarterly Plan.pdf"));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() =>
      expect(deleteAsset).toHaveBeenCalledWith({
        kind: "document",
        id: "doc-1",
      })
    );
    expect(onDeleted).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("routes image download and delete through the same shared menu path", async () => {
    const onDeleted = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <MediaTile
        id="tile-1"
        assetId="image-1"
        src="/media/images/dashboard.png"
        alt="Dashboard image"
        onDeleted={onDeleted}
      />
    );

    fireEvent.contextMenu(screen.getByLabelText("Dashboard image"));
    expect(
      screen.getByRole("menu", { name: "Dashboard image actions" })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("menuitem", { name: "Download" }));
    await waitFor(() =>
      expect(downloadAsset).toHaveBeenCalledWith({
        url: "http://backend.test/media/images/dashboard.png",
        filename: "Dashboard image",
      })
    );

    fireEvent.contextMenu(screen.getByLabelText("Dashboard image"));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() =>
      expect(deleteAsset).toHaveBeenCalledWith({
        kind: "image",
        id: "image-1",
      })
    );
    expect(onDeleted).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
