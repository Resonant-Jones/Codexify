import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { deleteAssetMock, downloadAssetMock } = vi.hoisted(() => ({
  deleteAssetMock: vi.fn(),
  downloadAssetMock: vi.fn(),
}));

vi.mock("@/lib/assetActions", () => ({
  deleteAsset: deleteAssetMock,
  downloadAsset: downloadAssetMock,
  notifyAssetActionError: vi.fn(),
  resolveAssetDownloadUrl: (url?: string) => url || "",
}));

import GalleryGrid from "@/components/gallery/GalleryGrid";
import type { GalleryItem } from "@/types/gallery";

describe("GalleryGrid", () => {
  afterEach(() => {
    deleteAssetMock.mockReset();
    downloadAssetMock.mockReset();
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders one tile per gallery item", () => {
    const items: GalleryItem[] = [
      {
        id: "uploaded_image:img-1",
        deletionId: "img-1",
        src: "/media/images/one.png",
        prompt: "First image",
        project: 11,
        tag: "uploaded",
      },
      { src: "/media/images/two.png", prompt: "Second image" },
    ];

    render(<GalleryGrid items={items} onOpen={vi.fn()} />);

    expect(screen.getByRole("button", { name: "First image" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Second image" })).toBeInTheDocument();
  });

  it("labels each tile with its provenance", () => {
    const items: GalleryItem[] = [
      {
        id: "uploaded_image:img-1",
        deletionId: "img-1",
        src: "/media/images/one.png",
        prompt: "First image",
        tag: "uploaded",
      },
      { src: "/media/images/two.png", prompt: "Second image" },
    ];

    render(<GalleryGrid items={items} onOpen={vi.fn()} />);

    expect(screen.getByText("Uploaded")).toBeInTheDocument();
    expect(screen.getByText("Unclassified")).toBeInTheDocument();
  });

  it("reports the opened item to its owner", () => {
    const onOpen = vi.fn();
    const items: GalleryItem[] = [
      {
        id: "uploaded_image:img-1",
        deletionId: "img-1",
        src: "/media/images/one.png",
        prompt: "First image",
      },
    ];

    render(<GalleryGrid items={items} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button", { name: "First image" }));

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(items[0]);
  });

  it("deletes the canonical source identifier, never the tile identity", async () => {
    const onDelete = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    deleteAssetMock.mockResolvedValue(undefined);
    const items: GalleryItem[] = [
      {
        id: "uploaded_image:img-1",
        deletionId: "img-1",
        src: "/media/images/one.png",
        prompt: "First image",
      },
    ];

    render(<GalleryGrid items={items} onOpen={vi.fn()} onDelete={onDelete} />);
    fireEvent.contextMenu(screen.getByRole("button", { name: "First image" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith(items[0]);
    });
    expect(confirmSpy).toHaveBeenCalled();
    expect(deleteAssetMock).toHaveBeenCalledWith({ kind: "image", id: "img-1" });
    expect(deleteAssetMock).not.toHaveBeenCalledWith({
      kind: "image",
      id: "uploaded_image:img-1",
    });
  });

  it("offers no Delete action without a deletion identifier", () => {
    const items: GalleryItem[] = [
      {
        id: "generated_image:gen-1",
        src: "/media/images/generated.png",
        prompt: "Generated image",
      },
    ];

    render(<GalleryGrid items={items} onOpen={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.contextMenu(screen.getByRole("button", { name: "Generated image" }));

    expect(screen.queryByRole("menuitem", { name: "Delete" })).not.toBeInTheDocument();
    expect(deleteAssetMock).not.toHaveBeenCalled();
  });

  it("keeps the download action for a deletable item", async () => {
    const items: GalleryItem[] = [
      {
        id: "uploaded_image:img-1",
        deletionId: "img-1",
        src: "/media/images/one.png",
        prompt: "First image",
      },
    ];

    render(<GalleryGrid items={items} onOpen={vi.fn()} />);
    fireEvent.contextMenu(screen.getByRole("button", { name: "First image" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Download" }));

    await waitFor(() => {
      expect(downloadAssetMock).toHaveBeenCalledWith({
        url: "/media/images/one.png",
        filename: "First image",
      });
    });
  });
});
