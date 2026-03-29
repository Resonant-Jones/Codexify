import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

import WorkspacePane from "./WorkspacePane";

describe("WorkspacePane", () => {
  it("classifies signed image URLs as images while ignoring query and hash", () => {
    render(
      <WorkspacePane
        activeDoc={{
          id: "img-1",
          title: "Signed image",
          ext: "jpg",
          type: "file",
          src_url: "/media/images/signed.jpg?sig=abc123&download=1#viewer",
        }}
      />
    );

    expect(screen.getByRole("img", { name: "Signed image" })).toHaveAttribute(
      "src",
      "http://backend.test/opaque-preview"
    );
  });

  it("classifies signed PDF URLs as PDFs while ignoring query and hash", () => {
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
  });
});
