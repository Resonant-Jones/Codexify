// Final alignment check: scroll Theme selector into view and compare
const p = require('/Users/chriscastillo/.hermes/hermes-agent/node_modules/playwright');

(async () => {
  const browser = await p.chromium.launch({ headless: true, args: ['--no-sandbox'] });
  for (const mode of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await ctx.newPage();
    await page.addInitScript((m) => {
      try {
        localStorage.setItem('cfy.themeMode', m);
        localStorage.setItem('cfy.baseColor', '#0ea5e9');
      } catch (e) {}
    }, mode);
    await page.goto('http://localhost:4321/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(400);
    await page.click('[data-testid="settings-utility-toggle"]');
    await page.waitForTimeout(400);
    await page.locator('[role="tablist"][aria-label="Settings tabs"] [role="tab"]').first().click();
    await page.waitForTimeout(300);

    // Scroll the theme selector into view inside the settings panel scroll container
    const scrolled = await page.evaluate(() => {
      const grp = document.querySelector('[role="group"][aria-label="Theme mode"]');
      if (!grp) return false;
      grp.scrollIntoView({ block: 'center' });
      return true;
    });
    await page.waitForTimeout(300);

    const data = await page.evaluate(() => {
      const activeTab = document.querySelector('[data-testid="settings-panel-dock"] [role="tab"][data-state="active"]');
      const themeActive = document.querySelector('[role="group"][aria-label="Theme mode"] button[data-state="active"]');
      if (!activeTab) return { error: 'no active tab' };
      const cs = window.getComputedStyle(activeTab);
      const result = {
        activeTab: {
          bg: cs.backgroundColor,
          border: cs.borderColor,
          shadow: cs.boxShadow.substring(0, 200),
          color: cs.color,
        },
        themeActive: null,
      };
      if (themeActive) {
        const csT = window.getComputedStyle(themeActive);
        result.themeActive = {
          bg: csT.backgroundColor,
          border: csT.borderColor,
          shadow: csT.boxShadow.substring(0, 200),
          color: csT.color,
        };
      }
      return result;
    });
    console.log(`--- ${mode.toUpperCase()} (cfy.baseColor=#0ea5e9) ---`);
    console.log('  scrolled Theme into view:', scrolled);
    console.log('  Settings active tab:', JSON.stringify(data.activeTab, null, 2));
    console.log('  Theme active tab:  ', JSON.stringify(data.themeActive, null, 2));
    if (data.activeTab && data.themeActive) {
      const same = (a, b) => a === b;
      console.log('  bg match:    ', same(data.activeTab.bg, data.themeActive.bg));
      console.log('  border match:', same(data.activeTab.border, data.themeActive.border));
      console.log('  shadow match:', same(data.activeTab.shadow, data.themeActive.shadow));
      console.log('  color match: ', same(data.activeTab.color, data.themeActive.color));
    }
    await ctx.close();
  }
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
