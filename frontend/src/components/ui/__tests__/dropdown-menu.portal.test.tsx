import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const originalGetBoundingClientRect = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "getBoundingClientRect"
);
const originalInnerWidth = Object.getOwnPropertyDescriptor(window, "innerWidth");
const originalInnerHeight = Object.getOwnPropertyDescriptor(window, "innerHeight");

function rect(top: number, left: number, width: number, height: number): DOMRect {
  return {
    x: left,
    y: top,
    top,
    left,
    width,
    height,
    bottom: top + height,
    right: left + width,
    toJSON: () => ({}),
  } as DOMRect;
}

describe("DropdownMenu", () => {
  afterEach(() => {
    if (originalGetBoundingClientRect) {
      Object.defineProperty(
        HTMLElement.prototype,
        "getBoundingClientRect",
        originalGetBoundingClientRect
      );
    } else {
      delete (HTMLElement.prototype as Record<string, unknown>).getBoundingClientRect;
    }
    if (originalInnerWidth) {
      Object.defineProperty(window, "innerWidth", originalInnerWidth);
    } else {
      delete (window as Record<string, unknown>).innerWidth;
    }
    if (originalInnerHeight) {
      Object.defineProperty(window, "innerHeight", originalInnerHeight);
    } else {
      delete (window as Record<string, unknown>).innerHeight;
    }
  });

  it("portals menu content outside overflow-clipped containers", () => {
    const { container } = render(
      <div data-testid="clipper" style={{ overflow: "hidden", width: 120, height: 40 }}>
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Choice A</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    const menu = screen.getByRole("menu");
    const clipper = screen.getByTestId("clipper");

    expect(menu).toBeInTheDocument();
    expect(document.body.contains(menu)).toBe(true);
    expect(clipper.contains(menu)).toBe(false);
    expect(container.contains(menu)).toBe(false);
    expect(menu).toHaveStyle({ width: "max-content" });
    expect(menu.className).toContain("max-w-[min(32rem,calc(100vw-24px))]");
  });

  it("prefers top placement when the viewport is constrained below the trigger", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1280,
    });
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      value: 720,
    });
    Object.defineProperty(HTMLElement.prototype, "getBoundingClientRect", {
      configurable: true,
      value: function getBoundingClientRect() {
        if (this.getAttribute?.("role") === "menu") {
          return rect(0, 0, 240, 480);
        }
        if (this.getAttribute?.("data-ddm-root") !== null) {
          return rect(580, 40, 180, 32);
        }
        return rect(0, 0, 180, 32);
      },
    });

    render(
      <div data-testid="clipper" style={{ overflow: "hidden", width: 120, height: 40 }}>
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent side="top" collisionPadding={12} sideOffset={10}>
            <DropdownMenuItem>Choice A</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    const menu = screen.getByRole("menu");
    const clipper = screen.getByTestId("clipper");

    expect(menu).toHaveAttribute("data-side", "top");
    expect(menu.style.getPropertyValue("--dropdown-menu-available-height")).toBe(
      "558px"
    );
    expect(document.body.contains(menu)).toBe(true);
    expect(clipper.contains(menu)).toBe(false);
  });
});
