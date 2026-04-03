import { beforeEach, describe, expect, it, vi } from "vitest";
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
