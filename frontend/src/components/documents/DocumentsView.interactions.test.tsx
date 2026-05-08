import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DocumentsView from "@/components/documents/DocumentsView";
import type { ExtColors } from "@/types/ui";

const { requestWorkspaceOpenMock, uploaderMocks } = vi.hoisted(() => ({
  requestWorkspaceOpenMock: vi.fn(() => true),
  uploaderMocks: {
    configs: [] as Array<Record<string, unknown>>,
    onDrop: vi.fn(),
    onDragOver: vi.fn(),
    pick: vi.fn(),
  },
}));

vi.mock("@/features/workspace/state/useWorkspaceState", () => ({
  requestWorkspaceOpen: requestWorkspaceOpenMock,
}));

vi.mock("@/hooks/useUploader", () => ({
  default: (config: Record<string, unknown>) => {
    uploaderMocks.configs.push(config);
    return {
      handleFiles: vi.fn(),
      onDrop: uploaderMocks.onDrop,
      onDragOver: uploaderMocks.onDragOver,
      pick: uploaderMocks.pick,
    };
  },
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
    uploaderMocks.configs = [];
    uploaderMocks.onDrop.mockReset();
    uploaderMocks.onDragOver.mockReset();
    uploaderMocks.pick.mockReset();
    vi.restoreAllMocks();
  });

  it("keeps DocumentsView focused on the center lane without a route-local rail", () => {
    render(
      <DocumentsView
        documents={[]}
        extColors={EXT_COLORS}
      />
    );

    expect(screen.getByTestId("documents-layout")).toHaveAttribute(
      "data-documents-layout",
      "center_lane"
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
    expect(screen.getByTestId("documents-layout").style.padding).toBe("0px");
    expect(screen.getByTestId("documents-layout").style.display).toBe("flex");
    expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
    expect(screen.getByTestId("documents-upload-affordance")).toBeInTheDocument();
    fireEvent.drop(screen.getByTestId("documents-drop-zone"));
    expect(uploaderMocks.onDrop).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "choose files" }));
    expect(uploaderMocks.pick).toHaveBeenCalledTimes(1);
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

  it("preserves center lane usability when sidebar is dismissed in the shell", () => {
    render(
      <DocumentsView
        documents={[]}
        extColors={EXT_COLORS}
      />
    );

    const layout = screen.getByTestId("documents-layout");
    expect(layout).toHaveAttribute("data-documents-layout", "center_lane");
    expect(layout.style.flex).toBe("1 1 0%");
    expect(layout.style.minWidth).toBe("0");
    expect(layout.style.maxWidth).toBe("100%");
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
  });

  it("forwards the selected project and thread into the uploader context", () => {
    render(
      <DocumentsView
        documents={[]}
        extColors={EXT_COLORS}
        projectId={42}
        threadId={101}
      />
    );

    expect(uploaderMocks.configs).toHaveLength(1);
    expect(uploaderMocks.configs[0]).toEqual(
      expect.objectContaining({
        tag: "upload",
        projectId: 42,
        threadId: 101,
      })
    );
  });

  it("opens the workspace on primary click", () => {
    render(
      <DocumentsView
        documents={[DOCUMENT]}
        extColors={EXT_COLORS}
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
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId("documents-layout")).toHaveAttribute(
        "data-documents-layout",
        "mobile_stack"
      );
      expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
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
