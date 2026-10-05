import { act, render, screen, waitFor } from "@testing-library/react";
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

const authTestState = vi.hoisted(() => ({
  auth: { ready: true, status: "authenticated" as const, token: "account-a-session" },
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => authTestState.auth,
  getAuthState: () => authTestState.auth,
  checkAuthGate: (auth: typeof authTestState.auth) =>
    auth.ready && auth.status === "authenticated",
}));

function ProjectsHarness() {
  const { projectList, accountId, loadedForCurrentAuth } = useProjectsCache();

  return (
    <div>
      <div data-testid="project-count">{projectList.length}</div>
      <div data-testid="project-names">{projectList.map((project) => project.name).join("|")}</div>
      <div data-testid="project-meta">{JSON.stringify(projectList[0] ?? null)}</div>
      <div data-testid="account-id">{accountId ?? "none"}</div>
      <div data-testid="projects-loaded">{String(loadedForCurrentAuth)}</div>
    </div>
  );
}

describe("useProjectsCache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    authTestState.auth = { ready: true, status: "authenticated", token: "account-a-session" };
    (api.get as any).mockResolvedValue({
      data: {
        projects: [{ id: 1, name: "General", icon: "📁", user_id: "account-a" }],
      },
    });
  });

  it("fetches projects once on mount and ignores focus churn", async () => {
    render(<ProjectsHarness />);

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
    expect(api.get).toHaveBeenCalledWith("/api/projects");
    expect(await screen.findByTestId("project-count")).toHaveTextContent("1");
    expect(screen.getByTestId("account-id")).toHaveTextContent("account-a");

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
            user_id: "account-a",
            metadata: { import_source: "chatgpt" },
          },
          { id: 2, name: "General", icon: "📁", user_id: "account-a" },
          { id: 3, name: "Loose Threads", icon: "📁", user_id: "account-a" },
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
            user_id: "account-a",
            metadata: { import_source: "chatgpt" },
          },
          { id: 2, name: "General", icon: "📁", user_id: "account-a" },
          { id: 3, name: "Loose Threads", icon: "📁", user_id: "account-a" },
          { id: 4, name: "Engineering", icon: "🧭", user_id: "account-a" },
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

  it("normalizes lifecycle fields and keeps renamed built-ins structurally identifiable", async () => {
    (api.get as any).mockResolvedValueOnce({
      data: [
        {
          id: 1,
          name: "Home",
          system_role: "general",
          archived_at: null,
          user_id: "account-a",
        },
        {
          id: 2,
          name: "Old work",
          system_role: null,
          archived_at: "2026-08-30T12:00:00Z",
          user_id: "account-a",
        },
      ],
    });

    render(<ProjectsHarness />);

    await waitFor(() => expect(screen.getByTestId("project-count")).toHaveTextContent("2"));
    expect(screen.getByTestId("project-meta")).toHaveTextContent('"systemRole":"general"');
    expect(screen.getByTestId("project-meta")).toHaveTextContent('"archivedAt":null');
    expect(screen.getByTestId("project-names")).toHaveTextContent("Home|Old work");
    await waitFor(() => expect(window.localStorage.getItem("cfy.generalProjectId")).toBe("1"));
  });

  it("hides Account A projects on session change and rejects its late response", async () => {
    let resolveAccountA!: (value: unknown) => void;
    let resolveAccountB!: (value: unknown) => void;
    (api.get as any)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveAccountA = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveAccountB = resolve; }));
    window.localStorage.setItem("cfy.projectsCache", JSON.stringify([
      { id: 7, name: "Private A Project", user_id: "account-a" },
    ]));

    const { rerender } = render(<ProjectsHarness />);
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("project-count")).toHaveTextContent("0");
    expect(screen.getByTestId("project-names")).not.toHaveTextContent("Private A Project");

    authTestState.auth = { ready: true, status: "authenticated", token: "account-b-session" };
    rerender(<ProjectsHarness />);
    expect(screen.getByTestId("project-count")).toHaveTextContent("0");
    expect(screen.getByTestId("account-id")).toHaveTextContent("none");
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));

    await act(async () => resolveAccountB({ data: [{ id: 9, name: "B General", user_id: "account-b" }] }));
    expect(await screen.findByTestId("project-names")).toHaveTextContent("B General");
    expect(screen.getByTestId("account-id")).toHaveTextContent("account-b");

    await act(async () => resolveAccountA({ data: [{ id: 7, name: "Private A Project", user_id: "account-a" }] }));
    expect(screen.getByTestId("project-names")).toHaveTextContent("B General");
    expect(screen.getByTestId("project-names")).not.toHaveTextContent("Private A Project");
    expect(window.localStorage.getItem("cfy.projectsCache")).toBeNull();
  });

  it("does not derive an account scope from inconsistent project owners", async () => {
    (api.get as any).mockResolvedValueOnce({
      data: [
        { id: 1, name: "A project", user_id: "account-a" },
        { id: 2, name: "B project", user_id: "account-b" },
      ],
    });

    render(<ProjectsHarness />);

    expect(await screen.findByTestId("project-count")).toHaveTextContent("2");
    expect(screen.getByTestId("account-id")).toHaveTextContent("none");
  });
});
