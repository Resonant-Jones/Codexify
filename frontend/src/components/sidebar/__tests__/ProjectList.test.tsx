import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import ProjectList from "../ProjectList";

describe("ProjectList presentation", () => {
  it("renders clean project labels while preserving provenance badges", () => {
    render(
      <ProjectList
        projects={[
          { id: "1", name: "ChatGPT: Recovery Sprint", icon: "🗂️" },
          { id: "2", name: "Imports", icon: "📁" },
        ]}
        search=""
        currentId={null}
        onPick={vi.fn()}
      />
    );

    const recoveryButton = screen.getByRole("button", { name: /Recovery Sprint/ });
    const generalButton = screen.getByRole("button", { name: /General/ });

    expect(screen.getByText("Recovery Sprint")).toBeInTheDocument();
    expect(screen.queryByText("ChatGPT: Recovery Sprint")).not.toBeInTheDocument();
    expect(within(recoveryButton).getByText("ChatGPT")).toBeVisible();
    expect(within(generalButton).getByText("Imported")).toBeVisible();
  });
});
