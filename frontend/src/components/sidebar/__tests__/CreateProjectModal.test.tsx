import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, beforeEach, describe, expect, it } from "vitest";
import CreateProjectModal from "../CreateProjectModal";
import SidebarRoot from "../SidebarRoot";
import api from "@/lib/api";

const mockRefreshProjects = vi.fn();
const mockSetProjectList = vi.fn();
const mockSetScope = vi.fn();
const mockSidebarState = vi.hoisted(() => ({
  currentProjectId: null as string | null,
}));
const mockProjectsState = vi.hoisted(() => ({
  list: [] as Array<{ id: string; name: string; icon?: string }>,
}));

vi.mock("../useSidebarThreads", () => ({
  default: () => ({
    threads: [],
    displayThreads: [],
    scopeLabel: "Loose",
    currentProjectId: mockSidebarState.currentProjectId,
    setScope: mockSetScope,
    renameThread: vi.fn(),
    toggleArchiveThread: vi.fn(),
    deleteThread: vi.fn(),
    looseCount: 0,
  }),
}));

vi.mock("../useProjectsCache", () => ({
  default: () => ({
    projectList: mockProjectsState.list,
    setProjectList: mockSetProjectList,
    refreshProjectsFromServer: mockRefreshProjects,
    looseCount: 0,
  }),
}));

vi.mock("../ThreadList", () => ({
  default: () => <div data-testid="thread-list" />,
}));

vi.mock("../ProjectList", () => ({
  default: ({
    projects = [],
    onOpenNewProject,
    onDeleteProject,
  }: {
    projects?: Array<{ id: string; name: string }>;
    onOpenNewProject?: () => void;
    onDeleteProject?: (id: string) => Promise<void> | void;
  }) => (
    <div>
      <button type="button" onClick={onOpenNewProject}>
        New Project
      </button>
      {projects.map((project) => (
        <button
          key={`delete-${project.id}`}
          type="button"
          onClick={() => onDeleteProject?.(String(project.id))}
        >
          Delete {project.name}
        </button>
      ))}
    </div>
  ),
}));

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApi = api as {
  post: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

describe("CreateProjectModal", () => {
  beforeEach(() => {
    mockRefreshProjects.mockReset();
    mockSetProjectList.mockReset();
    mockSetScope.mockReset();
    mockApi.post.mockReset();
    mockApi.get.mockReset();
    mockApi.delete.mockReset();
    mockSidebarState.currentProjectId = null;
    mockProjectsState.list = [];
    window.localStorage.setItem("cfy.sidebarTab", "projects");
  });

  it("renders a visible modal surface", () => {
    render(
      <CreateProjectModal
        open
        onClose={() => undefined}
        onCreateProject={vi.fn()}
      />
    );

    const dialog = screen.getByRole("dialog");
    const heading = screen.getByRole("heading", { name: /create project/i });
    const form = heading.closest("form");

    expect(dialog).toBeInTheDocument();
    expect(form).not.toBeNull();
    expect(form?.style.background).not.toBe("");
    expect(form?.style.background).not.toBe("transparent");
  });

  it("submits a project and closes on success", async () => {
    mockApi.post.mockResolvedValue({ data: { id: 123 } });

    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Delta" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create project/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith("/api/projects", {
        name: "Delta",
        icon: "📁",
        description: "",
      });
    });

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(mockRefreshProjects).toHaveBeenCalled();
  });

  it("falls back to the legacy mounted projects route when /api/projects returns 404", async () => {
    mockApi.post
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValueOnce({ data: { id: 456 } });

    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Fallback" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create project/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenNthCalledWith(1, "/api/projects", {
        name: "Fallback",
        icon: "📁",
        description: "",
      });
      expect(mockApi.post).toHaveBeenNthCalledWith(2, "/projects", {
        name: "Fallback",
        icon: "📁",
        description: "",
      });
    });

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(mockRefreshProjects).toHaveBeenCalled();
  });

  it("shows an error message when create fails", async () => {
    mockApi.post.mockRejectedValue({
      response: { data: { message: "Nope" } },
    });

    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Failing" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create project/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Nope");
  });

  it("deletes a project on success and removes it from local list state", async () => {
    mockApi.delete.mockResolvedValue({ data: { ok: true } });
    mockProjectsState.list = [
      { id: "10", name: "Alpha" },
      { id: "20", name: "Beta" },
    ];

    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /delete alpha/i }));

    await waitFor(() => {
      expect(mockApi.delete).toHaveBeenCalledWith("/api/projects/10");
    });

    expect(mockSetProjectList).toHaveBeenCalled();
    const updater = mockSetProjectList.mock.calls[0][0] as (value: Array<{ id: string; name: string }>) => Array<{ id: string; name: string }>;
    expect(updater(mockProjectsState.list).map((project) => project.id)).toEqual(["20"]);
  });

  it("falls back to a remaining project when deleting the selected project", async () => {
    mockApi.delete.mockResolvedValue({ data: { ok: true } });
    mockSidebarState.currentProjectId = "10";
    mockProjectsState.list = [
      { id: "10", name: "Alpha" },
      { id: "20", name: "Beta" },
    ];

    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /delete alpha/i }));

    await waitFor(() => {
      expect(mockApi.delete).toHaveBeenCalledWith("/api/projects/10");
    });
    expect(mockSetScope).toHaveBeenCalledWith("20");
  });

  it("keeps project state intact when delete fails", async () => {
    mockApi.delete.mockRejectedValue({ response: { status: 500 } });
    mockSidebarState.currentProjectId = "10";
    mockProjectsState.list = [
      { id: "10", name: "Alpha" },
      { id: "20", name: "Beta" },
    ];

    render(
      <SidebarRoot
        threads={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /delete alpha/i }));

    await waitFor(() => {
      expect(mockApi.delete).toHaveBeenCalledWith("/api/projects/10");
    });
    expect(mockSetProjectList).not.toHaveBeenCalled();
    expect(mockSetScope).not.toHaveBeenCalled();
  });
});
