import { createRef } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import GuardianChatWindow from "./GuardianChatWindow";

it("clamps movement to the application pane and stops moving after pointer cancellation", () => {
  const { unmount } = render(<GuardianChatWindow mode="open" onModeChange={vi.fn()} onDock={vi.fn()} opener={createRef()}>
    <textarea aria-label="Draft" />
  </GuardianChatWindow>);
  const frame = screen.getByRole("dialog", { name: "Guardian Chat" });
  const layer = frame.parentElement!;
  Object.defineProperties(layer, { clientWidth: { value: 700 }, clientHeight: { value: 500 } });
  vi.spyOn(layer, "getBoundingClientRect").mockReturnValue(new DOMRect(30, 20, 700, 500));
  vi.spyOn(frame, "getBoundingClientRect").mockImplementation(() =>
    new DOMRect(30 + parseFloat(frame.style.left), 20 + parseFloat(frame.style.top), 480, 360));
  fireEvent(window, new Event("resize"));
  const handle = screen.getByRole("button", { name: "Move Guardian Chat" });
  handle.setPointerCapture = vi.fn();
  const pointer = (type: string, x: number, y: number) => {
    const event = new MouseEvent(type, { clientX: x, clientY: y, button: 0, bubbles: true });
    Object.defineProperty(event, "pointerId", { value: 1 });
    fireEvent(handle, event);
  };
  pointer("pointerdown", 252, 162);
  pointer("pointermove", -500, -500);
  expect(frame).toHaveStyle({ left: "8px", top: "8px" });
  pointer("pointercancel", 0, 0);
  pointer("pointermove", 1200, 1000);
  expect(frame).toHaveStyle({ left: "8px", top: "8px" });
  fireEvent.keyDown(handle, { key: "ArrowRight" });
  expect(frame).toHaveStyle({ left: "24px" });
  pointer("pointerdown", 65, 40);
  pointer("pointermove", 1200, 1000);
  expect(frame).toHaveStyle({ left: "212px", top: "132px" });
  unmount();
  expect(layer.isConnected).toBe(false);
});
