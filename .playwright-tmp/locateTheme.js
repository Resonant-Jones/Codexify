const p = require('/Users/chriscastillo/.hermes/hermes-agent/node_modules/playwright');
(async () => {
  const browser = await p.chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    localStorage.setItem('cfy.themeMode', 'light');
    localStorage.setItem('cfy.baseColor', '#0ea5e9');
  });
  await page.goto('http://localhost:4321/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.click('[data-testid="settings-utility-toggle"]');
  await page.waitForTimeout(400);
  await page.locator('[role="tablist"][aria-label="Settings tabs"] [role="tab"]').first().click();
  await page.waitForTimeout(300);

  const data = await page.evaluate(() => {
    const out = {};
    const sel = document.querySelector('[role="group"][aria-label="Theme mode"]');
    out.themeSelectorElement = !!sel;
    out.themeSelectorHTML = sel ? sel.outerHTML.substring(0, 600) : null;

    const allButtons = [...document.querySelectorAll('button')];
    const lightBtns = allButtons.filter((b) => (b.textContent || '').trim() === 'Light');
    const darkBtns = allButtons.filter((b) => (b.textContent || '').trim() === 'Dark');
    const systemBtns = allButtons.filter((b) => (b.textContent || '').trim() === 'System');

    const enrich = (b) => {
      if (!b) return null;
      const cs = window.getComputedStyle(b);
      const parent = b.parentElement;
      return {
        cls: b.className,
        parent_cls: parent && parent.className,
        parent_role: parent && parent.getAttribute('role'),
        parent_aria_label: parent && parent.getAttribute('aria-label'),
        computed: {
          background: cs.background.substring(0, 200),
          backgroundColor: cs.backgroundColor,
          backgroundImage: cs.backgroundImage,
          color: cs.color,
          border: cs.border,
          borderColor: cs.borderColor,
          borderRadius: cs.borderRadius,
          boxShadow: cs.boxShadow.substring(0, 200),
          padding: cs.padding,
          height: cs.height,
          fontSize: cs.fontSize,
          fontWeight: cs.fontWeight,
        },
      };
    };

    return {
      themeSelectorElement: !!sel,
      themeSelectorHTML: sel ? sel.outerHTML.substring(0, 600) : null,
      lightCount: lightBtns.length,
      darkCount: darkBtns.length,
      systemCount: systemBtns.length,
      lightFirst: enrich(lightBtns[0]),
      darkFirst: enrich(darkBtns[0]),
      systemFirst: enrich(systemBtns[0]),
    };
  });
  console.log(JSON.stringify(data, null, 2));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
