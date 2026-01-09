import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ESM-safe __dirname shim
const __dirname = new URL('.', import.meta.url).pathname;

/**
 * Guardian Chat Layout Diagnostic Test
 *
 * Captures screenshots and layout telemetry to diagnose scroll/composer issues.
 * Outputs:
 *   - Full page screenshot
 *   - Element screenshot of chat panel (if found)
 *   - JSON layout report with computed styles for key containers
 */

interface LayoutMetrics {
  selector: string;
  found: boolean;
  clientHeight?: number;
  scrollHeight?: number;
  clientWidth?: number;
  scrollWidth?: number;
  computedStyles?: {
    display?: string;
    flexDirection?: string;
    flex?: string;
    flexGrow?: string;
    flexShrink?: string;
    flexBasis?: string;
    position?: string;
    overflow?: string;
    overflowX?: string;
    overflowY?: string;
    height?: string;
    minHeight?: string;
    maxHeight?: string;
    width?: string;
    minWidth?: string;
  };
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

interface LayoutReport {
  timestamp: string;
  url: string;
  viewport: { width: number; height: number };
  elements: LayoutMetrics[];
}

test.describe('Guardian Chat Layout Diagnostic', () => {
  test('capture layout telemetry and screenshots', async ({ page }) => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const screenshotDir = path.join(__dirname, '../../screenshots');
    const layoutDir = path.join(__dirname, '../../screenshots/layout');

    // Ensure directories exist
    fs.mkdirSync(screenshotDir, { recursive: true });
    fs.mkdirSync(layoutDir, { recursive: true });

    // Navigate to Guardian chat
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click on Guardian tab in navigation
    const guardianTab = page.locator('button:has-text("Guardian"), a:has-text("Guardian"), [href*="guardian"]').first();
    if (await guardianTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await guardianTab.click();
      await page.waitForLoadState('networkidle');
    }

    // Wait for the app to stabilize
    await page.waitForTimeout(2000);

    // If still no chat container, try clicking on a thread in the sidebar
    const chatContainer = page.locator('[data-testid="chat-container"]');
    let hasChatContainer = await chatContainer.count() > 0;

    if (!hasChatContainer) {
      // Look for thread items in sidebar and click one
      const threadItem = page.locator('[data-testid="thread-item"], .thread-item, [role="listitem"]').first();
      if (await threadItem.isVisible({ timeout: 2000 }).catch(() => false)) {
        await threadItem.click();
        await page.waitForTimeout(1500);
        hasChatContainer = await chatContainer.count() > 0;
      }
    }

    // Take full page screenshot
    await page.screenshot({
      path: path.join(screenshotDir, `guardian-chat__${timestamp}.png`),
      fullPage: true,
    });

    // Try to capture chat panel element screenshot
    const chatPanelSelectors = [
      '[data-testid="chat-container"]',
      '[data-debug-scroll]',
      '[role="log"]',
      '.overflow-y-auto',
    ];

    for (const selector of chatPanelSelectors) {
      const element = page.locator(selector).first();
      if (await element.count() > 0) {
        try {
          await element.screenshot({
            path: path.join(screenshotDir, `guardian-chat-panel__${timestamp}.png`),
          });
          break;
        } catch (e) {
          // Element might not be visible or have zero dimensions
        }
      }
    }

    // Collect layout metrics for key containers
    const selectorsToMeasure = [
      '#root',
      '[data-layer="panel-shell"]',
      '[data-testid="chat-container"]',
      '[data-debug-scroll]',
      // GuardianChat body wrapper (messages region)
      '.relative.flex.flex-col.flex-1.min-h-0.overflow-clip',
      // ChatView outer div
      '.flex.flex-col.h-full.min-h-0',
      // Composer textarea
      'textarea',
      // Composer rail
      '.shrink-0.z-20.mx-\\[6px\\].mt-2.rounded-\\[24px\\]',
      // Generic fallbacks
      'main',
      '[role="main"]',
    ];

    const layoutReport: LayoutReport = {
      timestamp,
      url: page.url(),
      viewport: page.viewportSize() || { width: 0, height: 0 },
      elements: [],
    };

    for (const selector of selectorsToMeasure) {
      const metrics = await page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (!el) {
          return { selector: sel, found: false };
        }

        const computed = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        return {
          selector: sel,
          found: true,
          clientHeight: (el as HTMLElement).clientHeight,
          scrollHeight: (el as HTMLElement).scrollHeight,
          clientWidth: (el as HTMLElement).clientWidth,
          scrollWidth: (el as HTMLElement).scrollWidth,
          computedStyles: {
            display: computed.display,
            flexDirection: computed.flexDirection,
            flex: computed.flex,
            flexGrow: computed.flexGrow,
            flexShrink: computed.flexShrink,
            flexBasis: computed.flexBasis,
            position: computed.position,
            overflow: computed.overflow,
            overflowX: computed.overflowX,
            overflowY: computed.overflowY,
            height: computed.height,
            minHeight: computed.minHeight,
            maxHeight: computed.maxHeight,
            width: computed.width,
            minWidth: computed.minWidth,
          },
          boundingBox: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
          },
        };
      }, selector);

      layoutReport.elements.push(metrics as LayoutMetrics);
    }

