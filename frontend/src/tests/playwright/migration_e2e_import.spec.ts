import { test, expect } from '@playwright/test';

test.describe('ChatGPT migration import', () => {
  test('hits canonical endpoint and triggers refresh', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('cfy.lastView', 'settings');
    });

    await page.addInitScript(() => {
      (window as any).__threadsRefreshSeen = false;
      window.addEventListener('cfy:threads:refresh', () => {
        (window as any).__threadsRefreshSeen = true;
      });

      const originalFetch = window.fetch.bind(window);
      window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
        const url =
          typeof input === 'string'
            ? input
            : input instanceof URL
              ? input.toString()
              : input.url;
        if (url === '/upload-chatgpt-export') {
          return originalFetch('/api/upload-chatgpt-export', init);
        }
        if (input instanceof Request && input.url.endsWith('/upload-chatgpt-export')) {
          return originalFetch(new Request('/api/upload-chatgpt-export', input));
        }
        return originalFetch(input, init);
      };
    });

    let canonicalHit = false;
    let legacyUploadHit = false;
    let importCompleted = false;
    let threadFetches = 0;

    const baseThreads = [
      { id: 101, title: 'Seed Thread', last_message: 'Hello', project_id: null },
    ];
    const importedThread = {
      id: 202,
      title: 'Imported Thread',
      last_message: 'Imported',
      project_id: null,
    };

    await context.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;

      if (path === '/upload-chatgpt-export') {
        legacyUploadHit = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ threads_imported: 1, messages_imported: 2 }),
        });
        return;
      }

      if (path === '/api/upload-chatgpt-export') {
        expect(request.method()).toBe('POST');
        canonicalHit = true;
        importCompleted = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ threads_imported: 1, messages_imported: 2 }),
        });
        return;
      }

      if (!path.startsWith('/api/')) {
        await route.continue();
        return;
      }
      if (/\.(ts|tsx|js|jsx|css|map)$/.test(path)) {
        await route.continue();
        return;
      }

      if (path.startsWith('/api/chat/threads')) {
        threadFetches += 1;
        const threads = importCompleted
          ? [...baseThreads, importedThread]
          : baseThreads;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ threads }),
        });
        return;
      }

      if (path.startsWith('/api/projects')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ projects: [] }),
        });
        return;
      }

      if (path.startsWith('/api/connectors')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
        return;
      }

      if (path.startsWith('/api/codex/entries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
        return;
      }

      if (path.startsWith('/api/events')) {
        await route.fulfill({
          status: 200,
          headers: { 'content-type': 'text/event-stream' },
          body: 'event: ping\\ndata: {}\\n\\n',
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      });
    });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    await page.evaluate(() => {
      localStorage.setItem('cfy.lastView', 'settings');
    });
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    const dataTab = page.getByRole('button', { name: 'Data' }).first();
    await expect(dataTab).toBeVisible({ timeout: 20000 });
    await dataTab.click();

    const importButton = page.getByRole('button', { name: 'Import from ChatGPT' });
    await expect(importButton).toBeVisible();
    await importButton.click();

    await expect(page.getByRole('heading', { name: 'Import from ChatGPT' })).toBeVisible();

    const fileInput = page.locator('input[type="file"][accept=".json"]');
    await fileInput.setInputFiles({
      name: 'conversations.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({ conversations: [] })),
    });

    await page.getByRole('button', { name: 'Upload & Migrate' }).click();

    await expect(page.getByText('Migration Successful')).toBeVisible();

    await expect.poll(() => canonicalHit).toBeTruthy();
    expect(legacyUploadHit).toBeFalsy();
    await expect.poll(() => threadFetches).toBeGreaterThan(1);
    await page.waitForFunction(() => (window as any).__threadsRefreshSeen === true);

    const guardianTab = page.getByRole('button', { name: 'Guardian' }).first();
    if (await guardianTab.isVisible().catch(() => false)) {
      await guardianTab.click();
    }

    const sidebarToggle = page.getByRole('button', { name: /Show sidebar|Hide sidebar/ }).first();
    if (await sidebarToggle.isVisible().catch(() => false)) {
      const label = await sidebarToggle.getAttribute('aria-label');
      if (label === 'Show sidebar') {
        await sidebarToggle.click();
      }
    }

    const importedThreadTile = page.locator('.thread-preview', { hasText: 'Imported Thread' }).first();
    await expect(importedThreadTile).toBeVisible();
  });
});
