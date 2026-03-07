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

function restoreDescriptor(
  key:
    | "offsetTop"
    | "offsetHeight"
    | "clientHeight"
    | "scrollHeight"
    | "scrollTo",
  descriptor?: PropertyDescriptor
) {
  if (descriptor) {
    Object.defineProperty(HTMLElement.prototype, key, descriptor);
    return;
  }
  delete (HTMLElement.prototype as Record<string, unknown>)[key];
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
    scrollToMock.mockReset();
  });

  it("centers the selected option on open and keeps keyboard navigation in view", async () => {
    const onSelect = vi.fn();

    render(
      <ComposerSelectMenu
        ariaLabel="Select model"
        menuLabel="Model"
        valueLabel="Model 8"
        selectedValue="model-8"
        options={Array.from({ length: 12 }, (_, index) => ({
          value: `model-${index}`,
          label: `Model ${index}`,
          meta: `${index + 1}k`,
        }))}
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
  });
});
