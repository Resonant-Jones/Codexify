import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/gallery/GalleryGrid", () => ({
  default: ({ items }: { items: Array<{ id: string; prompt: string; tag: string }> }) => (
    <div data-testid="gallery-items">
      {items.map((item) => (
        <div key={item.id}>{`${item.prompt}:${item.tag}`}</div>
      ))}
    </div>
  ),
}));

vi.mock("@/components/modals/ImageGenModal", () => ({
  ImageGenModal: () => null,
}));

vi.mock("@/hooks/useUploader", () => ({
  default: () => ({
    onDrop: vi.fn(),
    onDragOver: vi.fn(),
    pick: vi.fn(),
    input: null,
  }),
}));

import GalleryView from "@/components/gallery/GalleryView";
import { ProjectContext } from "@/components/layout/ProjectContext";

function renderGallery() {
  return render(
    <ProjectContext.Provider value={{ projectId: "7", setProjectId: vi.fn() }}>
      <GalleryView onSelect={vi.fn()} />
    </ProjectContext.Provider>
  );
}

describe("GalleryView imported provenance", () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), "https://codexify.test");
    const tag = url.searchParams.get("tag") || "uploaded";
    return {
      ok: true,
      status: 200,
      json: async () => ({
        images: [
          {
            id: `${tag}-image`,
            project_id: 7,
            src_url: `/media/images/${tag}.png`,
            filename: `${tag}.png`,
            source_tag: tag,
          },
        ],
        count: 1,
      }),
    };
  });

  beforeEach(() => {
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.setItem("cfy.hideMockGallery", "1");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads uploaded, generated, and unclassified assets in All", async () => {
    renderGallery();

    await waitFor(() => {
      expect(screen.getByText("uploaded.png:uploaded")).toBeInTheDocument();
      expect(screen.getByText("generated.png:generated")).toBeInTheDocument();
      expect(
        screen.getByText("unclassified.png:unclassified")
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/Unclassified: 1 imported asset/)).toBeInTheDocument();
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(urls.some((url) => url.includes("tag=uploaded"))).toBe(true);
    expect(urls.some((url) => url.includes("tag=generated"))).toBe(true);
    expect(urls.some((url) => url.includes("tag=unclassified"))).toBe(true);
    expect(urls.every((url) => url.includes("limit=100"))).toBe(true);
  });

  it("keeps unclassified assets out of Uploaded and scopes that filter", async () => {
    renderGallery();
    await screen.findByText("unclassified.png:unclassified");

    fireEvent.click(screen.getByRole("button", { name: "Uploaded" }));

    await waitFor(() => {
      expect(screen.getByText("uploaded.png:uploaded")).toBeInTheDocument();
      expect(screen.queryByText("unclassified.png:unclassified")).toBeNull();
      expect(screen.queryByText("generated.png:generated")).toBeNull();
    });
    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    const lastUrl = String(lastCall?.[0]);
    expect(lastUrl).toContain("tag=uploaded");
    expect(lastUrl).toContain("project_id=7");
  });

  it("reloads backend truth when a committed media batch requests refresh", async () => {
    renderGallery();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    window.dispatchEvent(
      new CustomEvent("cfy:gallery:refresh", {
        detail: { source: "openai-account-import", job_id: "job-1" },
      })
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6));
  });
});
