import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import SegmentedThemeControl from "@/components/controls/SegmentedThemeControl";

describe("SegmentedThemeControl", () => {
  test("exposes a labeled control group with glass-pill and pill-tab buttons", () => {
    const onChange = vi.fn();
    render(<SegmentedThemeControl mode="system" onChange={onChange} />);

    const group = screen.getByRole("group", { name: "Theme mode" });
    expect(group).toBeInTheDocument();
    expect(group).toHaveClass("glass-pill", "inline-flex");

    const lightButton = screen.getByRole("button", { name: "Light" });
    const systemButton = screen.getByRole("button", { name: "System" });
    const darkButton = screen.getByRole("button", { name: "Dark" });

    for (const button of [lightButton, systemButton, darkButton]) {
      expect(button).toHaveClass("pill-tab");
      expect(button).toHaveAttribute("type", "button");
    }
  });

  test("marks the selected option active and unselected options inactive", () => {
    const onChange = vi.fn();
    render(<SegmentedThemeControl mode="light" onChange={onChange} />);

    const lightButton = screen.getByRole("button", { name: "Light" });
    const systemButton = screen.getByRole("button", { name: "System" });
    const darkButton = screen.getByRole("button", { name: "Dark" });

    expect(lightButton).toHaveAttribute("data-state", "active");
    expect(lightButton).toHaveAttribute("aria-pressed", "true");

    expect(systemButton).toHaveAttribute("data-state", "inactive");
    expect(systemButton).toHaveAttribute("aria-pressed", "false");

    expect(darkButton).toHaveAttribute("data-state", "inactive");
    expect(darkButton).toHaveAttribute("aria-pressed", "false");
  });

  test("keeps its selected value on the default filled pill contract", () => {
    const onChange = vi.fn();
    render(<SegmentedThemeControl mode="light" onChange={onChange} />);

    const group = screen.getByRole("group", { name: "Theme mode" });
    const selected = screen.getByRole("button", { name: "Light" });

    expect(selected).toHaveAttribute("data-state", "active");
    expect(selected.style.background).toBe("");
    expect(group.style.getPropertyValue("--pill-active-bg")).toBe("");
    expect(group.style.getPropertyValue("--settings-nav-surface")).toBe("");
    expect(group.style.getPropertyValue("--pill-active-border")).toBe("");
  });

  test("calls onChange with the correct theme mode on click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SegmentedThemeControl mode="system" onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Light" }));
    expect(onChange).toHaveBeenCalledWith("light");

    await user.click(screen.getByRole("button", { name: "Dark" }));
    expect(onChange).toHaveBeenCalledWith("dark");

    await user.click(screen.getByRole("button", { name: "System" }));
    expect(onChange).toHaveBeenCalledWith("system");
  });

  test("does not contain legacy square-button or hardcoded color classes", () => {
    const onChange = vi.fn();
    render(<SegmentedThemeControl mode="system" onChange={onChange} />);

    for (const button of screen.getAllByRole("button")) {
      expect(button.className).not.toContain("rounded-none");
    }

    const group = screen.getByRole("group", { name: "Theme mode" });
    expect(group.className).not.toContain("bg-white");
    expect(group.className).not.toContain("neutral");
    expect(group.className).not.toContain("rounded-xl");
    expect(group.className).not.toContain("overflow-hidden");
  });

  test("renders all three theme options", () => {
    const onChange = vi.fn();
    render(<SegmentedThemeControl mode="dark" onChange={onChange} />);

    expect(screen.getByRole("button", { name: "Light" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "System" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dark" })).toBeInTheDocument();
  });
});
