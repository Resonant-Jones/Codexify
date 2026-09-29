import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Composer } from "../Composer";

const providerChange = vi.fn(), modelChange = vi.fn(), modeChange = vi.fn();
const originalScrollTo = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollTo");
let finePointer = true;
const strip = () => screen.getByTestId("composer-landing-inference-controls");
const zone = () => screen.getByTestId("composer-landing-hover-zone");
const revealed = (value: boolean) => expect(strip()).toHaveAttribute("data-revealed", String(value));
const leave = async () => {
  fireEvent.pointerLeave(zone());
  await act(async () => { vi.advanceTimersByTime(150); });
};
function mount(props: Partial<React.ComponentProps<typeof Composer>> = {}) {
  return render(<Composer onSend={vi.fn()} presentationMode="landing"
    providerOptions={[{ value: "local", label: "Local" }]}
    modelOptions={[{ value: "model", label: "Test model" }]}
    inferenceModeOptions={[{ value: "normal", label: "Normal" }]}
    onProviderChange={providerChange} onModelChange={modelChange}
    onInferenceModeChange={modeChange} {...props} />);
}
beforeEach(() => {
  vi.useFakeTimers();
  finePointer = true;
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({
    matches: query === "(hover: hover) and (pointer: fine)" && finePointer,
    media: query, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })));
  Object.defineProperty(HTMLElement.prototype, "scrollTo", { configurable: true, value: vi.fn() });
});
afterEach(() => {
  cleanup();
  if (originalScrollTo) Object.defineProperty(HTMLElement.prototype, "scrollTo", originalScrollTo);
  else delete (HTMLElement.prototype as unknown as Record<string, unknown>).scrollTo;
  vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.clearAllMocks();
});

describe("landing inference disclosure", () => {
  it("rests hidden with persistent actions and send; textarea approach does nothing", () => {
    mount(); revealed(false);
    expect(strip()).toHaveClass("opacity-0", "pointer-events-none", "[transform:translateY(8px)]");
    expect(screen.getByRole("button", { name: "Open composer actions" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Send" })).toBeVisible();
    fireEvent.pointerEnter(screen.getByTestId("composer-textarea")); revealed(false);
  });
  it("+ opens canonical actions without disclosing inference controls", () => {
    mount(); fireEvent.click(screen.getByRole("button", { name: "Open composer actions" }));
    expect(screen.getByText("Composer actions")).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Attach file" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Generate image" })).toBeVisible();
    expect(screen.getByText(/RAG/i)).toBeVisible(); revealed(false);
  });
  it("reveals on lower approach and survives pointer transfer before dismissing", async () => {
    mount(); fireEvent.pointerEnter(zone()); revealed(true);
    expect(strip()).toHaveClass("[transform:translateY(0px)]", "opacity-100", "pointer-events-auto");
    fireEvent.pointerLeave(zone());
    fireEvent.pointerEnter(screen.getByRole("button", { name: "Select model" }));
    await act(async () => { vi.advanceTimersByTime(150); }); revealed(true);
    await leave(); revealed(false);
  });
  it("reveals and retains keyboard focus until focus leaves", async () => {
    mount(); act(() => screen.getByRole("button", { name: "Select provider" }).focus());
    revealed(true); await leave(); revealed(true);
    act(() => screen.getByRole("button", { name: "Select model" }).focus()); revealed(true);
    act(() => screen.getByTestId("composer-textarea").focus()); revealed(false);
  });
  it.each([
    ["provider", "Local", providerChange, "local"],
    ["model", "Test model", modelChange, "model"],
    ["inference mode", "Normal", modeChange, "normal"],
  ] as const)("retains the portaled %s menu and invokes its callback", async (name, label, callback, value) => {
    mount(); fireEvent.pointerEnter(zone());
    fireEvent.click(screen.getByRole("button", { name: `Select ${name}` }));
    await leave(); revealed(true);
    const option = screen.getByRole("menuitem", { name: label });
    expect(zone().contains(option)).toBe(false);
    fireEvent.pointerEnter(option);
    act(() => option.focus());
    await act(async () => { vi.advanceTimersByTime(150); }); revealed(true);
    fireEvent.click(option); await act(async () => {});
    expect(callback).toHaveBeenCalledWith(value); revealed(false);
  });
  it("tracks programmatic provider open and Escape without pinning", async () => {
    mount({ providerOpenSignal: 1 }); await act(async () => {}); revealed(true);
    fireEvent.keyDown(document, { key: "Escape" }); await act(async () => {}); revealed(false);
  });
  it("reserves fixed internal geometry with reduced-motion styles and only three selectors", () => {
    mount({ projectOptions: [{ value: "1", label: "Project" }], onProjectChange: vi.fn() });
    const row = screen.getByTestId("composer-landing-control-row"), rowClass = row.className;
    const cluster = screen.getByTestId("composer-landing-control-cluster");
    const textarea = screen.getByTestId("composer-textarea"), textareaStyle = textarea.getAttribute("style");
    const actions = screen.getByRole("button", { name: "Open composer actions" });
    const send = screen.getByRole("button", { name: "Send" });
    expect(row).toHaveClass("flex"); expect(row).not.toHaveClass("grid");
    expect(cluster).toContainElement(actions); expect(cluster).toContainElement(zone());
    expect(zone()).toHaveStyle({ height: "32px", minWidth: "0" });
    expect(strip()).toHaveClass("absolute", "motion-reduce:transition-none", "motion-reduce:!transform-none");
    expect(strip()).toHaveClass("justify-start"); expect(strip()).not.toHaveClass("justify-center");
    expect(within(strip()).getAllByRole("button")).toHaveLength(3);
    expect(within(strip()).queryByRole("button", { name: "Select project" })).toBeNull();
    expect(within(strip()).queryByRole("button", { name: "Toggle Coding Loop mode" })).toBeNull();
    for (const name of ["Select provider", "Select model", "Select inference mode"]) {
      expect(screen.getByRole("button", { name })).toHaveAttribute(
        "data-composer-select-trigger-variant",
        "chip"
      );
    }
    fireEvent.pointerEnter(zone()); expect(row.className).toBe(rowClass);
    expect(textarea.getAttribute("style")).toBe(textareaStyle);
    expect(screen.getByRole("button", { name: "Open composer actions" })).toBe(actions);
    expect(screen.getByRole("button", { name: "Send" })).toBe(send);
  });
  it.each([false, true])("keeps touch selection available (compact=%s)", async (compactMobile) => {
    finePointer = false; mount({ compactMobile }); revealed(true); await leave(); revealed(true);
    fireEvent.click(screen.getByRole("button", { name: "Select inference mode" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Normal" }));
    expect(modeChange).toHaveBeenCalledWith("normal");
  });
  it("preserves conversation controls without landing disclosure", () => {
    mount({ presentationMode: "conversation" });
    expect(screen.queryByTestId("composer-landing-hover-zone")).toBeNull();
    expect(screen.getByTestId("composer-controls-strip")).toBeVisible();
    for (const name of ["Select provider", "Select model", "Select inference mode", "Toggle Coding Loop mode", "Open composer actions"]) {
      expect(screen.getByRole("button", { name })).toBeVisible();
    }
    for (const name of ["Select provider", "Select model", "Select inference mode"]) {
      expect(screen.getByRole("button", { name })).toHaveAttribute(
        "data-composer-select-trigger-variant",
        "bare"
      );
    }
  });
});
