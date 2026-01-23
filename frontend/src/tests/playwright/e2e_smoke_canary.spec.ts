import { test, expect } from '@playwright/test';

test.describe('E2E smoke canary', () => {
  test('loads the app shell', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const guardianTab = page.getByRole('button', { name: 'Guardian' }).first();
    await expect(guardianTab).toBeVisible();
  });
});
