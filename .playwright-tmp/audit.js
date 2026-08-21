// Audit script: compare Settings dock active tab vs Theme selector
// across light and dark modes, with a blue accent to match the reference.
const p = require('/Users/chriscastillo/.hermes/hermes-agent/node_modules/playwright');
const fs = require('fs');

const OUT = '/Volumes/Dev_SSD/Codexify-main/.playwright-tmp';

async function setupPreset(page, mode) {
  await page.addInitScript((m) => {
    try {
      localStorage.setItem('cfy.themeMode', m);
      // Default baseColor is #6B7280 (slate gray). The Task Spec reference
      // uses a blue accent (sky-500). Set the canonical blue to match the
      // accepted reference so we can see the canonical aligned treatment.
      localStorage.setItem('cfy.baseColor', '#0ea5e9'); // sky-500 family
    } catch (e) {}
  }, mode);
}

async function gotoSettings(page) {
  // Hard reload to clear cached state from previous mode
  await page.goto('http://localhost:4321/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.click('[data-testid="settings-utility-toggle"]');
  await page.waitForTimeout(400);
  await page.locator('[role="tablist"][aria-label="Settings tabs"] [role="tab"]').first().click();
  await page.waitForTimeout(300);
}

async function inspect(page, label) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(150);

  const data = await page.evaluate(() => {
    const out = {};

    const dock = document.querySelector('[data-testid="settings-panel-dock"]');
    if (dock) {
      out.dock = {
        ariaLabel: dock.getAttribute('aria-label'),
        role: dock.getAttribute('role'),
        cls: dock.className,
        style: dock.getAttribute('style') || '',
      };
    }
    const rail = dock?.querySelector('.glass-pill');
    if (rail) {
      out.rail = {
        cls: rail.className,
        style: rail.getAttribute('style') || '',
      };
    }
    const tabs = dock ? [...dock.querySelectorAll('[role="tab"]')] : [];
    out.tabs = tabs.map((t) => ({
      label: (t.textContent || '').trim(),
      ariaSelected: t.getAttribute('aria-selected'),
      dataState: t.getAttribute('data-state'),
      cls: t.className,
      inlineStyle: t.getAttribute('style') || '',
      computed: (() => {
        const cs = window.getComputedStyle(t);
        return {
          background: cs.background,
          backgroundColor: cs.backgroundColor,
          backgroundImage: cs.backgroundImage,
          color: cs.color,
          border: cs.border,
          borderColor: cs.borderColor,
          borderWidth: cs.borderWidth,
          borderRadius: cs.borderRadius,
          boxShadow: cs.boxShadow,
          padding: cs.padding,
          font: cs.font,
          fontWeight: cs.fontWeight,
          fontSize: cs.fontSize,
          opacity: cs.opacity,
        };
      })(),
    }));

    // Theme selector (SegmentedThemeControl) — uses <button>, look for
    // group role with the right label, OR fall back to "Light/System/Dark"
    // buttons inside the Appearance section.
    const themeSelector = (() => {
      const groups = [...document.querySelectorAll('[role="group"]')];
      const found = groups.find((g) => g.getAttribute('aria-label') === 'Theme mode');
      return found;
    })();
    if (themeSelector) {
      out.themeSelector = {
        cls: themeSelector.className,
        ariaLabel: themeSelector.getAttribute('aria-label'),
      };
      const themeTabs = [...themeSelector.querySelectorAll('[role="button"]')];
      out.themeTabs = themeTabs.map((t) => ({
        label: (t.textContent || '').trim(),
        dataState: t.getAttribute('data-state'),
        ariaPressed: t.getAttribute('aria-pressed'),
        cls: t.className,
        computed: (() => {
          const cs = window.getComputedStyle(t);
          return {
            background: cs.background,
            backgroundColor: cs.backgroundColor,
            backgroundImage: cs.backgroundImage,
            color: cs.color,
            border: cs.border,
            borderColor: cs.borderColor,
            borderWidth: cs.borderWidth,
            borderRadius: cs.borderRadius,
            boxShadow: cs.boxShadow,
            padding: cs.padding,
            font: cs.font,
            fontWeight: cs.fontWeight,
            fontSize: cs.fontSize,
            opacity: cs.opacity,
          };
        })(),
      }));
    } else {
      // Try locating by container
      const allButtons = [...document.querySelectorAll('button')];
      const themeBtns = allButtons.filter((b) => {
        const txt = (b.textContent || '').trim();
        return txt === 'Light' || txt === 'System' || txt === 'Dark';
      });
      if (themeBtns.length > 0) {
        out.themeTabs = themeBtns.map((t) => ({
          label: (t.textContent || '').trim(),
          dataState: t.getAttribute('data-state'),
          ariaPressed: t.getAttribute('aria-pressed'),
          ariaLabel: t.getAttribute('aria-label'),
          cls: t.className,
          computed: (() => {
            const cs = window.getComputedStyle(t);
            return {
              background: cs.background,
              backgroundColor: cs.backgroundColor,
              backgroundImage: cs.backgroundImage,
              color: cs.color,
              border: cs.border,
              borderColor: cs.borderColor,
              borderWidth: cs.borderWidth,
              borderRadius: cs.borderRadius,
              boxShadow: cs.boxShadow,
              padding: cs.padding,
              font: cs.font,
              fontWeight: cs.fontWeight,
              fontSize: cs.fontSize,
              opacity: cs.opacity,
            };
          })(),
        }));
      }
    }

    out.htmlClass = document.documentElement.className;
    out.bodyBg = window.getComputedStyle(document.body).backgroundColor;

    const glassPills = [...document.querySelectorAll('.glass-pill')];
    out.glassPillsCount = glassPills.length;
    out.settingsGlassPillComputed = (() => {
      if (!rail) return null;
      const cs = window.getComputedStyle(rail);
      return {
        background: cs.background,
        backgroundColor: cs.backgroundColor,
        backgroundImage: cs.backgroundImage,
        border: cs.border,
        borderColor: cs.borderColor,
        borderRadius: cs.borderRadius,
        boxShadow: cs.boxShadow,
        backdropFilter: cs.backdropFilter,
        position: cs.position,
      };
    })();

    out.settingsGlassPillBefore = (() => {
      if (!rail) return null;
      const cs = window.getComputedStyle(rail, '::before');
      return {
        content: cs.content,
        boxShadow: cs.boxShadow,
        position: cs.position,
        inset: cs.inset,
        pointerEvents: cs.pointerEvents,
      };
    })();

    return out;
  });

  const dock = await page.locator('[data-testid="settings-panel-dock"]').first();
  if (await dock.count()) {
    try { await dock.screenshot({ path: `${OUT}/${label}_dock.png` }); } catch (e) {}
  }
  const themeSel = page.locator('[role="group"][aria-label="Theme mode"]').first();
  if (await themeSel.count()) {
    try { await themeSel.screenshot({ path: `${OUT}/${label}_theme.png` }); } catch (e) {}
  }
  // Try a fallback screenshot: the Appearance section's first segment
  // (Light/System/Dark buttons)
  try {
    const lightBtn = page.locator('button:has-text("Light")').first();
    if (await lightBtn.count()) {
      const bbox = await lightBtn.evaluate((el) => {
        const group = el.closest('[role="group"]') || el.parentElement;
        if (!group) return null;
        const r = group.getBoundingClientRect();
        return { x: r.x, y: r.y, width: r.width, height: r.height };
      });
      if (bbox) {
        await page.screenshot({
          path: `${OUT}/${label}_theme.png`,
          clip: { x: bbox.x - 6, y: bbox.y - 6, width: bbox.width + 12, height: bbox.height + 12 },
        });
      }
    }
  } catch (e) {}
  await page.screenshot({ path: `${OUT}/${label}_fullpage.png`, fullPage: true });

  fs.writeFileSync(`${OUT}/${label}.json`, JSON.stringify(data, null, 2));
  return data;
}

