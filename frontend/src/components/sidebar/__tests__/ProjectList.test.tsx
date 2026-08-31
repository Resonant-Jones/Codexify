import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import ProjectList from "../ProjectList";
import type { Project } from "@/types/common";

function createProject(overrides: Partial<Project> & Record<string, unknown> = {}): Project {
  return {
    id: "proj-1",
    name: "ChatGPT - Quarterly Planning",
    icon: "📁",
    ...overrides,
  } as Project;
}

describe("ProjectList imported project presentation", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("cleans imported titles and keeps native project selection intact", () => {
    const onPick = vi.fn();

    render(
      <ProjectList
        projects={[
          createProject({ metadata: { import_source: "chatgpt" } }),
          { id: "proj-2", name: "Engineering", icon: "🧭" },
        ]}
        search=""
        currentId={null}
        onPick={onPick}
      />
    );

    expect(screen.getByText("Quarterly Planning")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.queryByText("ChatGPT - Quarterly Planning")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Quarterly Planning"));

    expect(onPick).toHaveBeenCalledWith("proj-1");
  });

  it("gives the first, middle, and last tiles independently reachable action menus", async () => {
    const onPick = vi.fn();
    const onRenameProject = vi.fn();
    const onArchiveProject = vi.fn();
    const onRestoreProject = vi.fn();
    const onDeleteProject = vi.fn();
    vi.spyOn(window, "prompt").mockReturnValue("My renamed home");
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <ProjectList
        projects={[
          { id: "active", name: "Active", systemRole: null, archivedAt: null },
          { id: "general", name: "My Home", systemRole: "general", archivedAt: null },
          { id: "archived", name: "Archived", systemRole: null, archivedAt: "2026-08-30T12:00:00Z" },
        ]}
        search=""
        currentId={null}
        onPick={onPick}
        onRenameProject={onRenameProject}
        onArchiveProject={onArchiveProject}
        onRestoreProject={onRestoreProject}
        onDeleteProject={onDeleteProject}
      />
    );

    const triggers = screen.getAllByRole("button", { name: /Project actions for/i });
    expect(triggers).toHaveLength(3);

    fireEvent.click(triggers[0]);
    expect(onPick).not.toHaveBeenCalled();
    let menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: /Rename/i })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: /^Archive$/i })).toBeInTheDocument();
    expect(within(menu).queryByRole("menuitem", { name: /Delete/i })).not.toBeInTheDocument();
    fireEvent.click(within(menu).getByRole("menuitem", { name: /^Archive$/i }));
    await waitFor(() => expect(onArchiveProject).toHaveBeenCalledWith("active"));

    fireEvent.click(triggers[1]);
    menu = screen.getByRole("menu");
    expect(within(menu).getAllByRole("menuitem")).toHaveLength(1);
    fireEvent.click(within(menu).getByRole("menuitem", { name: /Rename/i }));
    await waitFor(() => {
      expect(onRenameProject).toHaveBeenCalledWith("general", "My renamed home");
    });

    fireEvent.click(triggers[2]);
    menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: /Restore/i })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: /Delete permanently/i })).toBeInTheDocument();
    fireEvent.click(within(menu).getByRole("menuitem", { name: /Delete permanently/i }));
    expect(window.confirm).toHaveBeenCalledWith(
      expect.stringMatching(/threads will be moved to General.*backups are not guaranteed/i)
    );
    await waitFor(() => expect(onDeleteProject).toHaveBeenCalledWith("archived"));
  });

  it("keeps renamed Imports structural identity and exposes rename only", () => {
    render(
      <ProjectList
        projects={[
          { id: "imports", name: "Conversation Vault", systemRole: "imports", archivedAt: null },
        ]}
        search=""
        currentId={null}
        onPick={vi.fn()}
        onRenameProject={vi.fn()}
        onArchiveProject={vi.fn()}
        onRestoreProject={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Project actions for Conversation Vault" }));
    const menu = screen.getByRole("menu");
    expect(within(menu).getAllByRole("menuitem")).toHaveLength(1);
    expect(within(menu).getByRole("menuitem", { name: /Rename/i })).toBeInTheDocument();
  });
});
