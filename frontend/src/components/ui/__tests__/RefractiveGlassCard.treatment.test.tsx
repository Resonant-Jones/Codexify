import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render } from "@testing-library/react";

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
  vi.unstubAllGlobals();
});

function controlWallpaperLoading() {
  const images: HTMLImageElement[] = [];
  vi.spyOn(globalThis, "Image").mockImplementation(function () {
    const image = document.createElement("img");
    images.push(image);
    return image;
  });
  return {
    images,
    load() {
      const image = images[images.length - 1];
      Object.defineProperties(image, {
        complete: { configurable: true, value: true },
        naturalWidth: { configurable: true, value: 10 },
        naturalHeight: { configurable: true, value: 10 },
      });
      image.width = 10;
      image.height = 10;
      act(() => image.dispatchEvent(new Event("load")));
    },
  };
}

/** Exercise setup and drawing without requiring a GPU in jsdom. */
function mockWebglRenderer(context: "webgl2" | "webgl") {
  const gl = {
    createShader: vi.fn(() => ({})),
    shaderSource: vi.fn(),
    compileShader: vi.fn(),
    getShaderParameter: vi.fn(() => true),
    createProgram: vi.fn(() => ({})),
    attachShader: vi.fn(),
    bindAttribLocation: vi.fn(),
    linkProgram: vi.fn(),
    getProgramParameter: vi.fn(() => true),
    createBuffer: vi.fn(() => ({})),
    bindBuffer: vi.fn(),
    bufferData: vi.fn(),
    createTexture: vi.fn(() => ({})),
    bindTexture: vi.fn(),
    texParameteri: vi.fn(),
    getUniformLocation: vi.fn(() => ({})),
    viewport: vi.fn(),
    useProgram: vi.fn(),
    enableVertexAttribArray: vi.fn(),
    vertexAttribPointer: vi.fn(),
    activeTexture: vi.fn(),
    pixelStorei: vi.fn(),
    texImage2D: vi.fn(),
    uniform1i: vi.fn(),
    uniform2f: vi.fn(),
    uniform1f: vi.fn(),
    clearColor: vi.fn(),
    clear: vi.fn(),
    drawArrays: vi.fn(),
  };
  const getContext = vi
    .spyOn(HTMLCanvasElement.prototype, "getContext")
    .mockImplementation(((id: string) => id === context ? gl : null) as never);
  const disconnect = vi.fn();
  vi.stubGlobal("ResizeObserver", class {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = disconnect;
  });
  return { gl, getContext, disconnect };
}

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
  it.each(["webgl2", "webgl"] as const)(
    "restores %s drawing after repeated treatment changes without remounting",
    (context) => {
      const wallpaper = controlWallpaperLoading();
      const { gl, getContext, disconnect } = mockWebglRenderer(context);
      const card = (treatment: "refractive" | "frosted" | "solid", intensity = 0.012) => (
        <FrameCard wallpaperUrl={WALLPAPER} treatment={treatment} intensity={intensity}>
          content
        </FrameCard>
      );
      const { container, rerender } = render(card("refractive"));
      const root = container.firstElementChild;
      expect(getContext).not.toHaveBeenCalled();
      wallpaper.load();
      expect(gl.drawArrays).toHaveBeenCalledTimes(1);

      // A renderer update while still refractive keeps the existing canvas.
      const canvas = container.querySelector("canvas");
      rerender(card("refractive", 0.02));
      expect(container.querySelector("canvas")).toBe(canvas);
      expect(gl.drawArrays).toHaveBeenCalledTimes(2);

      for (const treatments of [["frosted", "solid"], ["solid", "frosted"]] as const) {
        const requests = getContext.mock.calls.length;
        const draws = gl.drawArrays.mock.calls.length;
        const cleanups = disconnect.mock.calls.length;
        const imageCount = wallpaper.images.length;

        for (const treatment of treatments) {
          rerender(card(treatment));
          expect(container.firstElementChild).toBe(root);
          expect(root).toHaveAttribute("data-glass-treatment", treatment);
          expect(container.querySelector("canvas")).toBeNull();
          act(() => window.dispatchEvent(new Event("scroll")));
          act(() => window.dispatchEvent(new Event("resize")));
          expect(getContext).toHaveBeenCalledTimes(requests);
          expect(gl.drawArrays).toHaveBeenCalledTimes(draws);
          expect(wallpaper.images).toHaveLength(imageCount);
        }
        expect(disconnect).toHaveBeenCalledTimes(cleanups + 1);

        rerender(card("refractive"));
        expect(container.firstElementChild).toBe(root);
        expect(container.querySelector("canvas")).not.toBeNull();
        expect(getContext).toHaveBeenCalledTimes(requests);
        wallpaper.load();
        expect(getContext.mock.calls.slice(requests).map(([id]) => id)).toEqual(
          context === "webgl2" ? ["webgl2"] : ["webgl2", "webgl"]
        );
        expect(gl.drawArrays).toHaveBeenCalledTimes(draws + 1);
        act(() => window.dispatchEvent(new Event("scroll")));
        expect(gl.drawArrays).toHaveBeenCalledTimes(draws + 2);
      }
    }
  );

  it("keeps the CSS fallback when wallpaper loading fails", () => {
    const wallpaper = controlWallpaperLoading();
    const { created } = trackWebgl();
    const { container, getByText } = render(
      <FrameCard wallpaperUrl={WALLPAPER}>content</FrameCard>
    );
    act(() => wallpaper.images[0].dispatchEvent(new Event("error")));
    expect(container.querySelector("canvas")).toBeNull();
    expect(getByText("content")).toBeInTheDocument();
    expect(created).toEqual([]);
  });

  it("keeps the CSS fallback when a loaded wallpaper has no WebGL support", () => {
    const wallpaper = controlWallpaperLoading();
    const { created } = trackWebgl();
    const { container, getByText } = render(
      <FrameCard wallpaperUrl={WALLPAPER}>content</FrameCard>
    );
    wallpaper.load();
    expect(created).toEqual(["webgl2", "webgl", "experimental-webgl"]);
    expect(container.querySelector("canvas")).toBeNull();
    expect(getByText("content")).toBeInTheDocument();
    expect((container.firstElementChild as HTMLElement).style.backdropFilter).toBe(
      "blur(12px) saturate(120%)"
    );
  });

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
