import { act, fireEvent, render, screen } from "@testing-library/react";
import { createPortal } from "react-dom";
import { useRef, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ResponsiveUtilityActions from "./ResponsiveUtilityActions";

function StatefulLauncher() {
  const [open, setOpen] = useState(false);
  return <>
    <button onClick={() => setOpen(true)}>People</button>
    {open && createPortal(
      <div role="dialog" onPointerDown={(event) => event.stopPropagation()}>
        People window
      </div>,
      document.body
    )}
  </>;
}

function Harness() {
  const ref = useRef<HTMLDivElement>(null);
  return <div ref={ref}>
    <ResponsiveUtilityActions containerRef={ref} actions={[
      { label: "Settings", control: <button>Settings</button> },
      { label: "People", control: <StatefulLauncher /> },
      { label: "Unavailable", control: null },
    ]} />
    <button>Outside</button>
  </div>;
}

afterEach(() => vi.restoreAllMocks());

describe("responsive utilities", () => {
  it("uses the containing pane width and supports keyboard opening, dismissal, and focus return", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({ width: 872 } as DOMRect);
    render(<Harness />);
    const trigger = screen.getByRole("button", { name: "Utilities" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Settings" })).toBeNull();
    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    expect(screen.getByRole("button", { name: "Settings" })).toHaveFocus();
    expect(screen.queryByText("Unavailable")).toBeNull();
    fireEvent.keyDown(screen.getByRole("button", { name: "Settings" }), { key: "Escape" });
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    fireEvent.pointerDown(screen.getByRole("button", { name: "Outside" }));
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps launcher state through disclosure dismissal and changes between wide and compact layouts", () => {
    let width = 1440;
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(() => ({ width }) as DOMRect);
    render(<Harness />);
    expect(screen.queryByRole("button", { name: "Utilities" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "People" }));
    expect(screen.getByRole("dialog")).toBeVisible();
    act(() => { width = 872; window.dispatchEvent(new Event("resize")); });
    fireEvent.click(screen.getByRole("button", { name: "Utilities" }));
    fireEvent.pointerDown(screen.getByRole("dialog"));
    expect(screen.getByRole("button", { name: "Utilities" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("dialog")).toBeVisible();
    act(() => { width = 1440; window.dispatchEvent(new Event("resize")); });
    expect(screen.getByRole("button", { name: "People" })).toBeVisible();
    expect(screen.getByRole("dialog")).toBeVisible();
  });
});
