import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import api from "@/lib/api";
import SidebarRoot from "../SidebarRoot";

const mockSetScope = vi.fn();
const mockSidebarState = vi.hoisted(() => ({
  currentProjectId: "stale-project" as string | null,
import { fireEvent, render, screen } from "@testing-library/react";

import SidebarRoot from "../SidebarRoot";
import type { Thread } from "@/types/ui";

const mockSetScope = vi.fn();
const mockSetProvenanceFilter = vi.fn();
const mockUseSidebarThreads = vi.hoisted(() => ({
  currentProjectId: null as string | null,
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
    threads: [createThread("thread-1")],
    displayThreads: [createThread("thread-1")],
    scopeLabel: "General",
    currentProjectId: mockUseSidebarThreads.currentProjectId,
    setScope: mockSetScope,
    provenanceFilter: "ChatGPT",
    setProvenanceFilter: mockSetProvenanceFilter,
    provenanceOptions: [
      { value: "ChatGPT", label: "ChatGPT" },
      { value: "OpenAI", label: "OpenAI" },
    ],
    renameThread: vi.fn().mockResolvedValue(undefined),
    toggleArchiveThread: vi.fn().mockResolvedValue(undefined),
    deleteThread: vi.fn().mockResolvedValue(undefined),
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
vi.mock("../useProjectsCache", () => ({
  default: () => ({
    projectList: [],
    setProjectList: vi.fn(),
    refreshProjectsFromServer: vi.fn(),
    looseCount: 0,
  }),
}));

vi.mock("../ProjectList", () => ({
  default: () => <div data-testid="project-list" />,
}));

vi.mock("../CreateProjectModal", () => ({
  default: () => null,
}));

function createThread(id: string): Thread {
  return {
    id,
    title: `Thread ${id}`,
    lastMessage: "Sidebar filter test thread",
    unread: 0,
    participants: [],
    messages: [],
  };
}

describe("SidebarRoot provenance filter wiring", () => {
  beforeEach(() => {
    mockSetScope.mockReset();
    mockSetProvenanceFilter.mockReset();
    mockUseSidebarThreads.currentProjectId = null;
    window.localStorage.clear();
    window.localStorage.setItem("cfy.sidebarTab", "threads");
  });

  it("renders the provenance filter in the threads view and forwards selection changes", () => {
    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByRole("button", { name: "ChatGPT" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: "OpenAI" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "OpenAI" }));
    expect(mockSetProvenanceFilter).toHaveBeenCalledWith("OpenAI");
  });

  it("keeps the provenance filter out of the Projects tab", () => {
    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "ChatGPT" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));

    expect(screen.getByTestId("project-list")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ChatGPT" })).not.toBeInTheDocument();
  });
});
