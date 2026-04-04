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

const mockSetProvenanceFilter = vi.fn();
const mockSidebarState = vi.hoisted(() => ({
  currentProjectId: null as string | null,
  provenanceFilter: null as string | null,
}));

vi.mock("../useSidebarThreads", () => ({
  default: () => ({
    threads: [createThread("thread-1")],
    displayThreads: [createThread("thread-1")],
    scopeLabel: "General",
    currentProjectId: mockSidebarState.currentProjectId,
    setScope: vi.fn(),
    provenanceFilter: mockSidebarState.provenanceFilter,
    setProvenanceFilter: mockSetProvenanceFilter,
    provenanceOptions: [
      { value: "chatgpt", label: "ChatGPT" },
      { value: "openai", label: "OpenAI" },
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

describe("SidebarRoot provenance filter wiring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("cfy.sidebarTab", "threads");
    mockSidebarState.currentProjectId = null;
    mockSidebarState.provenanceFilter = "chatgpt";
  });

  it("renders the canonical source dock and forwards stable keys", () => {
    render(<SidebarRoot threads={[]} activeId={null} onSelect={vi.fn()} onNewChat={vi.fn()} />);

    const toolbar = screen.getByRole("toolbar", { name: "Imported source filter" });
    expect(toolbar).toBeInTheDocument();
    expect(within(toolbar).getByRole("button", { name: "All" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByRole("button", { name: "ChatGPT" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: "OpenAI" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "OpenAI" }));
    expect(mockSetProvenanceFilter).toHaveBeenCalledWith("openai");
  });

  it("keeps the provenance filter out of the Projects tab", () => {
    render(<SidebarRoot threads={[]} activeId={null} onSelect={vi.fn()} onNewChat={vi.fn()} />);

    expect(screen.getByRole("button", { name: "ChatGPT" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Projects" }));

    expect(screen.getByTestId("project-list")).toBeInTheDocument();
    expect(screen.queryByRole("toolbar", { name: "Imported source filter" })).not.toBeInTheDocument();
  });
});
