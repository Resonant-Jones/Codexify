import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

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
});
