import React from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/documents/DocumentTile", () => ({
  default: ({
    file,
    onClick,
  }: {
    file: { name: string };
    onClick?: () => void;
  }) => (
    <button type="button" onClick={onClick}>
      {file.name}
    </button>
  ),
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/hooks/useUploader", () => ({
  default: () => ({
    onDrop: vi.fn(),
    onDragOver: vi.fn(),
    pick: vi.fn(),
    uploading: false,
  }),
}));

vi.mock("@/components/bootstrap/BootstrapGate", () => ({
  default: () => <div data-testid="bootstrap-gate-mock" />,
}));

vi.mock("@/components/DocumentGenModal", () => ({
  default: () => null,
}));

vi.mock("@/components/persona/layout/AppShell", () => ({
  default: () => <div data-testid="app-shell-mock" />,
}));

vi.mock("@/components/TopBar", () => ({
  TopBar: () => null,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@/features/commandCenter/CommandCenterPage", () => ({
  default: () => <div data-testid="command-center-mock" />,
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(async () => ({ data: {} })),
    post: vi.fn(async () => ({ data: {} })),
  },
}));

vi.mock("@/lib/runtimeBootstrap", () => ({
  appendBootstrapDetail: vi.fn((_existing?: string, incoming?: string) => incoming ?? ""),
  BOOTSTRAP_LOG_SERVICES: ["backend"],
  createCheckingRuntimeBootstrapState: vi.fn(() => ({
    status: "ready",
    stepResults: {},
  })),
  createBootstrapSupportNoticeFromDockerOpenResult: vi.fn(() => null),
  createBootstrapSupportNoticeFromLogResult: vi.fn(() => null),
  createBootstrapSupportNoticeFromRestartResult: vi.fn(() => null),
  createComposeRecoveryStepResult: vi.fn(() => ({ ok: true })),
  createFailedRuntimeBootstrapState: vi.fn(() => ({
    status: "failed",
    stepResults: {},
  })),
  createPreparingLocalConfigState: vi.fn(() => ({
    status: "preparing-local-config",
    stepResults: {},
  })),
  createReadyForWelcomeState: vi.fn(() => ({
    status: "ready-for-welcome",
    stepResults: {},
  })),
  createStartingLocalServicesState: vi.fn(() => ({
    status: "starting-local-services",
    stepResults: {},
  })),
  createWaitingForReadyState: vi.fn(() => ({
    status: "waiting-for-ready",
    stepResults: {},
  })),
  formatBootstrapStepResult: vi.fn(() => ""),
  formatRuntimeReadinessResult: vi.fn(() => ""),
  getBootstrapLogs: vi.fn(async () => ({ lines: [] })),
  hasDismissedWelcomeScreen: vi.fn(() => false),
  mapRuntimePreflightFailureToState: vi.fn(() => ({
    status: "failed",
    stepResults: {},
  })),
  mapRuntimeReadinessFailureToState: vi.fn(() => ({
    status: "failed",
    stepResults: {},
  })),
  openDockerDesktopNative: vi.fn(async () => ({ ok: false })),
  openDockerDesktopDownloadPage: vi.fn(async () => ({ ok: true })),
  restartRuntimeServices: vi.fn(async () => ({ ok: true })),
  runComposeUp: vi.fn(async () => ({ ok: true })),
  runRuntimeBootstrapPreflight: vi.fn(async () => ({ ok: true })),
  runSetupCli: vi.fn(async () => ({ ok: true })),
  setWelcomeScreenDismissed: vi.fn(),
  shouldRunRuntimeBootstrap: vi.fn(() => false),
  waitForRuntimeReady: vi.fn(async () => ({ ok: true })),
}));

vi.mock("@/pages/EventsConsole", () => ({
  default: () => <div data-testid="events-console-mock" />,
}));

vi.mock("@/pages/SharePage", () => ({
  SharePage: () => <div data-testid="share-page-mock" />,
}));

import DocumentsView from "@/components/documents/DocumentsView";
import {
  forwardLegacyDocumentOpenToWorkspace,
  requestWorkspaceOpen,
  useWorkspaceState,
} from "@/features/workspace/state/useWorkspaceState";

