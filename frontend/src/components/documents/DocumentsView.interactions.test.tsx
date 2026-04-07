import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentsView from "@/components/documents/DocumentsView";
import type { ExtColors } from "@/types/ui";

const { requestWorkspaceOpenMock } = vi.hoisted(() => ({
  requestWorkspaceOpenMock: vi.fn(() => true),
}));

vi.mock("@/features/workspace/state/useWorkspaceState", () => ({
  requestWorkspaceOpen: requestWorkspaceOpenMock,
}));

vi.mock("@/hooks/useUploader", () => ({
  default: () => ({
    onDrop: vi.fn(),
    onDragOver: vi.fn(),
    pick: vi.fn(),
  }),
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

const DOCUMENT = {
  id: "doc-1",
  title: "Quarterly Plan",
  name: "Quarterly Plan",
  ext: "pdf",
  type: "file" as const,
  src_url: "/media/documents/doc-1.pdf",
};

describe("DocumentsView interactions", () => {
  afterEach(() => {
    requestWorkspaceOpenMock.mockReset();
    vi.restoreAllMocks();
  });

  it("shows only the Thread and Project scope pills in the header", () => {
    render(
      <DocumentsView
        documents={[]}
        extColors={EXT_COLORS}
        documentScope="thread"
        onDocumentScopeChange={vi.fn()}
        threadScopeEnabled
      />
    );

    expect(screen.getByRole("button", { name: "Thread" })).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByRole("button", { name: "Project" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Open in Workspace/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Open in Thread/i })
    ).not.toBeInTheDocument();
  });

  it("opens the workspace on primary click", () => {
    render(
      <DocumentsView
        documents={[DOCUMENT]}
        extColors={EXT_COLORS}
        onDocumentScopeChange={vi.fn()}
        threadScopeEnabled
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Quarterly Plan" }));

    expect(requestWorkspaceOpenMock).toHaveBeenCalledWith(
      expect.objectContaining({
        doc: expect.objectContaining({
          id: "doc-1",
          title: "Quarterly Plan",
          ext: "pdf",
        }),
        source: "documents",
        targetView: "documents",
      }),
      expect.objectContaining({
        source: "documents",
        targetView: "documents",
      })
    );
  });

  it("offers Open in Thread from the document context menu", async () => {
    const onOpenInThread = vi.fn();

    render(
      <DocumentsView
        documents={[DOCUMENT]}
        extColors={EXT_COLORS}
        onOpenInThread={onOpenInThread}
        onDocumentScopeChange={vi.fn()}
        threadScopeEnabled
      />
    );

    fireEvent.contextMenu(screen.getByRole("button", { name: "Quarterly Plan" }));

    const menuItem = await screen.findByRole("menuitem", { name: "Open in Thread" });
    fireEvent.click(menuItem);

    await waitFor(() => {
      expect(onOpenInThread).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "doc-1",
          title: "Quarterly Plan",
        })
      );
    });
  });
});
