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
  post: vi.fn(),
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
    post: apiState.post,
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
    apiState.post.mockReset();
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

  it("renders the no-project Project Knowledge Base state and keeps it distinct from System Docs", () => {
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

    expect(
      screen.getByRole("heading", { name: /Project Knowledge Base/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Uploaded docs, notes, specs, and working references inform project work\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Select or create a project to build its Knowledge Base\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Project Knowledge Base informs project work; System Docs govern the assistant from Settings > Data\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/^Constitutional overlay$/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Upload Project Knowledge Base documents/i })
    ).not.toBeInTheDocument();
    expect(apiState.get).not.toHaveBeenCalledWith(
      "/media/documents",
      expect.objectContaining({ params: expect.objectContaining({ project_id: expect.anything() }) })
    );
  });

  it("renders the selected-project Project Knowledge Base panel with upload affordance and project documents", async () => {
    authState.allowGate = true;
    apiState.get.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
      if (url === "/chat/threads") return { data: [] };
      if (url === "/media/documents" && config?.params?.project_id === "42") {
        return {
          data: {
            documents: [
              {
                id: "doc-kb-1",
                filename: "Launch Spec.md",
                embedding_status: "ready",
              },
            ],
          },
        };
      }
      if (url === "/media/documents") {
        return { data: { documents: [] } };
      }
      return { data: {} };
    });

    render(
      <DashboardView
        extColors={EXT_COLORS}
        gallery={[]}
        activeProjectId="42"
        activeProjectName="Launch Project"
        onImagePrompt={vi.fn()}
        onRequestNewProject={vi.fn()}
        onRequestNewThread={vi.fn()}
        onNavigateDocuments={vi.fn()}
        onNavigateGallery={vi.fn()}
        threadGridRows={2}
      />
    );

    expect(await screen.findByText("Launch Spec.md")).toBeInTheDocument();
    expect(screen.getByText("Active project: Launch Project")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Upload Project Knowledge Base documents/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Project Knowledge Base informs project work\. System Docs govern the assistant from Settings > Data; they are separate from this project-local document lane\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /This surface uses existing project document storage\. It does not change global behavior or retrieval policy\./i
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/constitutional/i)).not.toBeInTheDocument();
  });

  it("uploads Project Knowledge Base documents through the existing project document API and refreshes the list", async () => {
    authState.allowGate = true;
    let projectDocs = [
      {
        id: "doc-before",
        filename: "Before Upload.md",
        embedding_status: "ready",
      },
    ];
    apiState.get.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
      if (url === "/chat/threads") return { data: [] };
      if (url === "/media/documents" && config?.params?.project_id === "7") {
        return { data: { documents: projectDocs } };
      }
      if (url === "/media/documents") return { data: { documents: [] } };
      return { data: {} };
    });
    apiState.post.mockImplementation(async () => {
      projectDocs = [
        {
          id: "doc-after",
          filename: "After Upload.md",
          embedding_status: "queued",
        },
      ];
      return { data: { id: "doc-after", filename: "After Upload.md" } };
    });

    render(
      <DashboardView
        extColors={EXT_COLORS}
        gallery={[]}
        activeProjectId={7}
        activeProjectName="Ops Project"
        onImagePrompt={vi.fn()}
        onRequestNewProject={vi.fn()}
        onRequestNewThread={vi.fn()}
        onNavigateDocuments={vi.fn()}
        onNavigateGallery={vi.fn()}
        threadGridRows={2}
      />
    );

    expect(await screen.findByText("Before Upload.md")).toBeInTheDocument();

    const input = screen.getByLabelText("Project Knowledge Base document files");
    const file = new File(["# Notes"], "After Upload.md", { type: "text/markdown" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(apiState.post).toHaveBeenCalledWith(
        "/api/media/upload/document",
        expect.any(FormData),
        expect.objectContaining({
          headers: { "Content-Type": "multipart/form-data" },
        })
      );
    });
    const form = apiState.post.mock.calls[0]?.[1] as FormData;
    expect(form.get("project_id")).toBe("7");
    expect(form.get("tag")).toBe("uploaded");
    expect(await screen.findByText("After Upload.md")).toBeInTheDocument();
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
