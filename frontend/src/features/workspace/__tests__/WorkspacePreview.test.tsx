import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/api/codex", () => ({
  getCodexEntry: vi.fn(),
  getCodexExportUrl: vi.fn(() => "/exports/codex.md"),
}));

vi.mock("@/lib/mediaUrl", async () => {
  const actual = await vi.importActual<typeof import("@/lib/mediaUrl")>(
    "@/lib/mediaUrl"
  );
  return {
    ...actual,
    resolveMediaSrc: vi.fn(() => "http://backend.test/opaque-preview"),
  };
});

import WorkspacePane from "../WorkspacePane";

describe("WorkspacePreview", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps PDF previews working for signed URLs", () => {
    render(
      <WorkspacePane
        activeDoc={{
          id: "pdf-1",
          title: "Signed PDF",
          ext: "pdf",
          type: "file",
          src_url: "http://assets.example.test/media/documents/guide.pdf?sig=pdf123#page=2",
        }}
      />
    );

    expect(screen.getByTitle("Signed PDF")).toHaveAttribute(
      "src",
      "http://backend.test/opaque-preview"
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders txt, md, and json documents inline", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        text: async () => "local-first line one\nline two",
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () => "# Launch Notes\n\n- Synced selectively",
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () => '{"mode":"local-first","ok":true}',
      });

    const { rerender } = render(
      <WorkspacePane
        activeDoc={{
          id: "txt-1",
          title: "Notes",
          ext: "txt",
          type: "file",
          src_url: "/media/documents/notes.txt?sig=txt123#viewer",
        }}
      />
    );

    expect(await screen.findByText(/local-first line one/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/opaque-preview",
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );

    rerender(
      <WorkspacePane
        activeDoc={{
          id: "md-1",
          title: "Launch Notes",
          ext: "md",
          type: "file",
          src_url: "/media/documents/launch.md?sig=md123#viewer",
        }}
      />
    );

    expect(await screen.findByText("Synced selectively")).toBeInTheDocument();

    rerender(
      <WorkspacePane
        activeDoc={{
          id: "json-1",
          title: "Manifest",
          ext: "json",
          type: "file",
          src_url: "/media/documents/manifest.json?sig=json123#viewer",
        }}
      />
    );

    expect(
      await screen.findByText((content) =>
        content.includes('"mode": "local-first"')
      )
    ).toBeInTheDocument();
  });

  it("shows the explicit fallback state for unsupported files", () => {
    render(
      <WorkspacePane
        activeDoc={{
          id: "csv-1",
          title: "Report",
          ext: "csv",
          type: "file",
          src_url: "/media/documents/report.csv?sig=csv123#viewer",
        }}
      />
    );

    expect(
      screen.getByText("This file type does not have an inline preview yet.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open in a new tab" })
    ).toHaveAttribute("href", "http://backend.test/opaque-preview");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
