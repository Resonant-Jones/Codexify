import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ThreadList from "../ThreadList";
import type { ProjectPresentation } from "../sidebarPresentation";
import type { Thread } from "@/types/ui";

function createThread(overrides: Partial<Thread> = {}): Thread {
  return {
    id: "thread-1",
    title: "Research notes",
    lastMessage: "Valid content should read as content.",
    unread: 0,
    participants: [],
    messages: [],
    ...overrides,
  };
}

function renderThreadList(
  overrides: Partial<Thread> = {},
  activeId: string | null = null,
  options: {
    browseMode?: "grouped" | "flat";
    projectPresentationsById?: Map<string, ProjectPresentation>;
    scopeLabel?: string;
    scopeBadge?: string | null;
  } = {}
) {
  return render(
    <ThreadList
      threads={[createThread(overrides)]}
      activeId={activeId}
      scopeLabel={options.scopeLabel ?? "General"}
      scopeBadge={options.scopeBadge ?? null}
      browseMode={options.browseMode}
      projectPresentationsById={options.projectPresentationsById}
      onSelect={vi.fn()}
      onNewChat={vi.fn()}
      onRename={vi.fn().mockResolvedValue(undefined)}
      onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
      onDelete={vi.fn().mockResolvedValue(undefined)}
    />
  );
}

describe("ThreadList dark mode surface contract", () => {
  afterEach(() => {
    document.documentElement.classList.remove("dark");
  });

  it("keeps the light-mode thread tile on the default panel background", () => {
    renderThreadList();

    expect(screen.getByTestId("thread-tile-thread-1")).toHaveStyle({
      background: "var(--panel-bg)",
    });
  });

  it("uses the darker sheet surface and white text in dark mode", () => {
    document.documentElement.classList.add("dark");

    renderThreadList();

    const tile = screen.getByTestId("thread-tile-thread-1");
    expect(tile).toHaveStyle({ background: "var(--panel-sheet)" });
    expect(tile).toHaveClass("dark:text-white");
  });

  it("keeps the active dark-mode tile anchored to the darker sheet token", () => {
    document.documentElement.classList.add("dark");

    renderThreadList({}, "thread-1");

    expect(screen.getByTestId("thread-tile-thread-1")).toHaveStyle({
      background: "color-mix(in oklab, var(--accent) 16%, var(--panel-sheet) 84%)",
    });
  });

  it("labels the active project context as project instead of scope", () => {
    renderThreadList({ title: "Project thread" });

    expect(screen.getByText("Project:")).toBeInTheDocument();
    expect(screen.getByText("General")).toBeInTheDocument();
    expect(screen.queryByText("Scope:")).not.toBeInTheDocument();
  });

  it("cleans visible thread titles and keeps project context visible in flat mode", () => {
    renderThreadList(
      {
        title: "ChatGPT: Draft brief",
        metadata: { import_source: "chatgpt" },
        projectId: "proj-1",
      },
      null,
      {
        browseMode: "flat",
        scopeLabel: "All threads",
        projectPresentationsById: new Map<string, ProjectPresentation>([
          [
            "proj-1",
            {
              label: "Recovery Sprint",
              badge: null,
              rawName: "ChatGPT: Recovery Sprint",
              isFallback: false,
            },
          ],
        ]),
      }
    );

    expect(screen.getByText("Draft brief")).toBeInTheDocument();
    expect(screen.getByText("ChatGPT")).toBeInTheDocument();
    expect(screen.getByTestId("thread-project-thread-1")).toHaveTextContent(
      "Recovery Sprint"
    );
    expect(screen.queryByText("ChatGPT: Draft brief")).not.toBeInTheDocument();
  });
});
