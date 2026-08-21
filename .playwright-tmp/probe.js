const p = require('/Users/chriscastillo/.hermes/hermes-agent/node_modules/playwright');

(async () => {
  const browser = await p.chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => { localStorage.setItem('cfy.themeMode', 'light'); });
  await page.goto('http://localhost:4321/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.click('[data-testid="settings-utility-toggle"]');
  await page.waitForTimeout(400);
  await page.locator('[role="tablist"][aria-label="Settings tabs"] [role="tab"]').first().click();
  await page.waitForTimeout(300);

  const data = await page.evaluate(() => {
    const activeTab = document.querySelector('[data-testid="settings-panel-dock"] [role="tab"][data-state="active"]');
    if (!activeTab) return { error: 'no active tab' };
    const cs = window.getComputedStyle(activeTab);
    const dock = document.querySelector('[data-testid="settings-panel-dock"]');
    const ds = window.getComputedStyle(dock);
    const csBefore = window.getComputedStyle(activeTab, '::before');
    const csAfter = window.getComputedStyle(activeTab, '::after');
    const get = (el, p) => {
      const v = el.getPropertyValue(p);
      return v || v === '' ? v : '(empty)';
    };
    return {
      dock_pill_active_bg: ds.getPropertyValue('--pill-active-bg'),
      dock_pill_active_border: ds.getPropertyValue('--pill-active-border'),
      dock_pill_active_shadow: ds.getPropertyValue('--pill-active-shadow'),
      dock_pill_active_text: ds.getPropertyValue('--pill-active-text'),
      activeTab_bg_image: cs.backgroundImage,
      activeTab_bg_color: cs.backgroundColor,
      activeTab_color: cs.color,
      activeTab_border: cs.border,
      activeTab_borderColor: cs.borderColor,
      activeTab_borderRadius: cs.borderRadius,
      activeTab_padding: cs.padding,
      activeTab_height: cs.height,
      activeTab_font_size: cs.fontSize,
      activeTab_font_weight: cs.fontWeight,
      activeTab_box_shadow: cs.boxShadow,
      activeTab_classes: activeTab.className,
      activeTab_inline_style: activeTab.getAttribute('style'),
      activeTab_outer_html_short: activeTab.outerHTML.substring(0, 400),
      activeTab_before_bg: csBefore.background,
      activeTab_before_content: csBefore.content,
      activeTab_after_bg: csAfter.background,
      activeTab_after_content: csAfter.content,
    };
  });
  console.log(JSON.stringify(data, null, 2));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
