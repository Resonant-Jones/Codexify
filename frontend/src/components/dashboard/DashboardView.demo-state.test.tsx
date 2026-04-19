import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ButtonHTMLAttributes, ReactNode } from "react";

const runtimeState = vi.hoisted(() => ({
  invokeTauriCommandMock: vi.fn(),
  tauriRuntime: false,
}));

const authState = vi.hoisted(() => ({
  value: { token: null },
  allowGate: false,
}));

const apiState = vi.hoisted(() => ({
  get: vi.fn(),
}));

const workspaceState = vi.hoisted(() => ({
  requestWorkspaceOpenMock: vi.fn(() => true),
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
  getRuntimeConfigSync: () => ({
    mode: runtimeState.tauriRuntime ? "tauri" : "web",
    backendBaseUrl: "http://backend.test",
    apiBaseUrl: "http://backend.test/api",
    sseUrl: "http://backend.test/api/events",
    sharePublicBaseUrl: "http://share.test",
    authMode: "local",
  }),
  isTauriRuntime: () => runtimeState.tauriRuntime,
  invokeTauriCommand: runtimeState.invokeTauriCommandMock,
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: apiState.get,
  },
}));

vi.mock("@/features/workspace/state/useWorkspaceState", () => ({
  requestWorkspaceOpen: workspaceState.requestWorkspaceOpenMock,
}));

vi.mock("@/lib/authState", () => ({
  checkAuthGate: vi.fn(() => authState.allowGate),
  useAuthState: vi.fn(() => authState.value),
}));

vi.mock("@/components/modals/ImageGenModal", () => ({
  ImageGenModal: () => null,
}));

vi.mock("@/components/modals/ImagePreviewModal", () => ({
  default: () => null,
}));

vi.mock("@/components/documents/DocumentTile", () => ({
  default: ({ file }: { file: { name: string } }) => <div>{file.name}</div>,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@/features/dashboard/components/DashboardGallery", () => ({
  default: ({ items }: { items: Array<{ src: string; prompt?: string }> }) => (
    <div data-testid="dashboard-gallery-mock">
      {items.map((item) => (
        <span key={item.src}>{item.prompt}</span>
      ))}
    </div>
  ),
}));

import DashboardView from "@/components/dashboard/DashboardView";

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  act(() => {
    window.dispatchEvent(new Event("resize"));
  });
}

const EXT_COLORS = {
  pdf: "#000",
  doc: "#000",
  md: "#000",
  png: "#000",
  sketch: "#000",
  txt: "#000",
  docx: "#000",
  jpeg: "#000",
  codex: "#000",
} as const;

describe("DashboardView demo content", () => {
  beforeEach(() => {
    act(() => {
      setViewportWidth(1280);
    });
    authState.allowGate = false;
    authState.value = { token: null };
    apiState.get.mockReset();
    workspaceState.requestWorkspaceOpenMock.mockReset();
  });

  afterEach(() => {
    act(() => {
      setViewportWidth(1280);
    });
    runtimeState.tauriRuntime = false;
    runtimeState.invokeTauriCommandMock.mockReset();
    cleanup();
    vi.clearAllMocks();
  });

  it("renders demo content when there is no real user data and leaves no manual toggle behind", () => {
    render(
      <DashboardView
        extColors={EXT_COLORS}
        gallery={[]}
        onImagePrompt={vi.fn()}
        onRequestNewProject={vi.fn()}
        onRequestNewThread={vi.fn()}
        onNavigateDocuments={vi.fn()}
        onNavigateGallery={vi.fn()}
        threadGridRows={2}
      />
    );

    expect(screen.getByText("Codexify Design Tokens.pdf")).toBeInTheDocument();
    expect(screen.getByText("Demo: Warm Gradient")).toBeInTheDocument();
    expect(screen.queryByText("Hide Mock Items")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Dismiss demo documents")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Dismiss demo gallery")).not.toBeInTheDocument();
  });

  it("auto-hides dashboard demo content once real user data exists", async () => {
    authState.allowGate = true;
    apiState.get.mockImplementation(async (url: string) => {
      if (url === "/chat/threads") {
        return { data: [] };
      }
      if (url === "/media/documents") {
        return {
          data: {
            documents: [
              {
                id: "doc-1",
                filename: "User Plan.md",
                ext: "md",
              },
            ],
          },
        };
      }
      return { data: {} };
    });

    render(
      <DashboardView
        extColors={EXT_COLORS}
        gallery={[
          {
            src: "/media/images/real-dashboard.png",
            prompt: "Real dashboard image",
          },
          {
            src: "/media/images/mock-dashboard.png",
            prompt: "Mock dashboard image",
            mock: true,
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

    expect(await screen.findByText("User Plan.md")).toBeInTheDocument();
    expect(screen.getByText("Real dashboard image")).toBeInTheDocument();
    expect(screen.queryByText("Codexify Design Tokens.pdf")).not.toBeInTheDocument();
    expect(screen.queryByText("Demo: Warm Gradient")).not.toBeInTheDocument();
    expect(screen.queryByText("Mock dashboard image")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Dismiss demo documents")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Dismiss demo gallery")).not.toBeInTheDocument();
  });

  it("switches Dashboard into a mobile stack and opens recent documents explicitly", async () => {
    setViewportWidth(390);
    authState.allowGate = true;
    apiState.get.mockImplementation(async (url: string) => {
      if (url === "/chat/threads") {
        return { data: [] };
      }
      if (url === "/media/documents") {
        return {
          data: {
            documents: [
              {
                id: "doc-1",
                filename: "User Plan.md",
                ext: "md",
              },
            ],
          },
        };
      }
      return { data: {} };
    });

    const { container } = render(
      <DashboardView
        extColors={EXT_COLORS}
        gallery={[
          {
            src: "/media/images/real-dashboard.png",
            prompt: "Real dashboard image",
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

    await waitFor(() => {
      expect(container.querySelector('[data-layout-mode="mobile-stack"]')).toBeTruthy();
      expect(screen.getByTestId("dashboard-layout")).toHaveAttribute(
        "data-dashboard-layout",
        "mobile_stack"
      );
    });

    const openRecentDocumentButton = await screen.findByRole("button", {
      name: "Open User Plan.md in Workspace",
    });
    fireEvent.click(openRecentDocumentButton);

    expect(workspaceState.requestWorkspaceOpenMock).toHaveBeenCalledWith(
      expect.objectContaining({
        doc: expect.objectContaining({
          id: "doc-1",
          name: "User Plan.md",
          ext: "md",
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
