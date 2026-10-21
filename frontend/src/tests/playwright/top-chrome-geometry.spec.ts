import { test, expect } from "@playwright/test";

/**
 * Desktop dock / utility-cluster geometry and wallpaper-facing contrast.
 *
 * Two contracts are covered here:
 *
 *  1. **Geometry.** The glass dock and the utility cluster must never
 *     intersect. The cluster renders outside the dock, directly on the
 *     wallpaper, at the far edge of the top chrome.
 *  2. **Contrast.** The cluster's backing is painted by a `::before`
 *     pseudo-element, so the cluster element itself keeps a transparent
 *     background. The foreground comes from the sampled `--top-chrome-fg`
 *     token, which is mode-derived — so it is asserted against that token
 *     rather than a hardcoded color.
 *
 * The dock auto-collapses on a delay (`DOCK_AUTO_COLLAPSE_DELAY_MS`, 900ms),
 * so the collapsed pass waits for the collapsed shell to actually appear
 * instead of re-measuring the expanded dock.
 */

const SHELL = ".codexify-shell";
const COLLAPSED = "codexify-shell--dock-collapsed";

type Box = { x: number; y: number; width: number; height: number };

/** Parse an rgb/rgba string into its channels. */
function channels(input: string): { r: number; g: number; b: number; a: number } {
  const nums = input.match(/[\d.]+/g)?.map(Number) ?? [];
  return { r: nums[0] ?? 0, g: nums[1] ?? 0, b: nums[2] ?? 0, a: nums[3] ?? 1 };
}

/** Relative luminance of an sRGB color, per WCAG 2.x. */
function luminance(input: string): number {
  const { r, g, b } = channels(input);
  const linear = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
}

/** WCAG contrast ratio between two colors. */
function contrastRatio(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Overlap area of two boxes, in CSS pixels. */
function overlapArea(a: Box, b: Box): number {
  const overlapX = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
  const overlapY = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
  return overlapX * overlapY;
}

test.describe("desktop dock and utility cluster collision", () => {
  for (const width of [1024, 1280, 1440, 1920]) {
    test(`no rectangle intersection at ${width}px in expanded and collapsed states`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/", { waitUntil: "domcontentloaded" });
      const dock = page.getByTestId("app-shell-nav-anchor");
      const cluster = page.getByTestId("app-shell-utility-cluster");
      await expect(dock).toBeVisible();
      await expect(cluster).toBeVisible();

      // Expanded state: hovering the dock keeps it expanded.
      await dock.hover();
      await page.waitForTimeout(300);
      const expandedDock = await dock.boundingBox();
      const expandedCluster = await cluster.boundingBox();
      expect(expandedDock, `dock should be measurable at ${width}px`).not.toBeNull();
      expect(expandedCluster, `cluster should be measurable at ${width}px`).not.toBeNull();
      expect(
        overlapArea(expandedDock!, expandedCluster!),
        `width=${width}, expanded, dock and utility cluster overlap`
      ).toBeLessThanOrEqual(1);

      // Collapsed state: the dock schedules its collapse on a delay, so wait
      // for the collapsed shell to appear rather than a fixed short delay that
      // would measure the expanded dock a second time.
      await page.mouse.move(width / 2, 800);
      await expect(page.locator(SHELL).first()).toHaveClass(new RegExp(COLLAPSED), {
        timeout: 5_000,
      });
      await page.waitForTimeout(300);

      const collapsedDock = await dock.boundingBox();
      expect(collapsedDock, `dock should be measurable when collapsed at ${width}px`).not.toBeNull();
      const collapsedCluster = await cluster.boundingBox();
      // The collapsed cluster is hidden (zero width, opacity 0), so it may
      // have no box at all. A hidden cluster cannot intersect the dock.
      if (collapsedCluster) {
        expect(
          overlapArea(collapsedDock!, collapsedCluster),
          `width=${width}, collapsed, dock and utility cluster overlap`
        ).toBeLessThanOrEqual(1);
      }
    });
  }
});

test("unavailable wallpaper keeps toolbar foreground readable without touching global colors", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    localStorage.setItem("cfy.wallpaper", "https://127.0.0.1:1/unavailable-wallpaper.jpg");
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const cluster = page.getByTestId("app-shell-utility-cluster");
  await expect(cluster).toBeVisible();

  // The contrast backing is painted by a `::before` pseudo-element, so the
  // cluster element keeps a transparent background of its own. Assert the
  // painted scrim and the sampled foreground token rather than a hardcoded
  // color on the host element.
  const contrast = await cluster.evaluate((el) => {
    const style = getComputedStyle(el);
    const before = getComputedStyle(el, "::before");
    return {
      clusterBackground: style.backgroundColor,
      scrim: before.backgroundColor,
      scrimActive: style.getPropertyValue("--top-chrome-scrim-active").trim(),
      foreground: style.getPropertyValue("--top-chrome-fg").trim(),
    };
  });

  expect(contrast.clusterBackground, "the cluster host must not paint its own background").toBe(
    "rgba(0, 0, 0, 0)"
  );
  expect(contrast.scrim, "the ::before backing must paint a scrim").not.toBe("rgba(0, 0, 0, 0)");
  expect(contrast.scrim, "the ::before backing must paint a scrim").not.toBe("transparent");
  expect(contrast.scrimActive, "an unavailable backdrop must still request backing").toBe("1");

  // The fallback foreground is mode-derived, so compare against the token
  // rather than pinning a literal color.
  const expected = channels(contrast.foreground);
  const foregrounds = await cluster.locator("button").evaluateAll(buttons =>
    buttons.map(button => ({
      color: getComputedStyle(button).color,
      background: getComputedStyle(button).backgroundColor,
    }))
  );
  expect(foregrounds.length).toBeGreaterThan(0);
  for (const { color } of foregrounds) {
    const actual = channels(color);
    expect(actual.r, `foreground red for ${color}`).toBe(expected.r);
    expect(actual.g, `foreground green for ${color}`).toBe(expected.g);
    expect(actual.b, `foreground blue for ${color}`).toBe(expected.b);
  }

  // With an opaque fallback scrim, the scrim itself is the effective
  // backdrop, so the sampled foreground must clear WCAG AA against it.
  const ratio = contrastRatio(contrast.foreground, contrast.scrim);
  expect(ratio, `contrast of ${contrast.foreground} against ${contrast.scrim}`).toBeGreaterThanOrEqual(
    4.5
  );
});
