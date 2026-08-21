import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import SidebarRoot from "../SidebarRoot";
import type { Thread } from "@/types/ui";

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

const useSidebarThreadsOptionsSpy = vi.fn();
const mockSidebarState = vi.hoisted(() => ({
  currentProjectId: null as string | null,
  projectList: [] as Array<{ id: string; name: string; icon?: string; description?: string }>,
}));

vi.mock("../useSidebarThreads", () => ({
  default: (options: any) => {
    useSidebarThreadsOptionsSpy(options);
    return {
    threads: [createThread("thread-1")],
    displayThreads: [createThread("thread-1")],
    scopeLabel: "General",
    currentProjectId: mockSidebarState.currentProjectId,
    setScope: vi.fn(),
    originSystem: options.originSystem ?? null,
    setOriginSystem: options.onOriginSystemChange,
    originOptions: [
      { value: "codexify", label: "Codexify", description: "Codexify" },
      { value: "openai", label: "ChatGPT", description: "ChatGPT" },
      { value: "anthropic", label: "Claude", description: "Claude" },
    ],
    renameThread: vi.fn().mockResolvedValue(undefined),
    toggleArchiveThread: vi.fn().mockResolvedValue(undefined),
    deleteThread: vi.fn().mockResolvedValue(undefined),
    looseCount: 0,
    };
  },
}));

vi.mock("../useProjectsCache", () => ({
  default: () => ({
    projectList: mockSidebarState.projectList,
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

describe("SidebarRoot canonical origin filter wiring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("cfy.sidebarTab", "threads");
    mockSidebarState.currentProjectId = null;
    mockSidebarState.projectList = [];
  });

  it("forwards the controlled canonical origin between the toolbar and parent loader seam", () => {
    const onOriginSystemChange = vi.fn();
    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
        originSystem="anthropic"
        onOriginSystemChange={onOriginSystemChange}
      />
    );

    expect(useSidebarThreadsOptionsSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        originSystem: "anthropic",
        onOriginSystemChange,
      })
    );

    const toolbar = screen.getByRole("toolbar", { name: "Canonical conversation origin filter" });
    expect(toolbar).toBeInTheDocument();
    expect(within(toolbar).getByRole("button", { name: "All" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByRole("button", { name: "Claude" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: "Codexify" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ChatGPT" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "ChatGPT" }));
    expect(onOriginSystemChange).toHaveBeenCalledWith("openai");
  });

  it("keeps the canonical origin filter out of the Projects tab", () => {
    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
        onOriginSystemChange={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Claude" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));

    expect(screen.getByTestId("project-list")).toBeInTheDocument();
    expect(screen.queryByRole("toolbar", { name: "Canonical conversation origin filter" })).not.toBeInTheDocument();
  });

  it("keeps the legacy Guardian tab key by default and isolates Documents tabs", () => {
    const guardian = render(
      <SidebarRoot threads={[]} activeId={null} onSelect={vi.fn()} onNewChat={vi.fn()} />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));
    expect(window.localStorage.getItem("cfy.sidebarTab")).toBe("projects");
    guardian.unmount();

    window.localStorage.setItem("cfy.sidebarTab", "threads");
    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
        persistence={{ tabStorageKey: "cfy.documents.sidebarTab", projectStorageKey: null }}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));
    expect(window.localStorage.getItem("cfy.documents.sidebarTab")).toBe("projects");
    expect(window.localStorage.getItem("cfy.sidebarTab")).toBe("threads");
    expect(useSidebarThreadsOptionsSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        persistence: { tabStorageKey: "cfy.documents.sidebarTab", projectStorageKey: null },
      })
    );
  });

  it("shows a dismissible Project Knowledge Base notice once", () => {
    mockSidebarState.currentProjectId = "project-42";
    mockSidebarState.projectList = [{ id: "project-42", name: "Launch Project" }];

    const firstRender = render(
      <SidebarRoot threads={[]} activeId={null} onSelect={vi.fn()} onNewChat={vi.fn()} />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));

    expect(
      screen.getByTestId("project-knowledge-base-entry")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Project Documents and the Project Knowledge Base live in the Projects rail on the left\./i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/System Docs stay in Settings > Data/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Dismiss Project Knowledge Base notice" })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Dismiss Project Knowledge Base notice" }));

    expect(screen.queryByTestId("project-knowledge-base-entry")).not.toBeInTheDocument();
    expect(window.localStorage.getItem("cfy.sidebar.projectKnowledgeBaseNoticeDismissed")).toBe(
      "true"
    );

    firstRender.unmount();

    render(<SidebarRoot threads={[]} activeId={null} onSelect={vi.fn()} onNewChat={vi.fn()} />);

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));

    expect(screen.queryByTestId("project-knowledge-base-entry")).not.toBeInTheDocument();
  });
});
