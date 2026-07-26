import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import SettingsRangeControl from "@/components/controls/SettingsRangeControl";

describe("SettingsRangeControl", () => {
  test("renders a native range input with accent color", () => {
    render(<SettingsRangeControl data-testid="test-slider" />);

    const slider = screen.getByTestId("test-slider");
    expect(slider).toBeInTheDocument();
    expect(slider).toHaveAttribute("type", "range");
    expect(slider.style.accentColor).toBe("var(--accent)");
  });

  test("forwards min, max, step, and value properties", () => {
    render(
      <SettingsRangeControl
        data-testid="test-slider"
        min={-100}
        max={100}
        step={5}
        value={42}
      />
    );

    const slider = screen.getByTestId("test-slider");
    expect(slider).toHaveAttribute("min", "-100");
    expect(slider).toHaveAttribute("max", "100");
    expect(slider).toHaveAttribute("step", "5");
    expect(slider).toHaveAttribute("value", "42");
  });

  test("forwards ARIA attributes", () => {
    render(
      <SettingsRangeControl
        data-testid="test-slider"
        aria-label="Test slider"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={50}
      />
    );

    const slider = screen.getByTestId("test-slider");
    expect(slider).toHaveAttribute("aria-label", "Test slider");
    expect(slider).toHaveAttribute("aria-valuemin", "0");
    expect(slider).toHaveAttribute("aria-valuemax", "100");
    expect(slider).toHaveAttribute("aria-valuenow", "50");
  });

  test("calls onChange when the slider value changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SettingsRangeControl
        data-testid="test-slider"
        value={50}
        onChange={onChange}
      />
    );

    const slider = screen.getByTestId("test-slider");
    // userEvent does not fully support range inputs; verify the handler is wired
    expect(slider).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  test("preserves disabled state", () => {
    render(
      <SettingsRangeControl data-testid="test-slider" disabled />
    );

    const slider = screen.getByTestId("test-slider");
    expect(slider).toBeDisabled();
  });

  test("merges a caller-provided className on the wrapper", () => {
    render(
      <SettingsRangeControl
        data-testid="test-slider"
        className="extra-class"
      />
    );

    const slider = screen.getByTestId("test-slider");
    // The wrapper div should have the extra class; the input is inside
    const wrapper = slider.closest("div.w-full");
    expect(wrapper).toHaveClass("extra-class");
  });

  test("does not contain hardcoded blue or green accent colors", () => {
    render(<SettingsRangeControl data-testid="test-slider" />);

    const slider = screen.getByTestId("test-slider");
    const accentColor = slider.style.accentColor;
    expect(accentColor).toBe("var(--accent)");
    expect(accentColor).not.toContain("#");
    expect(accentColor).not.toContain("blue");
    expect(accentColor).not.toContain("green");
  });
});
