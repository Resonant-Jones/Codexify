import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import FlowBuilderPage from "../FlowBuilderPage";

describe("FlowBuilderPage mode routing", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, "", "/flow-builder");
  });

  afterEach(() => {
    cleanup();
  });

  it("canonicalizes the route and keeps the selected mode in sync with history", async () => {
    const user = userEvent.setup();

    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });
    expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
      "data-flow-builder-mode",
      "process"
    );
    expect(
      screen.getByText(/The job here is to make the plan explicit/i)
    ).toBeInTheDocument();

    await user.click(screen.getByTestId("flow-builder-mode-expertise"));

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=expertise");
    });
    expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
      "data-flow-builder-mode",
      "expertise"
    );

    await act(async () => {
      window.history.pushState({}, "", "/flow-builder?mode=process");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
        "data-flow-builder-mode",
        "process"
      );
    });
    expect(window.location.search).toBe("?mode=process");
  });

  it("does not force the browser back to Flow Builder after leaving the route", async () => {
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    await act(async () => {
      window.history.pushState({}, "", "/dashboard");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(window.location.pathname).toBe("/dashboard");
    });
    expect(window.location.search).toBe("");
  });

  it("renders an inspectable non-runtime draft artifact in expertise mode", async () => {
    const user = userEvent.setup();

    window.history.pushState({}, "", "/flow-builder?mode=expertise");
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
        "data-flow-builder-mode",
        "expertise"
      );
    });

    const draftArtifact = screen.getByTestId("flow-builder-draft-spec");
    expect(draftArtifact).toBeVisible();
    expect(within(draftArtifact).getByText(/^draft specification artifact$/i)).toBeVisible();
    expect(within(draftArtifact).getByText(/^non-runtime$/i)).toBeVisible();
    expect(within(draftArtifact).getByText(/^draft only$/i)).toBeVisible();
    expect(within(draftArtifact).getByText(/build from expertise/i)).toBeVisible();
    expect(
      within(draftArtifact).getByText(/without claiming compile or execution support/i)
    ).toBeVisible();

    const objective = screen.getByTestId("flow-builder-draft-objective");
    await user.clear(objective);
    await user.type(objective, "Capture the first-pass workflow outcome.");

    expect(objective).toHaveValue("Capture the first-pass workflow outcome.");
  });
});
