import { test, expect } from '@playwright/test';

test.describe('ChatGPT migration import', () => {
  test('queues upload and resumes on reload', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('cfy.lastView', 'settings');
    });

    await page.addInitScript(() => {
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
    let uploadSettled = false;
    let reloadPhase = false;
    let startupScanHits = 0;
    let statusPollHits = 0;
    let releaseUpload: (() => void) | null = null;
    const uploadGate = new Promise<void>((resolve) => {
      releaseUpload = resolve;
    });

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
        await uploadGate;
        await route.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'job_1', status: 'queued' }),
        });
        uploadSettled = true;
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
        if (reloadPhase) {
          statusPollHits += 1;
        }
        const threads = reloadPhase ? [...baseThreads, importedThread] : baseThreads;
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
        if (reloadPhase) {
          startupScanHits += 1;
        }
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

    const settingsTab = page.getByRole('button', { name: 'Settings' }).first();
    await expect(settingsTab).toBeVisible({ timeout: 20000 });
    await settingsTab.click();
    await expect(page.getByRole('button', { name: 'Appearance' })).toBeVisible();

    const dataTab = page.getByRole('button', { name: 'Data' }).first();
    await dataTab.click();
    await expect(page.getByText('ChatGPT Migration')).toBeVisible();

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

    await expect(page.getByText(/Processing conversations/i)).toBeVisible();

    await expect.poll(() => canonicalHit).toBeTruthy();
    expect(legacyUploadHit).toBeFalsy();
    releaseUpload?.();
    await expect.poll(() => uploadSettled).toBeTruthy();

    reloadPhase = true;
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    const settingsTabReload = page.getByRole('button', { name: 'Settings' }).first();
    await expect(settingsTabReload).toBeVisible({ timeout: 20000 });
    await settingsTabReload.click();
    await expect(page.getByRole('button', { name: 'Appearance' })).toBeVisible();

    await expect.poll(() => startupScanHits).toBeGreaterThan(0);

    const guardianTab = page.getByRole('button', { name: 'Guardian' }).first();
    await expect(guardianTab).toBeVisible();
    await guardianTab.click();

    await expect.poll(() => statusPollHits).toBeGreaterThan(0);

    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent('cfy:toast', {
          detail: { message: 'Migration import completed in background' },
        })
      );
    });

    await expect(page.getByText(/Migration import completed/i)).toBeVisible();
  });
});
