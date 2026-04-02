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

  return <div data-testid="project-count">{projectList.length}</div>;
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

  it("treats Imports as the canonical general project when it is the only fallback bucket", async () => {
    (api.get as any).mockResolvedValueOnce({
      data: {
        projects: [{ id: 1, name: "Imports", icon: "📁" }],
      },
    });

    render(<ProjectsHarness />);

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(window.localStorage.getItem("cfy.generalProjectId")).toBe("1")
    );
    expect(window.localStorage.getItem("cfy.defaultProjectId")).toBe("1");
  });
});
