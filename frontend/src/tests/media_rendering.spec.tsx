import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock("@/lib/authState", () => ({
  checkAuthGate: vi.fn(() => false),
  useAuthState: vi.fn(() => ({ token: null })),
}));

vi.mock("@/components/modals/ImageGenModal", () => ({
  ImageGenModal: () => null,
}));

import DashboardView from "@/components/dashboard/DashboardView";
import GalleryGrid from "@/components/gallery/GalleryGrid";
import MediaTile from "@/components/media/MediaTile";
import { resolveMediaAssetSrc } from "@/lib/mediaUrl";

describe("media rendering", () => {
  it("prefers src_url as the canonical image asset field", () => {
    expect(
      resolveMediaAssetSrc({
        src_url: "/media/images/right.png",
        url: "/media/images/wrong.png",
      })
    ).toBe("http://backend.test/media/images/right.png");
  });

  it("renders gallery images through the shared normalized media path", () => {
    const { container } = render(
      <GalleryGrid
        items={[
          {
            id: "gallery-1",
            src: "/media/images/gallery.png",
            prompt: "Gallery image",
          },
        ]}
        onOpen={vi.fn()}
      />
    );

    expect(screen.getByRole("img", { name: "Gallery image" })).toHaveAttribute(
      "src",
      "http://backend.test/media/images/gallery.png"
    );
    expect(container.querySelector(".codexifyMediaGrid--gallery")).toBeTruthy();
  });

  it("renders dashboard images through the shared normalized media path", () => {
    render(
      <DashboardView
        extColors={{
          pdf: "#000",
          doc: "#000",
          md: "#000",
          png: "#000",
          sketch: "#000",
          txt: "#000",
          docx: "#000",
          jpeg: "#000",
          codex: "#000",
        }}
        gallery={[
          {
            src: "/media/images/dashboard.png",
            prompt: "Dashboard image",
          },
        ]}
        onImagePrompt={vi.fn()}
        onRequestNewProject={vi.fn()}
        onRequestNewThread={vi.fn()}
        onNavigateDocuments={vi.fn()}
        onNavigateGallery={vi.fn()}
        threadGridRows={2}
      />
    );

    expect(
      screen.getByRole("img", { name: "Dashboard image" })
    ).toHaveAttribute("src", "http://backend.test/media/images/dashboard.png");
  });

  it("renders every dashboard image without truncating the list", () => {
    render(
      <DashboardView
        extColors={{
          pdf: "#000",
          doc: "#000",
          md: "#000",
          png: "#000",
          sketch: "#000",
          txt: "#000",
          docx: "#000",
          jpeg: "#000",
          codex: "#000",
        }}
        gallery={Array.from({ length: 14 }, (_, index) => ({
          src: `/media/images/dashboard-${index}.png`,
          prompt: `Dashboard image ${index}`,
        }))}
        onImagePrompt={vi.fn()}
        onRequestNewProject={vi.fn()}
        onRequestNewThread={vi.fn()}
        onNavigateDocuments={vi.fn()}
        onNavigateGallery={vi.fn()}
        threadGridRows={2}
      />
    );

    expect(screen.getAllByRole("img")).toHaveLength(14);
  });

  it("falls back cleanly when an image asset fails to load", () => {
    const { container } = render(
      <MediaTile id="tile-1" src="http://backend.test/broken.png" alt="Broken image" />
    );

    fireEvent.error(screen.getByRole("img", { name: "Broken image" }));

    expect(
      screen.queryByRole("img", { name: "Broken image" })
    ).not.toBeInTheDocument();
    expect(container.querySelector(".codexifyMediaTileFallback")).toBeTruthy();
  });
});
