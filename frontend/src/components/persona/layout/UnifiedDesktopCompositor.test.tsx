import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import UnifiedDesktopCompositor from "./UnifiedDesktopCompositor";

afterEach(cleanup);

describe("UnifiedDesktopCompositor", () => {
  it("keeps Codexify mounted across open, resize, and close", () => {
    const { container } = render(
      <UnifiedDesktopCompositor enabled shellStyle={{}}>
        <div data-testid="selected-codexify-view">Guardian</div>
      </UnifiedDesktopCompositor>
    );
    const root = screen.getByTestId("unified-desktop");
    Object.defineProperty(root, "clientWidth", { configurable: true, value: 1200 });
    fireEvent(window, new Event("resize"));
    vi.spyOn(root, "getBoundingClientRect").mockReturnValue({
      left: 0,
      width: 1200,
    } as DOMRect);
    const originalView = screen.getByTestId("selected-codexify-view");

    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    expect(screen.getByTestId("unified-desktop-browser")).toBeInTheDocument();
    expect(screen.getByTestId("selected-codexify-view")).toBe(originalView);

    const divider = screen.getByRole("separator", { name: "Resize Codexify and browser" });
    const captured = new Set<number>();
    divider.setPointerCapture = (id) => captured.add(id);
    divider.hasPointerCapture = (id) => captured.has(id);
    fireEvent.pointerDown(divider, { pointerId: 1, clientX: 600 });
    fireEvent.pointerMove(divider, { pointerId: 1, clientX: 440 });
    expect(divider).toHaveAttribute("aria-valuenow", "37");
    fireEvent.pointerMove(divider, { pointerId: 1, clientX: 1100 });
    expect(divider).toHaveAttribute("aria-valuenow", "73");

    fireEvent.click(screen.getByRole("button", { name: "Close browser preview" }));
    expect(screen.queryByTestId("unified-desktop-browser")).not.toBeInTheDocument();
    expect(screen.queryByTestId("unified-desktop-divider")).not.toBeInTheDocument();
    expect(screen.getByTestId("selected-codexify-view")).toBe(originalView);
    expect(container.querySelector(".unified-desktop__codexify")).toHaveStyle({ flexGrow: "1" });
  });
});
