import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  window.dispatchEvent(new Event("resize"));
}

describe("DocumentsView interactions", () => {
  beforeEach(() => {
    act(() => {
      setViewportWidth(1280);
    });
  });

  afterEach(() => {
    act(() => {
      setViewportWidth(1280);
    });
    requestWorkspaceOpenMock.mockReset();
    vi.restoreAllMocks();
  });

  it("anchors Scope on the left, Documents in the center, and Workspace to the right contract", () => {
    const onDocumentScopeChange = vi.fn();
    const { container } = render(
      <DocumentsView
        documents={[]}
        extColors={EXT_COLORS}
        documentScope="thread"
        onDocumentScopeChange={onDocumentScopeChange}
        threadScopeEnabled
      />
    );

    expect(screen.getByTestId("documents-layout")).toHaveAttribute(
      "data-documents-layout",
      "desktop_three_panel"
    );
    expect(screen.getByTestId("documents-layout")).toHaveAttribute(
      "data-workspace-anchor",
      "app-shell-right"
    );
    expect(screen.getByTestId("documents-layout").style.flexGrow).toBe("1");
    expect(screen.getByTestId("documents-layout").style.flexShrink).toBe("1");
    expect(screen.getByTestId("documents-layout").style.flexBasis).toBe("0%");
    expect(screen.getByTestId("documents-layout").style.minWidth).toBe("0");
    expect(screen.getByTestId("documents-layout").style.maxWidth).toBe("100%");
    expect(screen.getByTestId("documents-layout").style.display).toBe("grid");
    expect(screen.getByTestId("documents-scope-rail")).toBeInTheDocument();
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
    expect(screen.getByTestId("documents-upload-affordance")).toBeInTheDocument();
    expect(screen.getByTestId("documents-scope-actions").style.minWidth).toBe(
      "0"
    );
    expect(screen.getByTestId("documents-scope-actions").style.maxWidth).toBe(
      "100%"
    );
    expect(
      container.querySelector('[data-testid="documents-scope-actions"] > div')
    ).toHaveClass("w-full", "justify-between", "flex-wrap");

    expect(screen.getByRole("tab", { name: "Thread" })).toHaveAttribute(
      "data-state",
      "active"
    );
    fireEvent.click(screen.getByRole("tab", { name: "Project" }));
    expect(onDocumentScopeChange).toHaveBeenCalledWith("project");
    expect(screen.getByRole("tab", { name: "Project" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Open in Workspace/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Open in Thread/i })
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Applet|Workbench/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Prioritized|Knowledge Base|cost tier|book badge/i)
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

  it("switches to a mobile list layout and keeps document taps explicit", async () => {
    act(() => {
      setViewportWidth(390);
    });

    const { container } = render(
      <DocumentsView
        documents={[DOCUMENT]}
        extColors={EXT_COLORS}
        onDocumentScopeChange={vi.fn()}
        threadScopeEnabled
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId("documents-layout")).toHaveAttribute(
        "data-documents-layout",
        "mobile_stack"
      );
      expect(screen.getByTestId("documents-scope-rail")).toBeInTheDocument();
      expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
      expect(
        container.querySelector('[data-layout-mode="mobile-list"]')
      ).toBeTruthy();
    });

    expect(
      screen.getByTestId("documents-mobile-row-button-doc-1")
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Open Quarterly Plan in Workspace" })
    );

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
});
