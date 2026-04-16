import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import FlowBuilderPage from "@/pages/FlowBuilderPage";

describe("FlowBuilderPage", () => {
  it("renders a non-runtime entry surface with explicit pre-execution copy", () => {
    render(<FlowBuilderPage />);

    expect(screen.getByTestId("flow-builder-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /flow builder/i })).toBeVisible();
    expect(screen.getByText(/pre-execution specification work only/i)).toBeVisible();
    expect(screen.getByText(/no compile or execute path is wired in this seam/i)).toBeVisible();
    expect(screen.getByRole("button", { name: /build from expertise/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: /build from process/i })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  it("lets the user switch between expertise and process entry lanes", async () => {
    const user = userEvent.setup();
    render(<FlowBuilderPage />);

    await user.click(screen.getByRole("button", { name: /build from process/i }));

    expect(screen.getByRole("button", { name: /build from process/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByTestId("flow-builder-selection-summary")).toHaveTextContent(
      /build from process/i
    );
    expect(
      within(screen.getByTestId("flow-builder-selection-summary")).getByText(
        /no runtime compile or execution support yet/i
      )
    ).toBeVisible();
  });
});
