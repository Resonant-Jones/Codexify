import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
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
});
