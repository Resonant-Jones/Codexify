import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SystemStatusIndicator from "./SystemStatusIndicator";

const ROWS = [
  { label: "Guardian", status: "Healthy", tone: "healthy" as const },
  { label: "Providers", status: "Healthy", tone: "healthy" as const },
  { label: "Live updates", status: "Healthy", tone: "healthy" as const },
];

function anchorRect(overrides: Partial<DOMRect> = {}): DOMRect {
  return {
    x: 1124,
    y: 20,
    width: 36,
    height: 36,
    top: 20,
    right: 1160,
    bottom: 56,
    left: 1124,
    toJSON: () => ({}),
    ...overrides,
  } as DOMRect;
}

describe("SystemStatusIndicator overlay", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1200,
    });
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      value: 800,
    });
  });

  afterEach(() => {
    cleanup();
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("portals the open panel above shell clipping while preserving its anchor", async () => {
    render(
      <SystemStatusIndicator
        level="attention"
        issue={{
          title: "Live updates unavailable",
          detail: "The event stream is disconnected.",
        }}
        rows={ROWS}
      />
    );

    const control = screen.getByTestId("system-status-control");
    vi.spyOn(control, "getBoundingClientRect").mockReturnValue(anchorRect());

    fireEvent.click(screen.getByTestId("system-status-toggle"));

    const panel = screen.getByTestId("system-status-panel");
    await waitFor(() => expect(panel.style.visibility).toBe("visible"));

    expect(document.body).toContainElement(panel);
    expect(control).not.toContainElement(panel);
    expect(panel.style.position).toBe("fixed");
    expect(panel.style.top).toBe("65px");
    expect(panel.style.right).toBe("40px");
    expect(panel.style.maxHeight).toBe("576px");
    expect(panel.style.zIndex).toBe("var(--shell-overlay-z, 2000)");

    fireEvent.pointerDown(panel);
    expect(screen.getByTestId("system-status-panel")).toBeInTheDocument();

    fireEvent.pointerDown(document.body);
    expect(screen.queryByTestId("system-status-panel")).toBeNull();
  });

  it("repositions with the anchor and closes on Escape", async () => {
    render(
      <SystemStatusIndicator
        level="healthy"
        issue={null}
        rows={ROWS}
      />
    );

    const control = screen.getByTestId("system-status-control");
    const rectSpy = vi
      .spyOn(control, "getBoundingClientRect")
      .mockReturnValue(anchorRect());

    fireEvent.click(screen.getByTestId("system-status-toggle"));
    const panel = screen.getByTestId("system-status-panel");
    await waitFor(() => expect(panel.style.right).toBe("40px"));

    rectSpy.mockReturnValue(
      anchorRect({ x: 1024, left: 1024, right: 1060, top: 40, bottom: 76 })
    );
    fireEvent(window, new Event("resize"));

    await waitFor(() => {
      expect(panel.style.top).toBe("85px");
      expect(panel.style.right).toBe("140px");
    });

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByTestId("system-status-panel")).toBeNull();
  });
});
