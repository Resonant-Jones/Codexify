import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import api from "@/lib/api";
import SidebarRoot from "../SidebarRoot";

const mockSetScope = vi.fn();
const mockSidebarState = vi.hoisted(() => ({
  currentProjectId: "stale-project" as string | null,
}));

vi.mock("../useSidebarThreads", () => ({
  default: () => ({
    displayThreads: [],
    scopeLabel: "Project",
    currentProjectId: mockSidebarState.currentProjectId,
    setScope: mockSetScope,
    renameThread: vi.fn(),
    toggleArchiveThread: vi.fn(),
    deleteThread: vi.fn(),
    looseCount: 0,
  }),
}));

vi.mock("../ThreadList", () => ({
  default: () => <div data-testid="thread-list" />,
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

describe("SidebarRoot project presentation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("cfy.sidebarTab", "projects");
    mockSidebarState.currentProjectId = "stale-project";
    mockApi.get.mockResolvedValue({
      data: {
        projects: [
          { id: "general-1", name: "General", icon: "📁" },
          { id: "general-2", name: "Loose Threads", icon: "📁" },
          {
            id: "proj-1",
            name: "ChatGPT - Quarterly Planning",
            icon: "📁",
            metadata: { import_source: "chatgpt" },
          },
          { id: "proj-2", name: "Engineering", icon: "🧭" },
        ],
      },
    });
  });

  it("renders imported projects natively with one General bucket", async () => {
    render(<SidebarRoot threads={[]} activeId={null} onSelect={vi.fn()} onNewChat={vi.fn()} />);

    expect(await screen.findByText("Quarterly Planning")).toBeInTheDocument();
    expect(screen.queryByText("ChatGPT - Quarterly Planning")).not.toBeInTheDocument();
    expect(screen.getAllByText("General")).toHaveLength(1);
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.queryByText("Imports")).not.toBeInTheDocument();

    await waitFor(() => expect(mockSetScope).toHaveBeenCalledWith("general-1"));
  });
});
