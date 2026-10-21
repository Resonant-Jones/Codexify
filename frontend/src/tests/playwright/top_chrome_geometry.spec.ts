import { expect, test, type Page } from "@playwright/test";

/**
 * Top chrome geometry and wallpaper-facing contrast.
 *
 * Two contracts are verified here that jsdom cannot express:
 *  1. **Geometry.** The glass dock and the utility cluster must never
 *     intersect. Comparing left/right edges is not enough — the container
 *     query at `@container codexify-pane (max-width: 850px)` restacks the
 *     chrome into a column, so the correct assertion is a true 2D
 *     bounding-box intersection test in every layout.
 *  2. **Contrast.** Foreground is sampled from the rendered backdrop behind
 *     the cluster, so the check samples the screenshot rather than assuming
 *     fixed wallpaper pixels.
 */

type Rect = { left: number; top: number; right: number; bottom: number };

const DOCK = '[data-testid="app-shell-top-nav"]';
const CLUSTER = '[data-testid="app-shell-utility-cluster"]';

function intersects(a: Rect, b: Rect): boolean {
  return !(
    a.right <= b.left ||
    b.right <= a.left ||
    a.bottom <= b.top ||
    b.bottom <= a.top
  );
}

async function rectOf(page: Page, selector: string): Promise<Rect | null> {
  const handle = await page.$(selector);
  if (!handle) return null;
  const box = await handle.boundingBox();
  if (!box) return null;
  return {
    left: box.x,
    top: box.y,
    right: box.x + box.width,
    bottom: box.y + box.height,
  };
}

async function bootShell(page: Page, path = "/chat") {
  await page.addInitScript(() => {
    window.localStorage.setItem("cfy.bootstrap.welcomeDismissed", "1");
    window.localStorage.setItem("cfy.lastView", "dashboard");
  });
  await page.goto(path);
  await page.waitForSelector(DOCK, { timeout: 30_000 });
  await page.waitForSelector(CLUSTER, { timeout: 30_000 });
}

/** Parse an rgb/rgba string into 0-255 channels. */
function parseColor(input: string): { r: number; g: number; b: number } {
  const nums = input.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
  return { r: nums[0] ?? 0, g: nums[1] ?? 0, b: nums[2] ?? 0 };
}

