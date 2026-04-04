import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import useProjectsCache from "../useProjectsCache";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock("@/lib/logging/logOnce", () => ({
  logOnce: vi.fn(),
}));

function ProjectsHarness() {
  const { projectList } = useProjectsCache();

  return (
    <div>
      <div data-testid="project-count">{projectList.length}</div>
      <div data-testid="project-names">{projectList.map((project) => project.name).join("|")}</div>
      <div data-testid="project-meta">{JSON.stringify(projectList[0] ?? null)}</div>
    </div>
  );
}

describe("useProjectsCache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    (api.get as any).mockResolvedValue({
      data: {
        projects: [{ id: 1, name: "General", icon: "📁" }],
      },
    });
  });

  it("fetches projects once on mount and ignores focus churn", async () => {
    render(<ProjectsHarness />);

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
    expect(api.get).toHaveBeenCalledWith("/api/projects");
    expect(await screen.findByTestId("project-count")).toHaveTextContent("1");

    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
  });

  it("cleans imported project labels and collapses duplicate General aliases", async () => {
    (api.get as any).mockResolvedValueOnce({
      data: {
        projects: [
          {
            id: 1,
            name: "ChatGPT - Quarterly Planning",
            icon: "📁",
            metadata: { import_source: "chatgpt" },
          },
          { id: 2, name: "General", icon: "📁" },
          { id: 3, name: "Loose Threads", icon: "📁" },
        ],
      },
    });

    render(<ProjectsHarness />);

    expect(await screen.findByTestId("project-count")).toHaveTextContent("2");
    expect(screen.getByTestId("project-names")).toHaveTextContent("Quarterly Planning|General");
    expect(screen.getByTestId("project-names")).not.toHaveTextContent("ChatGPT - Quarterly Planning");
    expect(screen.getByTestId("project-meta")).toHaveTextContent('"import_source":"chatgpt"');
  });

  it("keeps the canonical General project when an imported alias also cleans to General", async () => {
    (api.get as any).mockResolvedValueOnce({
      data: {
        projects: [
          {
            id: 1,
            name: "ChatGPT - General",
            icon: "📁",
            metadata: { import_source: "chatgpt" },
          },
          { id: 2, name: "General", icon: "📁" },
          { id: 3, name: "Loose Threads", icon: "📁" },
          { id: 4, name: "Engineering", icon: "🧭" },
        ],
      },
    });

    render(<ProjectsHarness />);

    await waitFor(() => expect(screen.getByTestId("project-count")).toHaveTextContent("2"));
    expect(screen.getByTestId("project-names")).toHaveTextContent("General|Engineering");
    expect(screen.getByTestId("project-names")).not.toHaveTextContent("ChatGPT - General");
    expect(screen.getByTestId("project-names")).not.toHaveTextContent("Loose Threads");
    await waitFor(() => expect(window.localStorage.getItem("cfy.generalProjectId")).toBe("2"));
    expect(window.localStorage.getItem("cfy.defaultProjectId")).toBe("2");
  });
});
