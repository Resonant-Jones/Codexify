import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, beforeEach, describe, expect, it } from "vitest";
import CreateProjectModal from "../CreateProjectModal";
import SidebarRoot from "../SidebarRoot";
import api from "@/lib/api";

const mockRefreshProjects = vi.fn();
const mockSetProjectList = vi.fn();
const mockSetScope = vi.fn();

vi.mock("../useSidebarThreads", () => ({
  default: () => ({
    threads: [],
    displayThreads: [],
    scopeLabel: "Loose",
    currentProjectId: null,
    setScope: mockSetScope,
    renameThread: vi.fn(),
    toggleArchiveThread: vi.fn(),
    deleteThread: vi.fn(),
    looseCount: 0,
  }),
}));

vi.mock("../useProjectsCache", () => ({
  default: () => ({
    projectList: [],
    setProjectList: mockSetProjectList,
    refreshProjectsFromServer: mockRefreshProjects,
    looseCount: 0,
  }),
}));

vi.mock("../ThreadList", () => ({
  default: () => <div data-testid="thread-list" />,
}));

vi.mock("../ProjectList", () => ({
  default: ({ onOpenNewProject }: { onOpenNewProject?: () => void }) => (
    <button type="button" onClick={onOpenNewProject}>
      New Project
    </button>
  ),
}));

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const mockApi = api as { post: ReturnType<typeof vi.fn>; get: ReturnType<typeof vi.fn> };

describe("CreateProjectModal", () => {
  beforeEach(() => {
    mockRefreshProjects.mockReset();
    mockSetProjectList.mockReset();
    mockSetScope.mockReset();
    mockApi.post.mockReset();
    mockApi.get.mockReset();
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
      expect(mockApi.post).toHaveBeenCalledWith("/projects", {
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
});
