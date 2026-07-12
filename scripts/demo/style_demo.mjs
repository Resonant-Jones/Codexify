#!/usr/bin/env node
/** Apply and verify Rowan's appearance through the real Settings UI. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(path.join(root, "frontend/src/package.json"));
let chromium;
try {
  ({ chromium } = require("@playwright/test"));
} catch (error) {
  console.error("Playwright is required for demo-style; run pnpm --dir frontend/src install first");
  process.exit(1);
}
const env = {};
for (const filename of [".env.tester", ".env.demo"]) {
  const envPath = path.join(root, filename);
  if (!fs.existsSync(envPath)) continue;
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)=(.*)\s*$/);
    if (match) env[match[1]] = match[2].replace(/^['"]|['"]$/g, "");
  }
}
const preset = JSON.parse(fs.readFileSync(path.join(root, "Demo-Assets/peekaboo-demo/appearance-preset.json"), "utf8"));
const base = (process.env.DEMO_FRONTEND_BASE || env.DEMO_FRONTEND_BASE || "http://localhost:5174").replace(/\/$/, "");
const username = process.env.DEMO_USERNAME || env.DEMO_USERNAME || "rowan";
const password = process.env.DEMO_PASSWORD || env.DEMO_PASSWORD;
if (!password) throw new Error("DEMO_PASSWORD is required via .env.demo or the environment");
const proof = path.join(root, "Demo-Assets/peekaboo-demo/captures/appearance-proof.png");
fs.mkdirSync(path.dirname(proof), { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto(base, { waitUntil: "networkidle" });
await page.getByLabel("Username").fill(username);
await page.getByLabel("Password").fill(password);
await page.getByRole("button", { name: /sign in/i }).click();
await page.getByLabel("Settings").click();
await page.getByRole("tab", { name: "Appearance" }).click();
await page.getByLabel("Base color").fill(preset.baseColor);
const sliders = page.locator('input[type="range"]');
await sliders.nth(0).fill(String(Math.round(preset.depth * 100)));
await sliders.nth(1).fill(String(Math.round(preset.fade * 100)));
await sliders.nth(2).fill(String(preset.wallpaperBlurPx));
await page.locator('input[type="file"]').first().setInputFiles(path.join(root, "Demo-Assets/peekaboo-demo", preset.wallpaper));
await page.reload({ waitUntil: "networkidle" });
await page.getByLabel("Settings").click();
await page.getByRole("tab", { name: "Appearance" }).click();
if ((await page.getByLabel("Base color").inputValue()).toLowerCase() !== preset.baseColor.toLowerCase()) throw new Error("base color did not survive reload");
if (!(await page.evaluate(() => localStorage.getItem("cfy.wallpaper")))) throw new Error("wallpaper did not survive reload");
await page.screenshot({ path: proof, fullPage: true });
await browser.close();
console.log(proof);
