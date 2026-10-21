import { test, expect } from "@playwright/test";

test.describe("desktop dock and utility cluster collision", () => {
  for (const width of [1024, 1280, 1440, 1920]) {
    test(`no rectangle intersection at ${width}px in expanded and collapsed states`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/", { waitUntil: "domcontentloaded" });
      const dock = page.getByTestId("app-shell-nav-anchor");
      const cluster = page.getByTestId("app-shell-utility-cluster");
      await expect(dock).toBeVisible();
      await expect(cluster).toBeVisible();
      for (const hover of [true, false]) {
        if (hover) await dock.hover();
        else await page.mouse.move(width / 2, 800);
        await page.waitForTimeout(220);
        const a = await dock.boundingBox();
        const b = await cluster.boundingBox();
        expect(a).not.toBeNull();
        expect(b).not.toBeNull();
        if (!a || !b) continue;
        const overlapX = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
        const overlapY = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
        expect(overlapX * overlapY, `width=${width}, hovered=${hover}, overlap=${overlapX}x${overlapY}`).toBeLessThanOrEqual(1);
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
  await expect(cluster).toHaveCSS("background-color", "rgb(22, 25, 29)");
  const foregrounds = await cluster.locator("button").evaluateAll(buttons => buttons.map(button => {
    const computed = getComputedStyle(button);
    return { color: computed.color, background: computed.backgroundColor };
  }));
  expect(foregrounds.length).toBeGreaterThan(0);
  for (const { color } of foregrounds) expect(color).toBe("rgb(255, 255, 255)");
});
