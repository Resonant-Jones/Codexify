import { test, expect } from '@playwright/test';

test.describe('App Views Screenshots', () => {
  test.beforeEach(async ({ page, context }) => {
    // Clear local storage to get default state
    await context.clearCookies();
    await page.goto('/');
    // Wait for app to fully load
    await page.waitForLoadState('networkidle');
  });

  test('Dashboard view', async ({ page }) => {
    // Navigate to dashboard (home page)
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for dashboard content to load
    await page.waitForSelector('[data-testid="dashboard"], main, .grid', { timeout: 5000 }).catch(() => null);

    // Take screenshot
    await page.screenshot({ path: 'screenshots/01-dashboard.png', fullPage: true });
  });

  test('AppShell Layout', async ({ page }) => {
    // Just verify the main shell loads
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/02-appshell.png', fullPage: true });
  });

  test('Settings View', async ({ page }) => {
    // Navigate to settings - look for settings link/button
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Try to find and click settings
    const settingsLink = page
      .locator(
        'button[aria-label="Settings"], [data-testid="settings-utility-toggle"], [href*="settings"], a:has-text("Settings")'
      )
      .first();

    if (await settingsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await settingsLink.click();
      await page.waitForLoadState('networkidle');
    }

    await page.screenshot({ path: 'screenshots/03-settings.png', fullPage: true });
  });

  test('Light Theme - Dashboard', async ({ page, context }) => {
    // Set light theme
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Try to set light theme via localStorage or UI
    await context.addInitScript(() => {
      localStorage.setItem('cfy.themeMode', 'light');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/04-light-theme.png', fullPage: true });
  });

  test('Dark Theme - Dashboard', async ({ page, context }) => {
    // Set dark theme
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Try to set dark theme via localStorage or UI
    await context.addInitScript(() => {
      localStorage.setItem('cfy.themeMode', 'dark');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/05-dark-theme.png', fullPage: true });
  });
});
