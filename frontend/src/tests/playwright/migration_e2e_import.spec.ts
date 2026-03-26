import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';

type ThreadRecord = {
  id: number;
  title: string;
  last_message: string;
  project_id: number | null;
  user_id: string;
  summary: string;
  archived_at: string | null;
};

type MessageRecord = {
  id: number;
  thread_id: number;
  role: string;
  content: string;
  created_at: string;
};

test.describe('ChatGPT migration import', () => {
  test('imports and recalls a fact through post-import completion', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('cfy.lastView', 'settings');
    });

    const importedFact = 'ORCHID-POLARIS-719';
    const importedThread = {
      id: 202,
      title: 'Migration Recall Fixture',
      last_message: '',
      project_id: null,
      user_id: 'default',
      summary: 'Imported from ChatGPT',
      archived_at: null,
    } satisfies ThreadRecord;
    const recalledAnswer = `Imported fact recalled: ${importedFact}`;
    const recallQuestion = 'What is the migration recall anchor?';

    let canonicalUploadHits = 0;
    let legacyUploadHits = 0;
    let completionHits = 0;
    let completedThreadId: number | null = null;
    let nextMessageId = 2000;
    let imported = false;

    const nowIso = () => new Date().toISOString();
    const makeMessage = (
      threadId: number,
      role: string,
      content: string
    ): MessageRecord => ({
      id: nextMessageId++,
      thread_id: threadId,
      role,
      content,
      created_at: nowIso(),
    });

    const threads: ThreadRecord[] = [
      {
        id: 101,
        title: 'Seed Thread',
        last_message: 'Seed context',
        project_id: null,
        user_id: 'default',
        summary: '',
        archived_at: null,
      },
    ];

    const messagesByThread = new Map<number, MessageRecord[]>([
      [
        101,
        [
          makeMessage(101, 'user', 'Seed context'),
          makeMessage(101, 'assistant', 'Ready.'),
        ],
      ],
    ]);

    const getThread = (threadId: number) => threads.find((thread) => thread.id === threadId);
    const getMessages = (threadId: number): MessageRecord[] => {
      const current = messagesByThread.get(threadId);
      if (current) return current;
      const next: MessageRecord[] = [];
      messagesByThread.set(threadId, next);
      return next;
    };
    const appendMessage = (threadId: number, role: string, content: string): MessageRecord => {
      const message = makeMessage(threadId, role, content);
      getMessages(threadId).push(message);
      const thread = getThread(threadId);
      if (thread) {
        thread.last_message = content;
      }
      return message;
    };

    const installImportedThread = () => {
      if (threads.some((thread) => thread.id === importedThread.id)) return;
      threads.push({ ...importedThread });
      messagesByThread.set(importedThread.id, [
        makeMessage(importedThread.id, 'user', `Migration anchor code: ${importedFact}.`),
        makeMessage(importedThread.id, 'assistant', 'Imported history available for recall.'),
      ]);
      const thread = getThread(importedThread.id);
      if (thread) {
        thread.last_message = 'Imported history available for recall.';
      }
    };

    await context.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;

      if (!path.startsWith('/api/') && path !== '/upload-chatgpt-export') {
        await route.continue();
        return;
      }
      if (/\.(ts|tsx|js|jsx|css|map)$/.test(path)) {
        await route.continue();
        return;
      }

      if (path === '/upload-chatgpt-export') {
        legacyUploadHits += 1;
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Use /api/upload-chatgpt-export' }),
        });
        return;
      }

      if (path === '/api/upload-chatgpt-export') {
        expect(request.method()).toBe('POST');
        canonicalUploadHits += 1;
        imported = true;
        installImportedThread();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ threads_imported: 1, messages_imported: 2 }),
        });
        return;
      }

      if (path === '/api/health/llm') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            status: 'online',
            provider: 'local',
            model: 'test-local-model',
          }),
        });
        return;
      }

      if (path.startsWith('/api/chat/threads')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, threads }),
        });
        return;
      }

      const messagePath = path.match(/^\/api\/chat\/(\d+)\/messages$/);
      if (messagePath) {
        const threadId = Number(messagePath[1]);
        if (request.method() === 'POST') {
          const payload = request.postDataJSON() as
            | { content?: string; role?: string }
            | null;
          const role = payload?.role || 'user';
          const content = payload?.content || '';
          const message = appendMessage(threadId, role, content);
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ ok: true, message }),
          });
          return;
        }

        if (request.method() === 'GET') {
          const all = getMessages(threadId);
          const limit = Number(url.searchParams.get('limit') ?? all.length);
          const offset = Number(url.searchParams.get('offset') ?? 0);
          const start = Number.isFinite(offset) ? Math.max(0, offset) : 0;
          const size = Number.isFinite(limit) ? Math.max(1, limit) : all.length;
          const pageMessages = all.slice(start, start + size);
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              ok: true,
              total: all.length,
              messages: pageMessages,
            }),
          });
          return;
        }
      }

      const completePath = path.match(/^\/api\/chat\/(\d+)\/complete$/);
      if (completePath && request.method() === 'POST') {
        completionHits += 1;
        completedThreadId = Number(completePath[1]);
        const reply = imported && completedThreadId === importedThread.id
          ? recalledAnswer
          : 'No imported fact available.';
        appendMessage(completedThreadId, 'assistant', reply);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ task_id: `task_${completionHits}` }),
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

      if (path.startsWith('/api/projects')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ projects: [] }),
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

      if (path.startsWith('/api/chat/debug/rag-trace')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ documents: [], graph: [] }),
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

    const fixturePath = fileURLToPath(
      new URL('./fixtures/chatgpt_export_sample.json', import.meta.url)
    );
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(fixturePath);

    await page.getByRole('button', { name: 'Upload & Migrate' }).click();
    await expect(page.getByText(/Migration Successful/i)).toBeVisible();
    await expect.poll(() => canonicalUploadHits).toBe(1);
    expect(legacyUploadHits).toBe(0);

    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('heading', { name: 'Import from ChatGPT' })).toHaveCount(0);

    const guardianTab = page.getByRole('button', { name: 'Guardian' }).first();
    await expect(guardianTab).toBeVisible();
    await guardianTab.click();

    const importedThreadTile = page.locator('.thread-preview', {
      hasText: importedThread.title,
    }).first();
    await expect(importedThreadTile).toBeVisible({ timeout: 20000 });
    await importedThreadTile.click();

    const composer = page.getByPlaceholder(/Write a message/i);
    await expect(composer).toBeVisible();
    await composer.fill(recallQuestion);
    await page.getByRole('button', { name: 'Send' }).click();

    await expect.poll(() => completionHits).toBeGreaterThan(0);
    await expect.poll(() => completedThreadId).toBe(importedThread.id);
    await expect(page.getByText(recalledAnswer)).toBeVisible({ timeout: 20000 });
  });

  test('accepts large exports without size gating', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('cfy.lastView', 'settings');
    });

    let uploadHits = 0;

    await context.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;

      if (!path.startsWith('/api/') && path !== '/upload-chatgpt-export') {
        await route.continue();
        return;
      }
      if (/\.(ts|tsx|js|jsx|css|map)$/.test(path)) {
        await route.continue();
        return;
      }

      if (path === '/upload-chatgpt-export') {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Use /api/upload-chatgpt-export' }),
        });
        return;
      }

      if (path === '/api/upload-chatgpt-export') {
        uploadHits += 1;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ threads_imported: 0, messages_imported: 0 }),
        });
        return;
      }

      if (path === '/api/health/llm') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            status: 'online',
            provider: 'local',
            model: 'test-local-model',
          }),
        });
        return;
      }

      if (path.startsWith('/api/chat/threads')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, threads: [] }),
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

      if (path.startsWith('/api/projects')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ projects: [] }),
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

    const largePayload = Buffer.alloc(51 * 1024 * 1024, ' ');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'chatgpt_export_large.json',
      mimeType: 'application/json',
      buffer: largePayload,
    });

    await expect(page.getByText('chatgpt_export_large.json')).toBeVisible();
    await expect(
      page.getByText('Large ChatGPT exports are accepted.')
    ).toBeVisible();
    await expect(
      page.getByText('Export file exceeds 50MB limit.')
    ).toHaveCount(0);

    const uploadButton = page.getByRole('button', { name: 'Upload & Migrate' });
    await expect(uploadButton).toBeEnabled();
    await uploadButton.click();
    await expect.poll(() => uploadHits).toBe(1);
  });
});
