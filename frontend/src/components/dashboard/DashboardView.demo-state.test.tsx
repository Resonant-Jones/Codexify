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

describe("DashboardView beta contract", () => {
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

  it("keeps the gallery empty state honest when no saved images exist", () => {
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
    expect(screen.getByText("No gallery images yet. Generate or upload to get started.")).toBeInTheDocument();
    expect(screen.queryByText("Demo: Warm Gradient")).not.toBeInTheDocument();
    expect(screen.queryByText("Hide Mock Items")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Dismiss demo documents")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Dismiss demo gallery")).not.toBeInTheDocument();
  });

  it("keeps recent threads capped and renders saved gallery images without demo fallbacks", async () => {
    authState.allowGate = true;
    apiState.get.mockImplementation(async (url: string) => {
      if (url === "/chat/threads") {
        return {
          data: Array.from({ length: 8 }, (_, index) => ({
            id: `thread-${index + 1}`,
            title: `Thread ${index + 1}`,
            lastMessage: `Message ${index + 1}`,
          })),
        };
      }
      if (url === "/media/documents") {
        return {
          data: { documents: [] },
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

    expect(await screen.findByRole("button", { name: "Open thread Thread 1" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Open thread / })).toHaveLength(6);
    expect(screen.getByTestId("dashboard-recent-threads-grid")).toHaveStyle({
      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    });
    const actionRow = screen.getByRole("button", { name: "Create new thread" }).parentElement;
    expect(actionRow).toHaveClass("flex-nowrap");
    expect(actionRow).not.toHaveClass("flex-wrap");
    expect(screen.getByText("Codexify Design Tokens.pdf")).toBeInTheDocument();
    expect(screen.getByText("Real dashboard image")).toBeInTheDocument();
    expect(screen.queryByText("Mock dashboard image")).not.toBeInTheDocument();
    expect(screen.queryByText("Demo: Warm Gradient")).not.toBeInTheDocument();
    expect(screen.queryByText("No gallery images yet. Generate or upload to get started.")).not.toBeInTheDocument();
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
