import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

import FrameCard from "@/components/ui/RefractiveGlassCard";
import { GLASS_TREATMENT_STORAGE_KEY } from "@/theme/glassTreatment";

const WALLPAPER =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="#888"/></svg>`
  );

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

/**
 * Count real WebGL context requests. jsdom returns null for these, so the
 * renderer takes its failure path; counting proves whether a treatment even
 * *attempted* the WebGL pipeline rather than merely hiding its output.
 */
function trackWebgl() {
  const created: string[] = [];
  const spy = vi
    .spyOn(HTMLCanvasElement.prototype, "getContext")
    .mockImplementation(function (this: HTMLCanvasElement, id: string) {
      created.push(id);
      return null;
    } as never);
  return { created, spy };
}

describe("RefractiveGlassCard treatment rendering", () => {
  it("mounts a canvas for the default refractive treatment", () => {
    const { container } = render(
      <FrameCard wallpaperUrl={WALLPAPER}>content</FrameCard>
    );
    expect(container.querySelector("canvas")).not.toBeNull();
    // Default must remain the shipped behaviour.
    expect(container.querySelector("[data-glass-treatment]")).toBeNull();
  });

  it("renders frost with uniform blur and no canvas", () => {
    const { created, spy } = trackWebgl();
    const { container } = render(
      <FrameCard wallpaperUrl={WALLPAPER} treatment="frosted">
        content
      </FrameCard>
    );
    expect(container.querySelector("canvas")).toBeNull();
    expect(
      container.querySelector("[data-glass-treatment='frosted']")
    ).not.toBeNull();
    expect(created).toEqual([]);
    spy.mockRestore();
  });

  it("renders solid with neither blur nor refraction", () => {
    const { created, spy } = trackWebgl();
    const { container } = render(
      <FrameCard wallpaperUrl={WALLPAPER} treatment="solid">
        content
      </FrameCard>
    );
    const el = container.querySelector("[data-glass-treatment='solid']") as HTMLElement;
    expect(el).not.toBeNull();
    expect(el.style.backdropFilter).toBe("none");
    expect(el.style.background).toBe("rgb(28, 28, 30)");
    expect(container.querySelector("canvas")).toBeNull();
    expect(created).toEqual([]);
    spy.mockRestore();
  });

  it("makes no WebGL attempt for frosted or solid even with a valid wallpaper", () => {
    const { created, spy } = trackWebgl();
    render(
      <FrameCard wallpaperUrl={WALLPAPER} treatment="frosted">
        a
      </FrameCard>
    );
    render(
      <FrameCard wallpaperUrl={WALLPAPER} treatment="solid">
        b
      </FrameCard>
    );
    expect(created).toEqual([]);
    spy.mockRestore();
  });

  it("still renders children in every treatment", () => {
    for (const treatment of ["refractive", "frosted", "solid"] as const) {
      const { getByText } = render(
        <FrameCard wallpaperUrl={WALLPAPER} treatment={treatment}>
          child-{treatment}
        </FrameCard>
      );
      expect(getByText(`child-${treatment}`)).toBeInTheDocument();
    }
  });

  it("renders frosted and solid even when no wallpaper is set", () => {
    for (const treatment of ["frosted", "solid"] as const) {
      const { container, getByText } = render(
        <FrameCard wallpaperUrl={null} treatment={treatment}>
          {`nowall-${treatment}`}
        </FrameCard>
      );
      expect(container.querySelector("canvas")).toBeNull();
      expect(getByText(`nowall-${treatment}`)).toBeInTheDocument();
    }
  });

  it("keeps the refractive fallback when the wallpaper cannot load", () => {
    const { container } = render(
      <FrameCard wallpaperUrl={null}>content</FrameCard>
    );
    // No wallpaper -> no refraction possible, falls back to the CSS surface.
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.textContent).toContain("content");
  });
});

describe("preference is independent of rendering", () => {
  it("does not require the preference key to render", () => {
    // The renderer is driven purely by its `treatment` prop; storage is read
    // by the shell, so a missing or malformed key cannot reach this component.
    localStorage.removeItem(GLASS_TREATMENT_STORAGE_KEY);
    const { container } = render(
      <FrameCard wallpaperUrl={WALLPAPER}>content</FrameCard>
    );
    expect(container.querySelector("canvas")).not.toBeNull();
  });
});