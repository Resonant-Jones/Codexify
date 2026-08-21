// Final audit: confirm with default baseColor (no override) the canonical
// alignment still holds (i.e. the visual output uses --accent-strong which
// AppShell resolves from cfy.baseColor).
const p = require('/Users/chriscastillo/.hermes/hermes-agent/node_modules/playwright');
const fs = require('fs');

const OUT = '/Volumes/Dev_SSD/Codexify-main/.playwright-tmp';

async function setupPreset(page, mode) {
  await page.addInitScript((m) => {
    try { localStorage.setItem('cfy.themeMode', m); } catch (e) {}
  }, mode);
}

async function gotoSettings(page) {
  await page.goto('http://localhost:4321/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.click('[data-testid="settings-utility-toggle"]');
  await page.waitForTimeout(400);
  await page.locator('[role="tablist"][aria-label="Settings tabs"] [role="tab"]').first().click();
  await page.waitForTimeout(300);
}

(async () => {
  const browser = await p.chromium.launch({ headless: true, args: ['--no-sandbox'] });
  for (const mode of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await ctx.newPage();
    await setupPreset(page, mode);
    await gotoSettings(page);
    const data = await page.evaluate(() => {
      const activeTab = document.querySelector('[data-testid="settings-panel-dock"] [role="tab"][data-state="active"]');
      const themeGroup = document.querySelector('[role="group"][aria-label="Theme mode"]');
      const themeActive = themeGroup?.querySelector('[role="button"][data-state="active"]');
      const cs = window.getComputedStyle(activeTab);
      const csT = themeActive ? window.getComputedStyle(themeActive) : null;
      return {
        accentStrong: window.getComputedStyle(document.documentElement).getPropertyValue('--accent-strong'),
        accent: window.getComputedStyle(document.documentElement).getPropertyValue('--accent'),
        activeTab: {
          bg: cs.backgroundColor,
          border: cs.borderColor,
          shadow: cs.boxShadow.substring(0, 200),
          color: cs.color,
        },
        themeActive: csT ? {
          bg: csT.backgroundColor,
          border: csT.borderColor,
          shadow: csT.boxShadow.substring(0, 200),
          color: csT.color,
        } : null,
      };
    });
    console.log(`--- ${mode.toUpperCase()} (default accent) ---`);
    console.log('  --accent:', data.accent);
    console.log('  --accent-strong:', data.accentStrong);
    console.log('  Settings active tab:', JSON.stringify(data.activeTab, null, 2));
    console.log('  Theme active tab:  ', JSON.stringify(data.themeActive, null, 2));
    // Compare
    const same = (a, b) => a === b;
    console.log('  bg match:', same(data.activeTab.bg, data.themeActive?.bg));
    console.log('  border match:', same(data.activeTab.border, data.themeActive?.border));
    console.log('  shadow match:', same(data.activeTab.shadow, data.themeActive?.shadow));
    console.log('  color match:', same(data.activeTab.color, data.themeActive?.color));
    await ctx.close();
  }
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
