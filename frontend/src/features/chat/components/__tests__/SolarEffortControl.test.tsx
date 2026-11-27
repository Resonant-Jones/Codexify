import { useState } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SolarEffortControl } from "../SolarEffortControl";

function mount(levels: string[], initialValue = "default") {
  const onChange = vi.fn();
  function ControlledEffort() {
    const [value, setValue] = useState(initialValue);
    return <SolarEffortControl levels={levels} value={value} onChange={(next) => {
      onChange(next);
      setValue(next);
    }} />;
  }

  render(<ControlledEffort />);
  const trigger = screen.getByRole("button", { name: /^Thinking effort:/ });
  fireEvent.click(trigger);
  const panel = screen.getByRole("dialog", { name: "Thinking effort" });
  const slider = within(panel).getByRole("slider", { name: "Thinking effort" });
  const reset = within(panel).getByRole("button", { name: "Provider default" });
  return { trigger, panel, slider, reset, onChange };
}

describe("Solar effort control", () => {
  it("preserves provider order and passes through each selection without normalizing the value", () => {
    const { trigger, panel, slider, onChange } = mount(["max", "extra_high", "low"], "max");
    expect(slider).toHaveAttribute("min", "0");
    expect(slider).toHaveAttribute("max", "2");
    expect(slider).toHaveAttribute("step", "1");
    expect(slider).toHaveAttribute("aria-valuetext", "Max");
    expect(within(panel).queryByText("Medium")).toBeNull();

    fireEvent.change(slider, { target: { value: "1" } });
    expect(onChange).toHaveBeenLastCalledWith("extra_high");
    expect(slider).toHaveAttribute("aria-valuetext", "Extra high");
    expect(trigger).toHaveAccessibleName("Thinking effort: Extra high");
    expect(panel.querySelector("[data-tone]")).toHaveAttribute("data-tone", "extra-high");

    fireEvent.change(slider, { target: { value: "2" } });
    expect(onChange).toHaveBeenLastCalledWith("low");
  });

  it("keeps provider default separate from the native scale and restores it on reset", () => {
    const { trigger, panel, slider, reset, onChange } = mount(["low", "high", "max"]);
    expect(slider).toHaveAttribute("aria-valuetext", "Provider default");
    expect(reset).toHaveAttribute("aria-pressed", "true");
    expect(panel.querySelector("[data-tone]")).toBeNull();
    expect(onChange).not.toHaveBeenCalled();

    fireEvent.keyDown(slider, { key: "End" });
    expect(onChange).toHaveBeenLastCalledWith("max");
    expect(reset).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(reset);
    expect(onChange).toHaveBeenLastCalledWith("default");
    expect(trigger).toHaveAccessibleName("Thinking effort: Provider default");
    expect(slider).toHaveAttribute("aria-valuetext", "Provider default");
    expect(panel.querySelector("[data-tone]")).toBeNull();
  });

  it("selects the first level on a pointer release at the native minimum", () => {
    const { slider, onChange } = mount(["low", "high"]);
    fireEvent.pointerUp(slider, { button: 0 });
    expect(onChange).toHaveBeenCalledExactlyOnceWith("low");
  });

  it("supports a single stop with keyboard entry and restores focus on Escape", async () => {
    const { slider, trigger, onChange } = mount(["high"]);
    expect(slider).toHaveAttribute("max", "0");
    await waitFor(() => expect(slider).toHaveFocus());
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onChange).toHaveBeenCalledExactlyOnceWith("high");

    fireEvent.keyDown(slider, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(trigger).toHaveFocus();
  });

  it("treats a stale selection as provider default and hides the control without capabilities", () => {
    const onChange = vi.fn();
    const view = render(<SolarEffortControl levels={["low"]} value="max" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Thinking effort: Provider default" }));
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuetext", "Provider default");
    expect(onChange).not.toHaveBeenCalled();
    view.rerender(<SolarEffortControl levels={[]} value="max" onChange={onChange} />);
    expect(screen.queryByRole("slider")).toBeNull();
    expect(screen.queryByRole("button", { name: /^Thinking effort:/ })).toBeNull();
  });
});
