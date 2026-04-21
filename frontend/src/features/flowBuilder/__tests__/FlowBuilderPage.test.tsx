import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import FlowBuilderPage from "../FlowBuilderPage";

describe("FlowBuilderPage layout", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, "", "/flow-builder");
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the three-zone layout and keeps the spec-first copy truthful", async () => {
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
      "data-flow-builder-mode",
      "process"
    );
    expect(screen.getByTestId("flow-builder-parameter-rail")).toBeVisible();
    expect(screen.getByTestId("flow-builder-graph-canvas")).toBeVisible();
    expect(screen.getByTestId("flow-builder-chat-dock")).toBeVisible();
    expect(
      screen.getByText(/authoring, inspection, validation, and draft shaping/i)
    ).toBeVisible();
    expect(screen.getByText(/before anything becomes runnable/i)).toBeVisible();
    expect(screen.getByTestId("flow-builder-route")).toHaveTextContent("/flow-builder?mode=process");
  });

  it("renders the expected staged parameter list and updates selection", async () => {
    const user = userEvent.setup();

    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    const parameterRail = screen.getByTestId("flow-builder-parameter-rail");
    const stages = [
      "select-source",
      "define-constraints",
      "set-outcomes",
      "add-steps",
      "insert-conditions",
      "validation-gates",
      "review-validate",
    ];

    stages.forEach((stage) => {
      expect(within(parameterRail).getByTestId(`flow-builder-stage-${stage}`)).toBeVisible();
    });

    expect(within(parameterRail).getByTestId("flow-builder-stage-select-source")).toHaveAttribute(
      "aria-pressed",
      "true"
    );

    await user.click(within(parameterRail).getByTestId("flow-builder-stage-define-constraints"));

    await waitFor(() => {
      expect(
        within(parameterRail).getByTestId("flow-builder-stage-define-constraints")
      ).toHaveAttribute("aria-pressed", "true");
    });
    expect(within(parameterRail).getByTestId("flow-builder-stage-select-source")).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByTestId("flow-builder-graph-canvas")).toHaveTextContent(
      /Seeded from Define Constraints/i
    );
  });

  it("dismisses and reopens the assistant dock without disturbing the builder layout", async () => {
    const user = userEvent.setup();

    render(<FlowBuilderPage />);

    const dock = screen.getByTestId("flow-builder-chat-dock");
    expect(dock).toBeVisible();
    expect(within(dock).getByText(/Embedded Guardian review space/i)).toBeVisible();

    await user.click(screen.getByTestId("flow-builder-assistant-toggle"));

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-chat-dock")).toHaveTextContent(
        /Assistant dock hidden/i
      );
    });

    await user.click(screen.getByTestId("flow-builder-assistant-toggle"));

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-chat-dock")).toHaveTextContent(
        /Embedded Guardian review space/i
      );
    });
  });

  it("keeps the expertise lane honest and editable without implying execution support", async () => {
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
    expect(
      within(draftArtifact).getByText(/without claiming compile or execution support/i)
    ).toBeVisible();

    const objective = screen.getByTestId("flow-builder-draft-objective");
    await user.clear(objective);
    await user.type(objective, "Capture the first-pass workflow outcome.");

    expect(objective).toHaveValue("Capture the first-pass workflow outcome.");
  });

  it("canonicalizes the route and keeps the selected mode in sync with history", async () => {
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    await act(async () => {
      window.history.pushState({}, "", "/flow-builder?mode=expertise");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
        "data-flow-builder-mode",
        "expertise"
      );
    });
    expect(window.location.search).toBe("?mode=expertise");
  });
});
