import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ComposerSelectMenu } from "@/features/chat/components/ComposerSelectMenu";

const ITEM_HEIGHT = 32;
const VIEWPORT_HEIGHT = 128;

const originalOffsetTop = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "offsetTop"
);
const originalOffsetHeight = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "offsetHeight"
);
const originalClientHeight = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "clientHeight"
);
const originalScrollHeight = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollHeight"
);
const originalScrollTo = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollTo"
);
const originalGetBoundingClientRect = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "getBoundingClientRect"
);
const originalInnerWidth = Object.getOwnPropertyDescriptor(window, "innerWidth");
const originalInnerHeight = Object.getOwnPropertyDescriptor(window, "innerHeight");

function restoreDescriptor(
  key:
    | "offsetTop"
    | "offsetHeight"
    | "clientHeight"
    | "scrollHeight"
    | "scrollTo"
    | "getBoundingClientRect",
  descriptor?: PropertyDescriptor
) {
  if (descriptor) {
    Object.defineProperty(HTMLElement.prototype, key, descriptor);
    return;
  }
  delete (HTMLElement.prototype as Record<string, unknown>)[key];
}

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

describe("ComposerSelectMenu", () => {
  const scrollToMock = vi.fn();

  beforeEach(() => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      callback(0);
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
    vi.spyOn(HTMLElement.prototype, "focus").mockImplementation(() => {});
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: scrollToMock,
    });

    Object.defineProperty(HTMLElement.prototype, "offsetTop", {
      configurable: true,
      get() {
        const index = Number(this.getAttribute?.("data-option-index") ?? -1);
        return index >= 0 ? index * ITEM_HEIGHT : 0;
      },
    });
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get() {
        return this.getAttribute?.("data-composer-select-scroll-region") === "true"
          ? VIEWPORT_HEIGHT
          : ITEM_HEIGHT;
      },
    });
    Object.defineProperty(HTMLElement.prototype, "clientHeight", {
      configurable: true,
      get() {
        return this.getAttribute?.("data-composer-select-scroll-region") === "true"
          ? VIEWPORT_HEIGHT
          : ITEM_HEIGHT;
      },
    });
    Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
      configurable: true,
      get() {
        if (this.getAttribute?.("data-composer-select-scroll-region") !== "true") {
          return ITEM_HEIGHT;
        }
        return this.querySelectorAll("[data-option-index]").length * ITEM_HEIGHT;
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    restoreDescriptor("offsetTop", originalOffsetTop);
    restoreDescriptor("offsetHeight", originalOffsetHeight);
    restoreDescriptor("clientHeight", originalClientHeight);
    restoreDescriptor("scrollHeight", originalScrollHeight);
    restoreDescriptor("scrollTo", originalScrollTo);
    restoreDescriptor("getBoundingClientRect", originalGetBoundingClientRect);
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
    scrollToMock.mockReset();
  });

  it("centers the selected option on open and keeps keyboard navigation in view", async () => {
    const onSelect = vi.fn();
    const options = Array.from({ length: 12 }, (_, index) => ({
      value: `model-${index}`,
      label: `Model ${index}`,
      meta: `${index + 1}k`,
    }));
    const { rerender } = render(
      <ComposerSelectMenu
        ariaLabel="Select model"
        menuLabel="Model"
        valueLabel="Model 8"
        selectedValue="model-8"
        options={options}
        onSelect={onSelect}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Select model" }));

    const menu = await screen.findByRole("menu", { name: "Model" });
    const selectedOption = screen.getByRole("menuitem", { name: /Model 8/i });

    await waitFor(() => {
      expect(scrollToMock).toHaveBeenCalledWith({ behavior: "auto", top: 208 });
    });
    expect(selectedOption).toHaveAttribute("data-selected", "true");

    fireEvent.keyDown(menu, { key: "ArrowDown" });

    await waitFor(() => {
      expect(scrollToMock).toHaveBeenLastCalledWith({
        behavior: "auto",
        top: 240,
      });
    });

    fireEvent.keyDown(menu, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("model-9");

    rerender(
      <ComposerSelectMenu
        ariaLabel="Select model"
        menuLabel="Model"
        valueLabel="Model 9"
        selectedValue="model-9"
        options={options}
        onSelect={onSelect}
      />
    );

    scrollToMock.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Select model" }));

    await screen.findByRole("menu", { name: "Model" });
    await waitFor(() => {
      expect(scrollToMock).toHaveBeenCalledWith({
        behavior: "auto",
        top: 240,
      });
    });
    expect(screen.getByRole("menuitem", { name: /Model 9/i })).toHaveAttribute(
      "data-selected",
      "true"
    );
  });

  it("keeps the menu bounded to the viewport and scrollable when opening upward", async () => {
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
          return rect(0, 0, 240, 640);
        }
        if (this.getAttribute?.("data-ddm-root") !== null) {
          return rect(580, 32, 180, 32);
        }
        return rect(0, 0, 180, ITEM_HEIGHT);
      },
    });

    render(
      <ComposerSelectMenu
        ariaLabel="Select model"
        menuLabel="Model"
        valueLabel="Model 2"
        selectedValue="model-2"
        options={Array.from({ length: 18 }, (_, index) => ({
          value: `model-${index}`,
          label: `Model ${index}`,
          meta: `${index + 1}k`,
        }))}
        onSelect={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Select model" }));

    const menu = await screen.findByRole("menu", { name: "Model" });
    const scrollRegion = menu.querySelector(
      '[data-composer-select-scroll-region="true"]'
    );

    expect(menu).toHaveAttribute("data-side", "top");
    expect(menu.style.getPropertyValue("--dropdown-menu-available-height")).toBe(
      "558px"
    );
    expect(menu.style.maxHeight).toBe(
      "min(24rem, var(--dropdown-menu-available-height, calc(100vh - 24px)))"
    );
    expect(scrollRegion).not.toBeNull();
    expect(scrollRegion).toHaveClass("min-h-0");
    expect(scrollRegion).toHaveClass("flex-1");
    expect(scrollRegion).toHaveClass("overflow-y-auto");
  });
});
