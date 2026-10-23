import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";

/**
 * MOB-G1-TASK-1 — mobile route disclosure.
 *
 * The compact mobile conversation surface is the only composer posture that
 * rendered no provider or model control at all. A phone user could therefore
 * not see which route was selected, and could not switch provider mid-thread.
 *
 * These tests pin the corrected contract:
 *   - the active route pair (provider runtime identity + model) is visible;
 *   - provider and model are switchable from that row;
 *   - model selection is owned in exactly one place;
 *   - the desktop and landing postures are unchanged;
 *   - the row is absent when the authorized catalog offers no route.
 */

const providerOptions = [{ value: "local", label: "Whoosh'd" }];
const modelOptions = [{ value: "local-chat", label: "DeepSeek" }];

const originalScrollTo = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollTo"
);

function restoreScrollTo() {
  if (originalScrollTo) {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", originalScrollTo);
    return;
  }
  delete (HTMLElement.prototype as Record<string, unknown>).scrollTo;
}

function mount(props: Partial<React.ComponentProps<typeof Composer>> = {}) {
  return render(
    <Composer
      onSend={vi.fn()}
      draftValue=""
      compactMobile
      activeProviderId="local"
      providerOptions={providerOptions}
      activeModelId="local-chat"
      modelOptions={modelOptions}
      {...props}
    />
  );
}

describe("compact mobile composer route disclosure", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    restoreScrollTo();
    vi.restoreAllMocks();
  });

  it("shows the active provider runtime identity next to the active model", () => {
    mount();

    const routeRow = screen.getByTestId("composer-mobile-route-row");
    expect(routeRow).toBeInTheDocument();

    // The provider is labelled by runtime identity ("Whoosh'd"), the model by
    // its own label ("DeepSeek"). Both are shown together so the pairing is
    // never ambiguous on a phone.
    expect(
      screen.getByRole("button", { name: "Select provider" })
    ).toHaveTextContent("Whoosh'd");
    expect(
      screen.getByRole("button", { name: "Select model" })
    ).toHaveTextContent("DeepSeek");
  });

  it("uses the phone-shell bare trigger variant so the composer does not widen", () => {
    mount();

    for (const name of ["Select provider", "Select model"]) {
      const trigger = screen.getByRole("button", { name });
      expect(trigger).toHaveAttribute(
        "data-composer-select-trigger-variant",
        "bare"
      );
    }
  });

  it("switches the provider from the route row", async () => {
    const onProviderChange = vi.fn();
    mount({
      providerOptions: [
        { value: "local", label: "Whoosh'd" },
        { value: "deepseek", label: "DeepSeek cloud" },
      ],
      onProviderChange,
    });

    fireEvent.click(screen.getByRole("button", { name: "Select provider" }));
    const option = await screen.findByRole("menuitem", { name: "DeepSeek cloud" });
    fireEvent.click(option);
    await act(async () => {});

    expect(onProviderChange).toHaveBeenCalledWith("deepseek");
  });

  it("switches the model from the route row", async () => {
    const onModelChange = vi.fn();
    mount({
      modelOptions: [
        { value: "local-chat", label: "DeepSeek" },
        { value: "local-chat-2", label: "Gemma" },
      ],
      onModelChange,
    });

    fireEvent.click(screen.getByRole("button", { name: "Select model" }));
    const option = await screen.findByRole("menuitem", { name: "Gemma" });
    fireEvent.click(option);
    await act(async () => {});

    expect(onModelChange).toHaveBeenCalledWith("local-chat-2");
  });

  it("owns model selection in the route row, without duplicating it in the actions menu", async () => {
    mount();

    fireEvent.click(screen.getByRole("button", { name: "Open composer actions" }));
    await screen.findByText("Composer actions");

    // The action menu no longer carries its own Model section; the route row
    // is the single model affordance on a phone.
    expect(screen.queryByText("Model")).toBeNull();
    expect(
      screen.queryByRole("menuitem", { name: "DeepSeek" })
    ).toBeNull();
  });

  it("hides the route row when the authorized catalog offers no route", () => {
    mount({ providerOptions: [], modelOptions: [] });

    expect(screen.queryByTestId("composer-mobile-route-row")).toBeNull();
  });

  it("does not add a route row to the desktop conversation surface", () => {
    mount({ compactMobile: false });

    expect(screen.queryByTestId("composer-mobile-route-row")).toBeNull();
    // Desktop keeps its existing selector row.
    expect(
      screen.getByRole("button", { name: "Select provider" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select model" })
    ).toBeInTheDocument();
  });

  it("leaves the landing posture on its own inference controls", () => {
    mount({ presentationMode: "landing" });

    // The landing surface already owned provider and model selection.
    expect(screen.queryByTestId("composer-mobile-route-row")).toBeNull();
    expect(
      screen.getByRole("button", { name: "Select provider" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select model" })
    ).toBeInTheDocument();
  });
});
