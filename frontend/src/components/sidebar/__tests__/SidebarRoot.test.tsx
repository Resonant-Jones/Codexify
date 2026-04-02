import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import SidebarRoot from "../SidebarRoot";
import type { Thread } from "@/types/ui";

const mockSetScope = vi.fn();
const mockSidebarState = vi.hoisted(() => ({
  currentProjectId: "imports-1" as string | null,
}));
const mockProjectsState = vi.hoisted(() => ({
  list: [
    { id: "imports-1", name: "Imports", icon: "📁" },
    { id: "proj-1", name: "ChatGPT: Recovery Sprint", icon: "🗂️" },
  ],
}));

function createThread(id: string, overrides: Partial<Thread> = {}): Thread {
  return {
    id,
    title: `Thread ${id}`,
    lastMessage: "",
    unread: 0,
    participants: [],
    messages: [],
    ...overrides,
  };
}

vi.mock("../useSidebarThreads", () => ({
  default: () => ({
    threads: [
      createThread("thread-1", {
        title: "ChatGPT: Draft agenda",
        lastMessage: "Imported thread",
        projectId: "imports-1",
        metadata: { import_source: "chatgpt" },
      }),
      createThread("thread-2", {
        title: "ChatGPT: Loose note",
        lastMessage: "Loose fallback",
        projectId: null,
        metadata: { import_source: "chatgpt" },
      }),
      createThread("thread-3", {
        title: "Project sync",
        lastMessage: "Project thread",
        projectId: "proj-1",
      }),
    ],
    displayThreads: [
      createThread("thread-1", {
        title: "ChatGPT: Draft agenda",
        lastMessage: "Imported thread",
        projectId: "imports-1",
        metadata: { import_source: "chatgpt" },
      }),
      createThread("thread-2", {
        title: "ChatGPT: Loose note",
        lastMessage: "Loose fallback",
        projectId: null,
        metadata: { import_source: "chatgpt" },
      }),
    ],
    scopeLabel: "General",
    currentProjectId: mockSidebarState.currentProjectId,
    setScope: mockSetScope,
    renameThread: vi.fn(),
    toggleArchiveThread: vi.fn(),
    deleteThread: vi.fn(),
    looseCount: 1,
  }),
}));

vi.mock("../useProjectsCache", () => ({
  default: () => ({
    projectList: mockProjectsState.list,
    setProjectList: vi.fn(),
    refreshProjectsFromServer: vi.fn(),
    looseCount: 1,
  }),
}));

vi.mock("@/contexts/LegacyThreadsContext", () => ({
  useLegacyThreads: () => ({
    enabled: false,
    open: vi.fn(),
  }),
}));

describe("SidebarRoot rail modes", () => {
  beforeEach(() => {
    mockSetScope.mockReset();
    window.localStorage.clear();
  });

  it("shows grouped projects, clean titles, and flat thread chips for recovered data", () => {
    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    const groupedTab = screen.getByRole("tab", { name: "Grouped" });
    const flatTab = screen.getByRole("tab", { name: "Flat" });

    expect(groupedTab).toHaveAttribute("data-state", "active");
    expect(screen.getByText("Projects")).toBeVisible();
    expect(screen.getByText("Threads")).toBeVisible();

    const recoveryProject = screen.getByText("Recovery Sprint", {
      selector: ".project-tile__label",
    }).closest("button");
    const generalProject = screen.getByText("General", {
      selector: ".project-tile__label",
    }).closest("button");
    if (!recoveryProject || !generalProject) {
      throw new Error("Expected project tiles to be present");
    }
    expect(within(recoveryProject).getByText("ChatGPT")).toBeVisible();
    expect(within(generalProject).getByText("Imported")).toBeVisible();
    expect(screen.getByText("Recovery Sprint")).toBeVisible();
    expect(screen.queryByText("ChatGPT: Recovery Sprint")).not.toBeInTheDocument();

    expect(screen.getByText("Draft agenda")).toBeVisible();
    expect(screen.getByTestId("thread-badge-thread-1")).toHaveTextContent("ChatGPT");

    fireEvent.click(flatTab);

    expect(flatTab).toHaveAttribute("data-state", "active");
    expect(screen.queryByText("Projects")).not.toBeInTheDocument();
    expect(screen.getByText("Flat:")).toBeVisible();
    expect(screen.getByTestId("thread-project-thread-3")).toHaveTextContent(
      "Recovery Sprint"
    );
    expect(screen.getByTestId("thread-project-thread-1")).toHaveTextContent("General");
    expect(screen.getByTestId("thread-project-badge-thread-1")).toHaveTextContent(
      "Imported"
    );
  });
});
