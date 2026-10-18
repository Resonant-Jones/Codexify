import { createEvent, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";

import SettingsView from "../SettingsView";
import { DEFAULT_GLASS_TREATMENT, type GlassTreatment } from "@/theme/glassTreatment";

/**
 * Glass Treatment picker coverage.
 *
 * Scoped to the control itself: three options, accessible radio semantics,
 * keyboard operation, and the separation between the saved preference and the
 * treatment that actually renders when an accessibility override applies.
 */

/**
 * Stateful harness. The picker is a controlled component, so keyboard
 * navigation reads the current selection back from its prop — a static mock
 * would never advance past the first option and would not represent real use.
 */
function renderPicker(
  overrides: Partial<Parameters<typeof SettingsView>[0]> = {}
) {
  const setGlassTreatment = vi.fn();
  function Harness() {
    const [treatment, setTreatment] = useState<GlassTreatment>(
      overrides.glassTreatment ?? DEFAULT_GLASS_TREATMENT
    );
    return (
      <SettingsView
        mode="light"
        setMode={vi.fn()}
        guardianName="Guardian"
        setGuardianName={vi.fn()}
        userName="User"
        setUserName={vi.fn()}
        role="Builder"
        setRole={vi.fn()}
        notes="Notes"
        setNotes={vi.fn()}
        baseColor="#111827"
        setBaseColor={vi.fn()}
        depth={0.3}
        setDepth={vi.fn()}
        fade={0.2}
        setFade={vi.fn()}
        resolved="light"
        systemPrompt="Original system prompt"
        setSystemPrompt={vi.fn()}
        wallpaper={null}
        setWallpaper={vi.fn()}
        extColors={{} as never}
        setExtColors={vi.fn()}
        dashboardThreadRows={2}
        setDashboardThreadRows={vi.fn()}
        {...overrides}
        glassTreatment={treatment}
        setGlassTreatment={(next) => {
          setGlassTreatment(next);
          setTreatment(next);
        }}
      />
    );
  }
  const result = render(<Harness />);
  return { setGlassTreatment, ...result };
}

describe("Glass Treatment picker", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.history.pushState({}, "", "/chat/42");
  });

  it("renders a labelled radio group with exactly three options", async () => {
    renderPicker();
    const group = await screen.findByRole("radiogroup", {
      name: "Glass Treatment",
    });
    const options = within(group).getAllByRole("radio");
    expect(options.map((o) => o.textContent?.trim())).toEqual([
      "Refractive",
      "Frosted",
      "Solid",
    ]);
  });

  it("sits above Surface Depth within Material Controls", async () => {
    renderPicker();
    const control = await screen.findByTestId("glass-treatment-control");
    const depth = screen.getByTestId("surface-depth-slider");
    const a = control.getBoundingClientRect();
    const b = depth.getBoundingClientRect();
    // jsdom reports zeroes; fall back to document order, which is what the
    // visual stacking follows.
    if (a.top === 0 && b.top === 0) {
      expect(
        control.compareDocumentPosition(depth) &
          Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    } else {
      expect(a.top).toBeLessThanOrEqual(b.top);
    }
  });

  it("reflects the supplied preference as the checked option", async () => {
    renderPicker({ glassTreatment: "frosted" as GlassTreatment });
    await screen.findByTestId("glass-treatment-control");
    const checked = screen
      .getAllByRole("radio")
      .filter((o) => o.getAttribute("aria-checked") === "true");
    expect(checked).toHaveLength(1);
    expect(checked[0].textContent?.trim()).toBe("Frosted");
  });

  it("uses a single roving tab stop on the checked option", async () => {
    renderPicker({ glassTreatment: "solid" as GlassTreatment });
    await screen.findByTestId("glass-treatment-control");
    const options = screen.getAllByRole("radio");
    const tabbable = options.filter((o) => o.getAttribute("tabindex") === "0");
    expect(tabbable).toHaveLength(1);
    expect(tabbable[0].textContent?.trim()).toBe("Solid");
  });

  it.each(["frosted", "solid"] as const)(
    "reports %s on selection",
    async (treatment) => {
      const { setGlassTreatment } = renderPicker();
      await screen.findByTestId("glass-treatment-control");
      await userEvent.click(
        screen.getByTestId(`glass-treatment-option-${treatment}`)
      );
      expect(setGlassTreatment).toHaveBeenCalledWith(treatment);
      const selected = screen.getByTestId(`glass-treatment-option-${treatment}`);
      expect(selected).toHaveAttribute("aria-checked", "true");
      expect(selected).toHaveFocus();
      expect(screen.getAllByRole("radio").filter((radio) => radio.tabIndex === 0))
        .toEqual([selected]);
    }
  );

  it.each([
    { key: "ArrowRight", selections: ["frosted", "solid", "refractive"] },
    { key: "ArrowDown", selections: ["frosted", "solid", "refractive"] },
    { key: "ArrowLeft", selections: ["solid", "frosted", "refractive"] },
    { key: "ArrowUp", selections: ["solid", "frosted", "refractive"] },
  ] as const)("cycles selection and focus with $key, including wrapping", async ({ key, selections }) => {
    const { setGlassTreatment } = renderPicker();
    const group = await screen.findByRole("radiogroup", { name: "Glass Treatment" });
    const radios = within(group).getAllByRole("radio");
    const expectSelection = (treatment: GlassTreatment) => {
      const selected = screen.getByTestId(`glass-treatment-option-${treatment}`);
      expect(within(group).getAllByRole("radio", { checked: true })).toEqual([selected]);
      expect(radios.filter((radio) => radio.tabIndex === 0)).toEqual([selected]);
      for (const radio of radios) {
        expect(radio).toHaveAttribute("aria-checked", String(radio === selected));
        expect(radio).toHaveAttribute("tabindex", radio === selected ? "0" : "-1");
      }
      expect(selected).toHaveFocus();
    };

    screen.getByTestId("glass-treatment-option-refractive").focus();
    expectSelection("refractive");
    for (const [index, treatment] of selections.entries()) {
      const focused = document.activeElement as HTMLElement;
      const event = createEvent.keyDown(focused, { key, cancelable: true });
      fireEvent(focused, event);
      expectSelection(treatment);
      expect(event.defaultPrevented).toBe(true);
      expect(setGlassTreatment).toHaveBeenCalledTimes(index + 1);
      expect(setGlassTreatment).toHaveBeenLastCalledWith(treatment);
    }
  });

  it.each(["{Enter}", " "])("preserves native button selection with %s", async (key) => {
    renderPicker();
    await screen.findByTestId("glass-treatment-control");
    const frosted = screen.getByTestId("glass-treatment-option-frosted");
    frosted.focus();
    await userEvent.keyboard(key);
    expect(frosted).toHaveAttribute("aria-checked", "true");
    expect(frosted).toHaveFocus();
    expect(screen.getAllByRole("radio").filter((radio) => radio.tabIndex === 0))
      .toEqual([frosted]);
  });

  it("ignores unrelated keys", async () => {
    const { setGlassTreatment } = renderPicker();
    await screen.findByTestId("glass-treatment-control");
    const refractive = screen.getByTestId("glass-treatment-option-refractive");
    refractive.focus();
    for (const key of ["Enter", " ", "a", "Tab", "Escape"]) {
      const event = createEvent.keyDown(refractive, { key, cancelable: true });
      fireEvent(refractive, event);
      expect(event.defaultPrevented).toBe(false);
      expect(refractive).toHaveAttribute("aria-checked", "true");
      expect(refractive).toHaveFocus();
      expect(screen.getAllByRole("radio").filter((radio) => radio.tabIndex === 0))
        .toEqual([refractive]);
    }
    expect(setGlassTreatment).not.toHaveBeenCalled();
  });

  it("describes the selected treatment for screen readers", async () => {
    renderPicker();
    await screen.findByTestId("glass-treatment-control");
    expect(
      screen.getByTestId("glass-treatment-option-refractive")
    ).toHaveAttribute("title", expect.stringContaining("refraction"));
    expect(
      screen.getByTestId("glass-treatment-option-frosted")
    ).toHaveAttribute("title", expect.stringContaining("blur"));
    expect(
      screen.getByTestId("glass-treatment-option-solid")
    ).toHaveAttribute("title", expect.stringContaining("Opaque"));
  });

  it("explains an accessibility override without changing the selection", async () => {
    renderPicker({
      glassTreatment: "refractive" as GlassTreatment,
      glassTreatmentEffective: "solid" as GlassTreatment,
      glassTreatmentOverridden: true,
    });
    await screen.findByTestId("glass-treatment-control");
    // The saved preference still shows as selected...
    const checked = screen
      .getAllByRole("radio")
      .filter((o) => o.getAttribute("aria-checked") === "true");
    expect(checked[0].textContent?.trim()).toBe("Refractive");
    // ...and the effective rendering is disclosed.
    expect(screen.getByText(/reduced transparency/i)).toBeInTheDocument();
  });

  it("omits the control entirely when no setter is supplied", async () => {
    render(
      <SettingsView
        mode="light"
        setMode={vi.fn()}
        guardianName="G"
        setGuardianName={vi.fn()}
        userName="U"
        setUserName={vi.fn()}
        role="R"
        setRole={vi.fn()}
        notes="N"
        setNotes={vi.fn()}
        baseColor="#111827"
        setBaseColor={vi.fn()}
        depth={0.3}
        setDepth={vi.fn()}
        fade={0.2}
        setFade={vi.fn()}
        resolved="light"
        systemPrompt="s"
        setSystemPrompt={vi.fn()}
        wallpaper={null}
        setWallpaper={vi.fn()}
        extColors={{} as never}
        setExtColors={vi.fn()}
        dashboardThreadRows={2}
        setDashboardThreadRows={vi.fn()}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("material-controls-section")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("glass-treatment-control")).toBeNull();
    // Existing material controls are unaffected.
    expect(screen.getByTestId("surface-depth-slider")).toBeInTheDocument();
  });
});