function WorkspaceProbe() {
  const { activeDoc, workspaceOpen } = useWorkspaceState();
  return (
    <div
      data-testid="workspace-probe"
      data-open={workspaceOpen ? "true" : "false"}
    >
      {activeDoc?.title ?? ""}
    </div>
  );
}

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  window.dispatchEvent(new Event("resize"));
}

beforeEach(() => {
  setViewportWidth(1280);
});

describe("workspace invocation contract", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.resetModules();
    vi.doUnmock("@/features/workspace/state/useWorkspaceState");
  });

  it("opens a document from Documents through the shared workspace contract", async () => {
    const user = userEvent.setup();

    render(
      <>
        <WorkspaceProbe />
        <DocumentsView
          documents={[
            {
              id: "doc-1",
              title: "Field Notes",
              name: "Field Notes",
              ext: "md",
              type: "file",
              src_url: "/media/documents/field-notes.md",
            },
          ]}
          extColors={{} as never}
        />
      </>
    );

    await user.click(screen.getByRole("button", { name: "Field Notes" }));

    await waitFor(() => {
      expect(screen.getByTestId("workspace-probe")).toHaveAttribute(
        "data-open",
        "true"
      );
      expect(screen.getByTestId("workspace-probe")).toHaveTextContent(
        "Field Notes"
      );
    });
  });

  it("opens a document from the Guardian Chat bridge through the same contract", async () => {
    render(<WorkspaceProbe />);

    let didOpen = false;
    await act(async () => {
      didOpen = forwardLegacyDocumentOpenToWorkspace(
        {
          doc: {
            id: "guardian-1",
            title: "Thread Attachment",
            name: "Thread Attachment",
            ext: "pdf",
            type: "file",
            src_url: "/media/documents/thread-attachment.pdf",
          },
        },
        {
          source: "guardian-chat",
          targetView: "guardian",
        }
      );
    });

    expect(didOpen).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-probe")).toHaveAttribute(
        "data-open",
        "true"
      );
      expect(screen.getByTestId("workspace-probe")).toHaveTextContent(
        "Thread Attachment"
      );
    });
  });

  it("treats an unsupported dashboard target as the shared documents workspace", async () => {
    render(<WorkspaceProbe />);

    let didOpen = false;
    await act(async () => {
      didOpen = requestWorkspaceOpen({
        doc: {
          id: "dashboard-rail",
          title: "Dashboard Notes",
          name: "Dashboard Notes",
          ext: "md",
          type: "file",
          src_url: "/media/documents/dashboard-notes.md",
        },
        source: "documents",
        targetView: "dashboard" as any,
      });
    });

    expect(didOpen).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-probe")).toHaveAttribute(
        "data-open",
        "true"
      );
      expect(screen.getByTestId("workspace-probe")).toHaveTextContent(
        "Dashboard Notes"
      );
    });
  });

  it("keeps Workspace collapsed by default on phone widths after a document open request", async () => {
    setViewportWidth(390);
    render(<WorkspaceProbe />);

    let didOpen = false;
    await act(async () => {
      didOpen = forwardLegacyDocumentOpenToWorkspace(
        {
          doc: {
            id: "phone-1",
            title: "Phone Notes",
            name: "Phone Notes",
            ext: "md",
            type: "file",
            src_url: "/media/documents/phone-notes.md",
          },
        },
        {
          source: "documents",
          targetView: "documents",
        }
      );
    });

    expect(didOpen).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-probe")).toHaveAttribute(
        "data-open",
        "false"
      );
      expect(screen.getByTestId("workspace-probe")).toHaveTextContent(
        "Phone Notes"
      );
    });
  });

  it("blocks nested shell rendering when the app re-enters inside a workspace preview", async () => {
    vi.doMock("@/features/workspace/state/useWorkspaceState", async () => {
      const actual =
        await vi.importActual<typeof import("@/features/workspace/state/useWorkspaceState")>(
          "@/features/workspace/state/useWorkspaceState"
        );
      return {
        ...actual,
        shouldBlockNestedWorkspaceShell: vi.fn(() => true),
      };
    });

    const { default: App } = await import("@/App");

    render(<App />);

    expect(screen.getByTestId("workspace-recursion-guard")).toBeInTheDocument();
    expect(screen.queryByTestId("app-shell-mock")).not.toBeInTheDocument();
  });
});
