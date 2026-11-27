import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AppShell from "@/components/persona/layout/AppShell";
import {
  DEFAULT_GLASS_TREATMENT,
  GLASS_TREATMENT_STORAGE_KEY,
  type GlassTreatment,
} from "@/theme/glassTreatment";
import { resetAccountAppearanceFixture, setAccountAppearanceFixture } from "@/test/accountPresentationHarness";

vi.mock("@/features/settings/accountPresentation", async () => import("@/test/accountPresentationHarness"));

// Appearance tests exercise the real shell, not chat health polling. Keep
// polling requests from outliving this test environment; chat has its own suite.
vi.mock("@/features/chat/GuardianChat", () => ({
  default: () => <div data-testid="guardian-chat-mock" />,
}));

/**
 * Shell-level coverage for the Glass Treatment material axis.
 *
 * The picker itself is covered in SettingsView.test.tsx, which owns the
 * settings harness. These tests assert the shell contract: the saved
 * preference reaches the dock, survives reload, degrades safely, and never
 * disturbs the toolbar contrast safeguards merged in #875-#877.
 */
describe("Glass Treatment shell integration", () => {
  beforeEach(() => {
    resetAccountAppearanceFixture();
    localStorage.clear();
    window.localStorage.setItem("cfy.lastView", "dashboard");
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  const dock = () => screen.getByTestId("app-shell-top-nav");

  it("defaults to refractive when no preference is stored", async () => {
    render(<AppShell />);
    await waitFor(() => expect(dock()).toBeInTheDocument());
    expect(dock()).toHaveAttribute("data-glass-treatment", DEFAULT_GLASS_TREATMENT);
    expect(dock()).toHaveAttribute("data-glass-preference", DEFAULT_GLASS_TREATMENT);
    expect(dock()).toHaveAttribute("data-glass-overridden", "false");
    expect(localStorage.getItem(GLASS_TREATMENT_STORAGE_KEY)).toBeNull();
  });

  it.each(["frosted", "solid", "refractive"] as const)(
    "restores the account's %s treatment on load",
    async (treatment) => {
      setAccountAppearanceFixture({ settings: { glass_treatment: treatment } });
      render(<AppShell />);
      await waitFor(() =>
        expect(dock()).toHaveAttribute("data-glass-treatment", treatment)
      );
      expect(dock()).toHaveAttribute("data-glass-preference", treatment);
    }
  );

  it.each(["matte-v2", "", "SOLID", "1", "null"])(
    "ignores malformed legacy browser value %p when the account uses refractive",
    async (bad) => {
      localStorage.setItem(GLASS_TREATMENT_STORAGE_KEY, bad);
      render(<AppShell />);
      await waitFor(() => expect(dock()).toBeInTheDocument());
      expect(dock()).toHaveAttribute(
        "data-glass-treatment",
        DEFAULT_GLASS_TREATMENT
      );
    }
  );

  it("never overloads an existing ADR-064 appearance key", async () => {
    localStorage.setItem("cfy.surfaceDepth", "73");
    localStorage.setItem("cfy.surfaceWarmth", "-41");
    setAccountAppearanceFixture({ settings: { glass_treatment: "solid" } });
    render(<AppShell />);
    await waitFor(() =>
      expect(dock()).toHaveAttribute("data-glass-treatment", "solid")
    );
    // Reading a treatment must not disturb the other material axes.
    expect(localStorage.getItem("cfy.surfaceDepth")).toBe("73");
    expect(localStorage.getItem("cfy.surfaceWarmth")).toBe("-41");
  });

  it("keeps the utility cluster scoped contrast tokens in every treatment", async () => {
    for (const treatment of ["refractive", "frosted", "solid"] as const) {
      setAccountAppearanceFixture({ settings: { glass_treatment: treatment as GlassTreatment } });
      const view = render(<AppShell />);
      await waitFor(() =>
        expect(screen.getByTestId("app-shell-utility-cluster")).toBeInTheDocument()
      );
      // The contrast safeguard is published on the shell and inherited by the
      // utility cluster; it must survive every material choice.
      const shell = document.querySelector(".codexify-shell") as HTMLElement;
      const style = shell?.getAttribute("style") ?? "";
      expect(style).toContain("--top-chrome-fg");
      expect(style).toContain("--top-chrome-scrim");
      expect(style).toContain("--top-chrome-scrim-active");
      view.unmount();
    }
  });

  it("keeps the Workspace toggle icon-only with its tooltip in every treatment", async () => {
    for (const treatment of ["refractive", "frosted", "solid"] as const) {
      setAccountAppearanceFixture({ settings: { glass_treatment: treatment as GlassTreatment } });
      const view = render(<AppShell />);
      await waitFor(() =>
        expect(screen.getByTestId("workspace-drawer-toggle")).toBeInTheDocument()
      );
      const toggle = screen.getByTestId("workspace-drawer-toggle");
      expect(toggle).toHaveAttribute("title", "Workspace");
      expect(toggle.textContent?.trim()).toBe("");
      expect(toggle.querySelector("svg[aria-hidden='true']")).not.toBeNull();
      view.unmount();
    }
  });

  it("keeps dock and utility-cluster grid placement in every treatment", async () => {
    for (const treatment of ["frosted", "solid"] as const) {
      setAccountAppearanceFixture({ settings: { glass_treatment: treatment as GlassTreatment } });
      const view = render(<AppShell />);
      await waitFor(() =>
        expect(screen.getByTestId("app-shell-utility-cluster")).toBeInTheDocument()
      );
      // Geometry is a grid contract, not a material concern.
      expect(screen.getByTestId("app-shell-utility-cluster")).toHaveStyle({
        gridColumn: "3",
        justifySelf: "end",
      });
      expect(screen.getByTestId("app-shell-nav-anchor")).toHaveStyle({
        gridColumn: "1",
        justifySelf: "start",
      });
      view.unmount();
    }
  });

  it.each(["light", "dark"] as const)(
    "keeps collapsed solid dock transparent in %s mode",
    async (themeMode) => {
      setAccountAppearanceFixture({ settings: { glass_treatment: "solid" } });
      setAccountAppearanceFixture({ settings: { theme_mode: themeMode } });
      render(<AppShell />);
      await waitFor(() =>
        expect(dock()).toHaveAttribute("data-glass-treatment", "solid")
      );
      await waitFor(() =>
        expect(document.documentElement.classList.contains("dark")).toBe(
          themeMode === "dark"
        )
      );

      const shell = document.querySelector(".codexify-shell") as HTMLElement;
      shell.classList.add("codexify-shell--dock-collapsed");

      expect(window.getComputedStyle(dock()).backgroundColor).toBe(
        "rgba(0, 0, 0, 0)"
      );
    }
  );

  it.each(["refractive", "frosted", "solid"] as const)(
    "keeps global text/icon tokens mode-derived and unchanged under %s",
    async (treatment) => {
      setAccountAppearanceFixture({ settings: { glass_treatment: treatment as GlassTreatment } });
      const view = render(<AppShell />);
      await waitFor(() =>
        expect(dock()).toHaveAttribute("data-glass-treatment", treatment)
      );
      const shell = document.querySelector(".codexify-shell") as HTMLElement;
      const style = shell?.getAttribute("style") ?? "";
      const text = style.match(/--text:\s*([^;]+);/)?.[1]?.trim();
      const icon = style.match(/--icon:\s*([^;]+);/)?.[1]?.trim();

      // Still mode-derived literals, and identical to the no-treatment case.
      expect(text).toMatch(/^#(ffffff|111827)$/);
      expect(icon).toBe(text);
      expect(style).toContain("--text-on-accent:");
      view.unmount();
    }
  );

  it("does not change the global token values across treatments", async () => {
    const capture = async (treatment: string) => {
      setAccountAppearanceFixture({ settings: { glass_treatment: treatment as GlassTreatment } });
      const view = render(<AppShell />);
      await waitFor(() =>
        expect(dock()).toHaveAttribute("data-glass-treatment", treatment)
      );
      const shell = document.querySelector(".codexify-shell") as HTMLElement;
      const style = shell?.getAttribute("style") ?? "";
      view.unmount();
      return {
        text: style.match(/--text:\s*([^;]+);/)?.[1]?.trim(),
        muted: style.match(/--muted:\s*([^;]+);/)?.[1]?.trim(),
        onAccent: style.match(/--text-on-accent:\s*([^;]+);/)?.[1]?.trim(),
      };
    };

    const base = await capture("refractive");
    expect(await capture("frosted")).toEqual(base);
    expect(await capture("solid")).toEqual(base);
  });
});