function summarize(label, data) {
  console.log(`--- ${label} ---`);
  console.log('htmlClass:', data.htmlClass);
  console.log('dock.style (first 200):', (data.dock?.style || '').substring(0, 200));
  console.log('rail.cls:', data.rail?.cls);
  console.log('glassPillsCount:', data.glassPillsCount);
  if (data.settingsGlassPillComputed) {
    const c = data.settingsGlassPillComputed;
    console.log('rail background-image:', c.backgroundImage);
    console.log('rail border-color:', c.borderColor);
    console.log('rail box-shadow:', c.boxShadow);
    console.log('rail backdrop-filter:', c.backdropFilter);
  }
  if (data.settingsGlassPillBefore) {
    console.log('rail::before box-shadow:', data.settingsGlassPillBefore.boxShadow);
  }
  console.log('dock tabs:');
  for (const t of data.tabs) {
    const c = t.computed;
    console.log(`  - ${t.label} (${t.dataState})`);
    console.log(`     background: ${c.backgroundColor}`);
    console.log(`     background-image: ${c.backgroundImage}`);
    console.log(`     color: ${c.color}`);
    console.log(`     border: ${c.border}`);
    console.log(`     box-shadow: ${c.boxShadow.substring(0, 200)}`);
  }
  console.log('theme tabs:');
  for (const t of (data.themeTabs || [])) {
    const c = t.computed;
    console.log(`  - ${t.label} (${t.dataState})`);
    console.log(`     background: ${c.backgroundColor}`);
    console.log(`     background-image: ${c.backgroundImage}`);
    console.log(`     color: ${c.color}`);
    console.log(`     border: ${c.border}`);
    console.log(`     box-shadow: ${c.boxShadow.substring(0, 200)}`);
  }
}

(async () => {
  const browser = await p.chromium.launch({ headless: true, args: ['--no-sandbox'] });

  // ---------------- LIGHT MODE ----------------
  {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await ctx.newPage();
    await setupPreset(page, 'light');
    await gotoSettings(page);
    const light = await inspect(page, 'light');
    summarize('LIGHT', light);
    await ctx.close();
  }

  // ---------------- DARK MODE ----------------
  {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await ctx.newPage();
    await setupPreset(page, 'dark');
    await gotoSettings(page);
    const dark = await inspect(page, 'dark');
    summarize('DARK', dark);
    await ctx.close();
  }

  await browser.close();
  console.log('AUDIT DONE');
})().catch((e) => { console.error('ERR', e); process.exit(1); });