function srgbToLinear(c: number): number {
  const v = c / 255;
  return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

function luminance(c: { r: number; g: number; b: number }): number {
  return (
    0.2126 * srgbToLinear(c.r) +
    0.7152 * srgbToLinear(c.g) +
    0.0722 * srgbToLinear(c.b)
  );
}

function contrastRatio(
  a: { r: number; g: number; b: number },
  b: { r: number; g: number; b: number }
): number {
  const l1 = luminance(a);
  const l2 = luminance(b);
  const hi = Math.max(l1, l2);
  const lo = Math.min(l1, l2);
  return (hi + 0.05) / (lo + 0.05);
}

test.describe("top chrome geometry", () => {
  // 1024 is the desktop breakpoint minimum; 860/840 straddle the 850px
  // container-query flip between row and column layouts.
  const widths = [1024, 1280, 1440, 1920, 860, 840];

  for (const width of widths) {
    test(`dock and utility cluster never intersect at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await bootShell(page);

      // The reported worst case is the dock fully expanded on hover.
      await page.hover(DOCK);
      await page.waitForTimeout(300);

      const dock = await rectOf(page, DOCK);
      const cluster = await rectOf(page, CLUSTER);
      expect(dock, "glass dock should be measurable").not.toBeNull();
      expect(cluster, "utility cluster should be measurable").not.toBeNull();

      const overlapping = intersects(dock!, cluster!);
      // Report the measured gap so a failure is diagnosable.
      const gap = cluster!.left - dock!.right;
      test.info().annotations.push({
        type: "geometry",
        description: `width=${width} gap=${gap.toFixed(1)} overlapping=${overlapping}`,
      });
      expect(
        overlapping,
        `dock and utility cluster overlap at ${width}px (gap ${gap.toFixed(1)}px)`
      ).toBe(false);
    });
  }

  test("utility cluster does not intersect the dock when collapsed", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await bootShell(page);

    const topChrome = page.locator('[data-testid="app-shell-top-chrome"]');
    await topChrome.hover();
    await topChrome.dispatchEvent("pointerleave");
    // Wait past the auto-collapse cooldown.
    await page.waitForTimeout(2500);

    const dock = await rectOf(page, DOCK);
    const cluster = await rectOf(page, CLUSTER);
    if (!dock || !cluster) return; // collapsed cluster may detach entirely
    expect(intersects(dock, cluster)).toBe(false);
  });
});

test.describe("utility cluster contrast over wallpaper", () => {
  test("foreground reaches every utility control", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await bootShell(page);

    const cluster = page.locator(CLUSTER);
    await expect(cluster).toBeVisible();

    // The scoped token must actually be applied to the cluster subtree.
    const fg = await cluster.evaluate((el) => {
      const value = getComputedStyle(el).getPropertyValue("--top-chrome-fg");
      return value.trim();
    });
    expect(fg, "--top-chrome-fg should resolve on the cluster").not.toBe("");
    expect(fg).not.toBe("var(--text)");

    // Every glyph in the cluster must resolve to the scoped foreground.
    const mismatched = await cluster.evaluate((el) => {
      const scoped = getComputedStyle(el)
        .getPropertyValue("--top-chrome-fg")
        .trim();
      const offenders: string[] = [];
      el.querySelectorAll("button, svg").forEach((node) => {
        const testid =
          node.getAttribute("data-testid") ??
          node.getAttribute("aria-label") ??
          node.tagName;
        const color = getComputedStyle(node).color;
        // The status dot is intentionally excluded: it carries a semantic
        // status hue and must not be recolored by backdrop adaptation.
        if (testid.includes("system-status")) return;
        if (color !== scoped) {
          offenders.push(`${testid}: ${color} != ${scoped}`);
        }
      });
      return offenders;
    });
    expect(
      mismatched,
      `controls not using the scoped foreground:\n${mismatched.join("\n")}`
    ).toEqual([]);
  });

  test("cluster text meets WCAG AA against the rendered backdrop", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await bootShell(page);
    await page.waitForTimeout(600);

    const cluster = page.locator(CLUSTER);
    const box = await cluster.boundingBox();
    expect(box).not.toBeNull();

    // Measure the real rendered pixels behind the cluster.
    const shot = await page.screenshot({
      clip: { x: box!.x, y: box!.y, width: box!.width, height: box!.height },
    });
    // Sharp's PNG decode is available via the browser itself; use the page
    // to decode rather than adding a Node PNG dependency.
    const backdrop = await page.evaluate(async (b64) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      let r = 0;
      let g = 0;
      let bl = 0;
      let n = 0;
      for (let i = 0; i < data.length; i += 4) {
        r += data[i];
        g += data[i + 1];
        bl += data[i + 2];
        n += 1;
      }
      return { r: r / n, g: g / n, b: bl / n };
    }, shot.toString("base64"));

    expect(backdrop, "backdrop sample should decode").not.toBeNull();

    const foreground = await cluster.evaluate((el) => {
      const button = el.querySelector("button");
      return button ? getComputedStyle(button).color : "";
    });
    const fg = parseColor(foreground);
    const bg = backdrop!;

    const ratio = contrastRatio(fg, bg);
    test.info().annotations.push({
      type: "contrast",
      description: `fg=${foreground} bg=rgb(${bg.r.toFixed(
        0
      )},${bg.g.toFixed(0)},${bg.b.toFixed(0)}) ratio=${ratio.toFixed(2)}`,
    });
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  test("stays legible when the wallpaper cannot be sampled", async ({
    page,
  }) => {
    // Force the sampler onto its fallback path by failing every image load.
    await page.route("**/*", (route) => {
      if (route.request().resourceType() === "image") {
        return route.abort();
      }
      return route.continue();
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await bootShell(page);
    await page.waitForTimeout(800);

    const cluster = page.locator(CLUSTER);
    const scrim = await cluster.evaluate((el) => {
      const cs = getComputedStyle(el, "::before");
      return {
        background: cs.backgroundColor,
        active: getComputedStyle(el)
          .getPropertyValue("--top-chrome-scrim-active")
          .trim(),
      };
    });

    // Sampling failed, so the contrast-safe backing must be engaged.
    expect(scrim.active).toBe("1");
    expect(scrim.background).not.toBe("rgba(0, 0, 0, 0)");
    expect(scrim.background).not.toBe("transparent");
  });
});