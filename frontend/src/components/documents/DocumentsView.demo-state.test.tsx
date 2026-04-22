import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DocumentsView from "@/components/documents/DocumentsView";
import type { ExtColors } from "@/types/ui";

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  window.dispatchEvent(new Event("resize"));
}

vi.mock("@/hooks/useUploader", () => ({
  default: () => ({
    onDrop: vi.fn(),
    onDragOver: vi.fn(),
    pick: vi.fn(),
  }),
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

const EXT_COLORS: ExtColors = {
  pdf: "#111111",
  doc: "#111111",
  md: "#111111",
  png: "#111111",
  sketch: "#111111",
  txt: "#111111",
  docx: "#111111",
  jpeg: "#111111",
  codex: "#111111",
};

describe("DocumentsView demo content", () => {
  beforeEach(() => {
    setViewportWidth(1280);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders demo documents when no real documents exist and removes the manual mock toggle", () => {
    const { container } = render(
      <DocumentsView
        documents={[
          {
            id: "mock-doc-1",
            title: "Demo Brief",
            name: "Demo Brief",
            ext: "pdf",
            type: "file",
            mock: true,
          },
        ]}
        extColors={EXT_COLORS}
      />
    );

    expect(screen.getByText("Demo Brief")).toBeInTheDocument();
    expect(screen.queryByText("Hide Mock Items")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(container.querySelector(".fc-root")).toBeNull();
  });

  it("auto-hides demo documents once real documents exist", () => {
    render(
      <DocumentsView
        documents={[
          {
            id: "real-doc-1",
            title: "User Plan",
            name: "User Plan",
            ext: "md",
            type: "file",
          },
          {
            id: "mock-doc-1",
            title: "Demo Brief",
            name: "Demo Brief",
            ext: "pdf",
            type: "file",
            mock: true,
          },
        ]}
        extColors={EXT_COLORS}
      />
    );

    expect(screen.getByText("User Plan")).toBeInTheDocument();
    expect(screen.queryByText("Demo Brief")).not.toBeInTheDocument();
    expect(screen.queryByText("Hide Mock Items")).not.toBeInTheDocument();
  });
});
