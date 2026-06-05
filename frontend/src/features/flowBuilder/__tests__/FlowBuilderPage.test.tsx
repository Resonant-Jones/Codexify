import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import FlowBuilderPage from "../FlowBuilderPage";
import { getFlowDraftStageNodeId } from "../model/flowDraft";

describe("FlowBuilderPage layout", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, "", "/flow-builder");
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the graph-first layout and describes automation-spec authoring", async () => {
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    const page = screen.getByTestId("flow-builder-page");
    expect(page).toHaveAttribute("data-flow-builder-mode", "process");
    expect(screen.getByTestId("flow-builder-parameter-rail")).toBeVisible();
    expect(screen.getByTestId("flow-builder-graph-canvas")).toBeVisible();
    expect(screen.getByTestId("flow-builder-chat-dock")).toBeVisible();
    expect(page).toHaveTextContent(/Build draft automation specifications/i);
    expect(page).toHaveTextContent(/known process/i);
    expect(page).toHaveTextContent(/Assistant-guided elicitation/i);
    expect(page).toHaveTextContent(/before anything becomes runnable/i);
    expect(screen.getByTestId("flow-builder-route")).toHaveTextContent("/flow-builder?mode=process");
  });

  it("keeps Flow Builder vertically scrollable inside the viewport shell", async () => {
    window.history.pushState({}, "", "/flow-builder?mode=expertise");
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
        "data-flow-builder-mode",
        "expertise"
      );
    });

    const page = screen.getByTestId("flow-builder-page");
    const surface = screen.getByTestId("flow-builder-surface");
    const panelGrid = screen.getByTestId("flow-builder-panel-grid");

    expect(page).toHaveClass("overflow-y-auto");
    expect(page).toHaveClass("overflow-x-hidden");
    expect(surface).not.toHaveClass("overflow-hidden");
    expect(surface).not.toHaveClass("flex-1");
    expect(panelGrid).not.toHaveClass("flex-1");
  });

  it("shows the manual process and Assistant-guided draft paths without adding execution claims", async () => {
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    expect(screen.getByTestId("flow-builder-mode-process")).toHaveTextContent(/Manual process/i);
    expect(screen.getByTestId("flow-builder-mode-process")).toHaveTextContent(
      /explicit steps you already know/i
    );
    expect(screen.getByTestId("flow-builder-mode-expertise")).toHaveTextContent(
      /Assistant-guided/i
    );
    expect(screen.getByTestId("flow-builder-mode-expertise")).toHaveTextContent(
      /outcome, constraints, or rough intent/i
    );

    const parameterRail = screen.getByTestId("flow-builder-parameter-rail");
    expect(parameterRail).toHaveTextContent(/Manual\/process starts from known steps/i);
    expect(parameterRail).toHaveTextContent(/Assistant-guided starts from an outcome/i);

    const graphCanvas = screen.getByTestId("flow-builder-graph-canvas");
    expect(graphCanvas).toHaveTextContent(/Manual process draft seed/i);
    expect(graphCanvas).toHaveTextContent(/drafting surface, not an execution surface/i);
    expect(graphCanvas).toHaveTextContent(/Automation spec draft/i);
    expect(graphCanvas).toHaveTextContent(/Draft only/i);
  });

  it("keeps the parameter rail, graph, and support dock aligned on the same shared selection", async () => {
    const user = userEvent.setup();

    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    const parameterRail = screen.getByTestId("flow-builder-parameter-rail");
    const graphCanvas = screen.getByTestId("flow-builder-graph-canvas");
    const chatDock = screen.getByTestId("flow-builder-chat-dock");

    await user.click(within(parameterRail).getByTestId("flow-builder-stage-define-constraints"));

    await waitFor(() => {
      expect(within(parameterRail).getByTestId("flow-builder-stage-define-constraints")).toHaveAttribute(
        "aria-pressed",
        "true"
      );
    });

    expect(graphCanvas).toHaveTextContent(/seeded from Define Constraints/i);
    expect(within(chatDock).getByTestId("flow-builder-support-context")).toHaveTextContent(
      /Stage: Define Constraints/i
    );
    expect(within(chatDock).getByTestId("flow-builder-support-context")).toHaveTextContent(
      /Validation: 1 warning/i
    );

    await user.click(
      within(graphCanvas).getByTestId(
        `flow-builder-graph-node-${getFlowDraftStageNodeId("set-outcomes")}`
      )
    );

    await waitFor(() => {
      expect(
        within(parameterRail).getByTestId("flow-builder-stage-set-outcomes")
      ).toHaveAttribute("aria-pressed", "true");
    });

    expect(within(chatDock).getByTestId("flow-builder-support-context")).toHaveTextContent(
      /Node: Set Outcomes/i
    );
  });

  it("updates the canonical draft order when a graph node is reordered", async () => {
    const user = userEvent.setup();

    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    const graphCanvas = screen.getByTestId("flow-builder-graph-canvas");
    const orderStrip = within(graphCanvas).getByTestId("flow-builder-draft-order");

    expect(orderStrip).toHaveTextContent(
      /1\. Select Source.*2\. Define Constraints.*3\. Set Outcomes/s
    );

    await user.click(
      within(graphCanvas).getByTestId(
        `flow-builder-graph-node-${getFlowDraftStageNodeId("set-outcomes")}`
      )
    );
    await waitFor(() => {
      expect(
        within(graphCanvas).getByTestId(
          `flow-builder-node-move-down-${getFlowDraftStageNodeId("set-outcomes")}`
        )
      ).toBeVisible();
    });
    await user.click(
      within(graphCanvas).getByTestId(
        `flow-builder-node-move-down-${getFlowDraftStageNodeId("set-outcomes")}`
      )
    );

    await waitFor(() => {
      expect(orderStrip).toHaveTextContent(
        /1\. Select Source.*2\. Define Constraints.*3\. Add Steps.*4\. Set Outcomes/s
      );
    });
  });

  it("dismisses and reopens the support dock without losing the shared draft state", async () => {
    const user = userEvent.setup();

    window.history.pushState({}, "", "/flow-builder?mode=expertise");
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
        "data-flow-builder-mode",
        "expertise"
      );
    });

    const dock = screen.getByTestId("flow-builder-chat-dock");
    expect(dock).toBeVisible();
    expect(within(dock).getByTestId("flow-builder-support-context")).toHaveTextContent(
      /Draft specification/i
    );

    const objective = screen.getByTestId("flow-builder-draft-objective");
    await user.clear(objective);
    await user.type(objective, "Capture the canonical draft across dock toggles.");

    await user.click(screen.getByTestId("flow-builder-assistant-toggle"));

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-chat-dock")).toHaveTextContent(/Assistant dock hidden/i);
    });

    await user.click(screen.getByTestId("flow-builder-assistant-toggle"));

    await waitFor(() => {
      expect(screen.getByTestId("flow-builder-chat-dock")).toHaveTextContent(
        /Local review support/i
      );
    });

    expect(screen.getByTestId("flow-builder-draft-objective")).toHaveValue(
      "Capture the canonical draft across dock toggles."
    );
    const draftSpec = screen.getByTestId("flow-builder-draft-spec");
    expect(within(draftSpec).getByText(/non-runtime/i)).toBeVisible();
    expect(within(draftSpec).getByText(/draft only/i)).toBeVisible();
    expect(
      within(draftSpec).getByText(/without backend chat transport, compile, scheduling, or execution support/i)
    ).toBeVisible();
  });

  it("keeps the assistant dock sidecar-only with no backend chat or execution boundary", async () => {
    render(<FlowBuilderPage />);

    await waitFor(() => {
      expect(window.location.search).toBe("?mode=process");
    });

    const dock = screen.getByTestId("flow-builder-chat-dock");
    expect(dock).toHaveTextContent(/Assistant-guided draft support/i);
    expect(dock).toHaveTextContent(/automation-spec drafting/i);
    expect(dock).toHaveTextContent(/Sidecar notes only/i);
    expect(dock).toHaveTextContent(/No backend chat integration is wired here/i);
    expect(dock).toHaveTextContent(/No automation execution is triggered here/i);
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