    // Also measure all ancestors of the chat container to find the flex chain
    const ancestorMetrics = await page.evaluate(() => {
      const chatContainer = document.querySelector('[data-testid="chat-container"]');
      if (!chatContainer) return [];

      const ancestors: any[] = [];
      let current = chatContainer.parentElement;
      let depth = 0;

      while (current && depth < 15) {
        const computed = window.getComputedStyle(current);
        const rect = current.getBoundingClientRect();

        // Build a useful selector description
        let selectorHint = current.tagName.toLowerCase();
        if (current.id) selectorHint += `#${current.id}`;
        if (current.className) {
          const classes = current.className.split(/\s+/).slice(0, 3).join('.');
          if (classes) selectorHint += `.${classes}`;
        }

        ancestors.push({
          selector: `ancestor[${depth}]: ${selectorHint}`,
          found: true,
          clientHeight: current.clientHeight,
          scrollHeight: current.scrollHeight,
          clientWidth: current.clientWidth,
          scrollWidth: current.scrollWidth,
          computedStyles: {
            display: computed.display,
            flexDirection: computed.flexDirection,
            flex: computed.flex,
            flexGrow: computed.flexGrow,
            flexShrink: computed.flexShrink,
            flexBasis: computed.flexBasis,
            position: computed.position,
            overflow: computed.overflow,
            overflowX: computed.overflowX,
            overflowY: computed.overflowY,
            height: computed.height,
            minHeight: computed.minHeight,
            maxHeight: computed.maxHeight,
            width: computed.width,
            minWidth: computed.minWidth,
          },
          boundingBox: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
          },
        });

        current = current.parentElement;
        depth++;
      }

      return ancestors;
    });

    layoutReport.elements.push(...ancestorMetrics);

    // Write the JSON report
    const reportPath = path.join(layoutDir, 'guardian-chat.json');
    fs.writeFileSync(reportPath, JSON.stringify(layoutReport, null, 2));

    console.log(`\n=== Guardian Chat Layout Diagnostic ===`);
    console.log(`Screenshot: screenshots/guardian-chat__${timestamp}.png`);
    console.log(`Layout report: screenshots/layout/guardian-chat.json`);
    console.log(`\nKey findings:`);

    // Quick analysis
    const chatEl = layoutReport.elements.find(e => e.selector === '[data-testid="chat-container"]');
    if (chatEl?.found) {
      const scrollable = chatEl.scrollHeight! > chatEl.clientHeight!;
      console.log(`  Chat container: ${chatEl.clientHeight}px client / ${chatEl.scrollHeight}px scroll`);
      console.log(`  Overflow-Y: ${chatEl.computedStyles?.overflowY}`);
      console.log(`  Is scrollable: ${scrollable}`);
      console.log(`  Height: ${chatEl.computedStyles?.height}`);
      console.log(`  Min-height: ${chatEl.computedStyles?.minHeight}`);
    } else {
      console.log(`  Chat container NOT FOUND`);
    }

    // Check for common issues
    for (const el of layoutReport.elements) {
      if (el.found && el.computedStyles) {
        // Flag elements with height: auto that should constrain
        if (el.computedStyles.height === 'auto' && el.computedStyles.display === 'flex') {
          console.log(`  WARNING: ${el.selector} has height:auto in flex context`);
        }
        // Flag missing min-h-0
        if (el.computedStyles.minHeight !== '0px' && el.computedStyles.flex?.includes('1')) {
          console.log(`  NOTE: ${el.selector} has flex:1 but minHeight=${el.computedStyles.minHeight}`);
        }
      }
    }

    expect(true).toBe(true); // Always pass - this is a diagnostic test
  });
});
