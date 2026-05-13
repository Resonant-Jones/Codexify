import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import CommandCenterBottomDrawer from "../CommandCenterBottomDrawer";

describe("CommandCenterBottomDrawer", () => {
  const onToggle = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("is collapsed by default when open=false", () => {
    render(<CommandCenterBottomDrawer open={false} onToggle={onToggle} />);
    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).toBe("0px");
  });

  it("is visible when open=true", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).not.toBe("0px");
  });

  it("renders all tab buttons", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    expect(screen.getByTestId("command-center-drawer-tab-terminal")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-drawer-tab-logs")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-drawer-tab-receipts")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-drawer-tab-problems")).toBeInTheDocument();
  });

  it("Terminal tab is default active", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    const terminalTab = screen.getByTestId("command-center-drawer-tab-terminal");
    expect(terminalTab).toHaveAttribute("aria-selected", "true");
  });

  it("Terminal tab shows non-executable copy", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    expect(
      screen.getByText(/Terminal execution is not enabled in this Command Center build/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/input disabled — terminal is non-executable/)
    ).toBeInTheDocument();
  });

  it("switching tabs updates the visible content", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("command-center-drawer-tab-logs"));
    expect(screen.getByTestId("command-center-drawer-tab-logs")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("command-center-drawer-tab-terminal")).toHaveAttribute("aria-selected", "false");
    expect(
      screen.getByText(/Log stream will appear here once available/)
    ).toBeInTheDocument();
  });

  it("receipts tab shows placeholder content", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("command-center-drawer-tab-receipts"));
    expect(
      screen.getByText(/Run receipts and lineage records will appear here/)
    ).toBeInTheDocument();
  });

  it("problems tab shows placeholder content", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("command-center-drawer-tab-problems"));
    expect(
      screen.getByText(/Detected problems and diagnostics will appear here/)
    ).toBeInTheDocument();
  });

  it("close button calls onToggle", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("command-center-drawer-close"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("resize handle is present when open", () => {
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    expect(screen.getByTestId("command-center-drawer-resize-handle")).toBeInTheDocument();
  });

  it("resize handle is absent when closed", () => {
    render(<CommandCenterBottomDrawer open={false} onToggle={onToggle} />);
    expect(screen.queryByTestId("command-center-drawer-resize-handle")).not.toBeInTheDocument();
  });

  it("persists drawer height preference", () => {
    localStorage.setItem("codexify-command-center-drawer-height", "400");
    render(<CommandCenterBottomDrawer open onToggle={onToggle} />);
    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).toBe("400px");
  });
});
