import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import UnifiedDesktopCompositor, { type BrowserPresentation } from "./UnifiedDesktopCompositor";

afterEach(cleanup);

function Harness() {
  const [presentation, setPresentation] = React.useState<BrowserPresentation>("closed");
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [sidebarPinned, setSidebarPinned] = React.useState(false);
  const changePresentation = (next: BrowserPresentation) => {
    setPresentation(next);
    setSidebarOpen(next === "focused");
    setSidebarPinned(next === "focused");
  };
  return (
    <UnifiedDesktopCompositor
      enabled
      shellStyle={{}}
      presentation={presentation}
      onPresentationChange={changePresentation}
      focusedSidebarOpen={sidebarOpen}
      focusedSidebarPinned={sidebarPinned}
      onFocusedSidebarReveal={() => setSidebarOpen(true)}
    >
      <div data-testid="selected-codexify-view">Guardian</div>
      <button type="button" onClick={() => { setSidebarOpen(false); setSidebarPinned(false); }}>Dismiss shelf</button>
    </UnifiedDesktopCompositor>
  );
}

function setDesktopGeometry() {
  const root = screen.getByTestId("unified-desktop");
  Object.defineProperty(root, "clientWidth", { configurable: true, value: 1600 });
  fireEvent(window, new Event("resize"));
  vi.spyOn(root, "getBoundingClientRect").mockReturnValue({ left: 0, width: 1600 } as DOMRect);
  return root;
}

function dragDivider(fromX: number, toX: number) {
  const divider = screen.getByRole("separator", { name: "Resize Codexify and browser" });
  const captured = new Set<number>();
  divider.setPointerCapture = (id) => captured.add(id);
  divider.hasPointerCapture = (id) => captured.has(id);
  fireEvent.pointerDown(divider, { pointerId: 1, clientX: fromX });
  fireEvent.pointerMove(divider, { pointerId: 1, clientX: toX });
}

describe("UnifiedDesktopCompositor", () => {
  it("keeps Codexify and Browser mounted through docked, focused, and restored states", () => {
    render(<Harness />);
    const root = setDesktopGeometry();
    const originalView = screen.getByTestId("selected-codexify-view");
    expect(root).toHaveAttribute("data-browser-state", "closed");
    expect(screen.queryByText("Browser", { exact: true })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    expect(root).toHaveAttribute("data-browser-state", "docked");
    const browser = screen.getByTestId("unified-desktop-browser");
    dragDivider(800, 1060);
    expect(screen.getByRole("separator")).toHaveAttribute("aria-valuenow", "67");

    fireEvent.click(screen.getByRole("button", { name: "Focus browser" }));
    expect(root).toHaveAttribute("data-browser-state", "focused");
    expect(screen.getByTestId("unified-desktop-codexify")).toHaveAttribute("inert");
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
    expect(screen.getByTestId("unified-desktop-browser")).toBe(browser);
    expect(root).toHaveAttribute("data-focused-sidebar-pinned", "true");

    fireEvent.click(screen.getByRole("button", { name: "Restore docked browser" }));
    expect(root).toHaveAttribute("data-browser-state", "docked");
    expect(screen.getByTestId("unified-desktop-codexify")).not.toHaveAttribute("inert");
    expect(screen.getByRole("separator")).toHaveAttribute("aria-valuenow", "67");
    expect(screen.getByTestId("unified-desktop-browser")).toBe(browser);
    expect(screen.getByTestId("selected-codexify-view")).toBe(originalView);

    fireEvent.click(screen.getByRole("button", { name: "Close browser preview" }));
    expect(root).toHaveAttribute("data-browser-state", "closed");
    expect(screen.queryByTestId("unified-desktop-browser")).not.toBeInTheDocument();
    expect(screen.getByTestId("selected-codexify-view")).toBe(originalView);
    expect(screen.getByTestId("unified-desktop-codexify")).toHaveStyle({ flexGrow: "1" });
  });

  it("focuses Browser when the desktop narrows below usable docked geometry", () => {
    render(<Harness />);
    const root = setDesktopGeometry();
    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    expect(root).toHaveAttribute("data-browser-state", "docked");

    Object.defineProperty(root, "clientWidth", { configurable: true, value: 800 });
    fireEvent(window, new Event("resize"));
    expect(root).toHaveAttribute("data-browser-state", "focused");
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  it("starts focused rather than creating a 200px content strip near 1024px", () => {
    render(<Harness />);
    const root = setDesktopGeometry();
    Object.defineProperty(root, "clientWidth", { configurable: true, value: 1024 });
    fireEvent(window, new Event("resize"));
    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    expect(root).toHaveAttribute("data-browser-state", "focused");
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  it("transitions at both drag edges and can reveal a dismissed focused shelf", () => {
    render(<Harness />);
    const root = setDesktopGeometry();
    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    dragDivider(600, 450);
    expect(root).toHaveAttribute("data-browser-state", "focused");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss shelf" }));
    const edge = screen.getByTestId("focused-sidebar-edge");
    fireEvent.pointerEnter(edge);
    expect(screen.queryByTestId("focused-sidebar-edge")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close browser preview" }));
    expect(root).toHaveAttribute("data-browser-state", "closed");

    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    dragDivider(800, 1500);
    expect(root).toHaveAttribute("data-browser-state", "closed");
  });

  it("returns focus to Codexify after Browser closes", async () => {
    render(<Harness />);
    setDesktopGeometry();
    const codexifyControl = screen.getByRole("button", { name: "Dismiss shelf" });
    codexifyControl.focus();
    fireEvent.click(screen.getByRole("button", { name: "Open browser preview" }));
    fireEvent.click(screen.getByRole("button", { name: "Focus browser" }));
    fireEvent.click(screen.getByRole("button", { name: "Close browser preview" }));
    await vi.waitFor(() => expect(codexifyControl).toHaveFocus());
  });
});
