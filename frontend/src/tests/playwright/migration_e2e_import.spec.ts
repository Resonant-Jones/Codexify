import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { test, expect } from '@playwright/test';

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

type ImportFixtureCase = {
  label: string;
  fixtureUrl: string;
  expectedFilename: string;
  contentMarkers: string[];
};

const IMPORT_FIXTURE_CASES: ImportFixtureCase[] = [
  {
    label: 'legacy ChatGPT export',
    fixtureUrl: './fixtures/chatgpt_export_sample.json',
    expectedFilename: 'chatgpt_export_sample.json',
    contentMarkers: ['"mapping"', 'Migration anchor code: ORCHID-POLARIS-719.'],
  },
  {
    label: 'modern sharded OpenAI export',
    fixtureUrl:
      './fixtures/openai_sharded_export/conversations__abcd.part-0001/file_0000000000000001.dat',
    expectedFilename: 'file_0000000000000001.dat',
    contentMarkers: [
      '"conversation_id": "sharded-thread"',
      '"messages"',
      'Migration anchor code: ORCHID-POLARIS-719.',
    ],
  },
];

for (const fileCount of [2, 25]) {
  test(`account-import browser sends ${fileCount} ordered multipart pairs`, async ({ page }) => {
    let received: { method: string; contentType: string; body: Buffer } | null = null;
    const receiver = createServer(async (request, response) => {
      response.setHeader('Access-Control-Allow-Origin', String(request.headers.origin ?? 'http://127.0.0.1:5173'));
      response.setHeader('Access-Control-Allow-Credentials', 'true');
      response.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-User-Id, X-API-Key, Authorization');
      response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
      if (request.method === 'OPTIONS') {
        response.statusCode = 204;
        response.end();
        return;
      }
      const chunks: Buffer[] = [];
      for await (const chunk of request) chunks.push(Buffer.from(chunk));
      if (request.url?.endsWith('/imports/openai-account/probe-job/files')) {
        received = {
          method: request.method ?? '',
          contentType: String(request.headers['content-type'] ?? ''),
          body: Buffer.concat(chunks),
        };
        response.setHeader('Content-Type', 'application/json');
        response.end(JSON.stringify({ job_id: 'probe-job', status: 'receiving', uploaded_file_count: fileCount }));
        return;
      }
      response.setHeader('Content-Type', 'application/json');
      response.end('{}');
    });
    await new Promise<void>((resolve) => receiver.listen(0, '127.0.0.1', resolve));
    const address = receiver.address();
    if (!address || typeof address === 'string') throw new Error('Receiver port unavailable');
    try {
      await page.route('**/api/**', async (route) => {
        const url = new URL(route.request().url());
        await route.continue({ url: `http://127.0.0.1:${address.port}${url.pathname}` });
      });
      await page.goto('/');
      await page.evaluate(async (count) => {
        const { uploadOpenAIAccountImportBatch } = await import(/* @vite-ignore */ '/lib/api.ts');
        const files = [
          { file: new File(['[]'], 'conversations.json', { type: 'application/json' }), relativePath: 'conversations.json' },
          { file: new File(['{}'], 'user.json', { type: 'application/json' }), relativePath: 'nested/user.json' },
        ];
        for (let index = 2; index < count; index += 1) {
          files.push({
            file: new File([new Uint8Array(750_000)], `part-${index}.dat`, { type: 'application/octet-stream' }),
            relativePath: `nested/part-${index}.dat`,
          });
        }
        await uploadOpenAIAccountImportBatch('probe-job', files);
      }, fileCount);

      expect(received).not.toBeNull();
      const { method, contentType, body } = received!;
      expect(method).toBe('POST');
      const boundary = contentType.match(/^multipart\/form-data;\s*boundary=([^;]+)$/i)?.[1];
      expect(boundary).toBeTruthy();
      const parts = body.toString('latin1').split(`--${boundary}`).slice(1, -1);
      expect(parts).toHaveLength(fileCount * 2);
      for (let index = 0; index < fileCount; index += 1) {
        const filename = index === 0 ? 'conversations.json' : index === 1 ? 'user.json' : `part-${index}.dat`;
        const relativePath = index === 0 ? filename : `nested/${filename}`;
        expect(parts[index * 2]).toContain(`name="files"; filename="${filename}"`);
        expect(parts[index * 2 + 1]).toContain('name="relative_paths"');
        expect(parts[index * 2 + 1]).toContain(`\r\n\r\n${relativePath}\r\n`);
      }
      expect(parts[0]).toContain('Content-Type: application/json');
      expect(parts[2]).toContain('Content-Type: application/json');
      if (fileCount === 25) expect(body.length).toBeGreaterThan(17_000_000);
    } finally {
      await new Promise<void>((resolve) => receiver.close(() => resolve()));
    }
  });
}

test('current account import UI stages an OpenAI batch through Guardian', async ({ page }) => {
  const fixtureRoot = mkdtempSync(join(tmpdir(), 'codexify-account-import-ui-'));
  const exportFolder = join(fixtureRoot, 'openai-export');
  mkdirSync(join(exportFolder, 'nested'), { recursive: true });
  writeFileSync(join(exportFolder, 'conversations.json'), '[]');
  writeFileSync(join(exportFolder, 'nested', 'user.json'), '{}');
  const expectedBytes = 4;
  let commitIntercepted = 0;

  try {
    await page.addInitScript(() => {
      localStorage.setItem('cfy.userName', 'local');
      localStorage.setItem('cfy.lastView', 'settings');
    });
    await page.route('**/api/imports/openai-account/*/commit', async (route) => {
      commitIntercepted += 1;
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Diagnostic probe stops after durable staging.' }),
      });
    });
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).first().click();
    await page.getByRole('tab', { name: 'Data' }).click();
    await page.getByRole('button', { name: 'Import ChatGPT history' }).click();
    await expect(page.getByRole('heading', { name: 'Import account data' })).toBeVisible();
    await expect(page.getByTestId('account-import-source-openai')).toBeChecked();

    const createResponsePromise = page.waitForResponse((response) =>
      new URL(response.url()).pathname === '/api/imports/openai-account' &&
      response.request().method() === 'POST'
    );
    const uploadResponsePromise = page.waitForResponse((response) =>
      /\/api\/imports\/openai-account\/[^/]+\/files$/.test(new URL(response.url()).pathname) &&
      response.request().method() === 'POST'
    );
    const chooserPromise = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: 'Choose Folder' }).click();
    await (await chooserPromise).setFiles(exportFolder);

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(200);
    const created = await createResponse.json();
    const jobId = String(created.job_id ?? '');
    expect(jobId).toMatch(/^[0-9a-f-]{36}$/i);
    expect(created.source_system).toBe('openai');
    expect(created.total_file_count).toBe(2);
    expect(created.total_byte_count).toBe(expectedBytes);

    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.status()).toBe(200);
    expect(new URL(uploadResponse.url()).pathname).toBe(`/api/imports/openai-account/${jobId}/files`);
    const contentType = uploadResponse.request().headers()['content-type'] ?? '';
    const boundary = contentType.match(/^multipart\/form-data;\s*boundary=([^;]+)$/i)?.[1];
    expect(boundary).toBeTruthy();
    const body = uploadResponse.request().postDataBuffer()?.toString('latin1') ?? '';
    const parts = body.split(`--${boundary}`).slice(1, -1);
    expect(parts).toHaveLength(4);
    expect(parts[0]).toContain('name="files"; filename="conversations.json"');
    expect(parts[1]).toContain('name="relative_paths"');
    expect(parts[1]).toContain('openai-export/conversations.json');
    expect(parts[2]).toContain('name="files"; filename="user.json"');
    expect(parts[3]).toContain('name="relative_paths"');
    expect(parts[3]).toContain('openai-export/nested/user.json');
    const uploaded = await uploadResponse.json();
    expect(uploaded.job_id).toBe(jobId);
    expect(uploaded.uploaded_file_count).toBe(2);
    expect(uploaded.uploaded_byte_count).toBe(expectedBytes);

    const statusResponse = await page.request.get(`/api/imports/openai-account/${jobId}`, {
      headers: { 'X-User-Id': 'local' },
    });
    expect(statusResponse.status()).toBe(200);
    const readback = await statusResponse.json();
    expect(readback.job_id).toBe(jobId);
    expect(readback.status).toBe('receiving');
    expect(readback.total_file_count).toBe(2);
    expect(readback.total_byte_count).toBe(expectedBytes);
    expect(readback.uploaded_file_count).toBe(2);
    expect(readback.uploaded_byte_count).toBe(expectedBytes);

    const dbContainer = process.env.PW_ACCOUNT_IMPORT_DB_CONTAINER;
    if (dbContainer) {
      const sql = `BEGIN READ ONLY;\nSELECT row_to_json(t)::text FROM (
        SELECT id, user_id, source_system, status, total_file_count,
               total_byte_count, uploaded_file_count, uploaded_byte_count,
               jsonb_array_length(staged_manifest::jsonb) AS manifest_count,
               (SELECT jsonb_agg(entry->>'path' ORDER BY ordinal)
                FROM jsonb_array_elements(staged_manifest::jsonb)
                  WITH ORDINALITY AS entries(entry, ordinal)) AS manifest_paths
        FROM openai_account_import_jobs WHERE id = '${jobId}'
      ) t;\nROLLBACK;\n`;
      const output = execFileSync('docker', [
        'exec', '-i', dbContainer, 'sh', '-lc',
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At',
      ], { input: sql, encoding: 'utf8' });
      const row = JSON.parse(output.split('\n').find((line) => line.startsWith('{')) ?? 'null');
      expect(row).toMatchObject({
        id: jobId,
        user_id: 'local',
        source_system: 'openai',
        status: 'receiving',
        total_file_count: 2,
        total_byte_count: expectedBytes,
        uploaded_file_count: 2,
        uploaded_byte_count: expectedBytes,
        manifest_count: 2,
        manifest_paths: [
          'openai-export/conversations.json',
          'openai-export/nested/user.json',
        ],
      });
    }
    await expect.poll(() => commitIntercepted).toBe(1);
    console.log('account-import staging receipt', JSON.stringify({
      job_id: jobId,
      observed_at: new Date().toISOString(),
      create_status: createResponse.status(),
      upload_status: uploadResponse.status(),
      readback_status: statusResponse.status(),
      files: 2,
      bytes: expectedBytes,
      database_readback: Boolean(dbContainer),
      commit_intercepted: commitIntercepted === 1,
    }));
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true });
  }
});

test('current account import UI commits a valid OpenAI export for materialization', async ({ page }) => {
  const fixtureRoot = mkdtempSync(join(tmpdir(), 'codexify-account-import-materialization-'));
  const exportFolder = join(fixtureRoot, 'openai-export');
  mkdirSync(exportFolder);
  const sourceConversationId = 'axis-import-materialization-20260923-01';
  const userMessageId = 'axis-import-user-message-20260923-01';
  const assistantMessageId = 'axis-import-assistant-message-20260923-01';
  const exportData = [{
    conversation_id: sourceConversationId,
    id: sourceConversationId,
    title: 'Axis Import Materialization Probe',
    current_node: assistantMessageId,
    create_time: 1720000000,
    update_time: 1720000001,
    mapping: {
      [userMessageId]: {
        id: userMessageId,
        parent: null,
        children: [assistantMessageId],
        message: {
          id: userMessageId,
          author: { role: 'user' },
          content: { content_type: 'text', parts: ['CODEXIFY_IMPORT_USER_SENTINEL_20260923'] },
          create_time: 1720000000,
        },
      },
      [assistantMessageId]: {
        id: assistantMessageId,
        parent: userMessageId,
        children: [],
        message: {
          id: assistantMessageId,
          author: { role: 'assistant' },
          content: { content_type: 'text', parts: ['CODEXIFY_IMPORT_ASSISTANT_SENTINEL_20260923'] },
          create_time: 1720000001,
        },
      },
    },
  }];
  const bytes = Buffer.from(JSON.stringify(exportData));
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  writeFileSync(join(exportFolder, 'conversations.json'), bytes);

  try {
    await page.addInitScript(() => {
      localStorage.setItem('cfy.userName', 'local');
      localStorage.setItem('cfy.lastView', 'settings');
    });
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).first().click();
    await page.getByRole('tab', { name: 'Data' }).click();
    await page.getByRole('button', { name: 'Import ChatGPT history' }).click();
    await expect(page.getByRole('heading', { name: 'Import account data' })).toBeVisible();
    await expect(page.getByTestId('account-import-source-openai')).toBeChecked();

    const createResponsePromise = page.waitForResponse((response) =>
      new URL(response.url()).pathname === '/api/imports/openai-account' &&
      response.request().method() === 'POST'
    );
    const uploadResponsePromise = page.waitForResponse((response) =>
      /\/api\/imports\/openai-account\/[^/]+\/files$/.test(new URL(response.url()).pathname) &&
      response.request().method() === 'POST'
    );
    const commitResponsePromise = page.waitForResponse((response) =>
      /\/api\/imports\/openai-account\/[^/]+\/commit$/.test(new URL(response.url()).pathname) &&
      response.request().method() === 'POST'
    );
    const chooserPromise = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: 'Choose Folder' }).click();
    await (await chooserPromise).setFiles(exportFolder);

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(200);
    const created = await createResponse.json();
    const jobId = String(created.job_id ?? '');
    expect(jobId).toMatch(/^[0-9a-f-]{36}$/i);
    expect(created.source_system).toBe('openai');
    expect(created.total_file_count).toBe(1);
    expect(created.total_byte_count).toBe(bytes.length);

    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.status()).toBe(200);
    expect(new URL(uploadResponse.url()).pathname).toBe(`/api/imports/openai-account/${jobId}/files`);
    const uploaded = await uploadResponse.json();
    expect(uploaded.job_id).toBe(jobId);
    expect(uploaded.uploaded_file_count).toBe(1);
    expect(uploaded.uploaded_byte_count).toBe(bytes.length);

    const commitResponse = await commitResponsePromise;
    expect(commitResponse.status()).toBe(200);
    expect(new URL(commitResponse.url()).pathname).toBe(`/api/imports/openai-account/${jobId}/commit`);
    const committed = await commitResponse.json();
    expect(committed.job_id).toBe(jobId);
    expect(committed.status).toBe('queued');
    expect(committed.queued_at).toBeTruthy();

    const statusResponse = await page.request.get(`/api/imports/openai-account/${jobId}`, {
      headers: { 'X-User-Id': 'local' },
    });
    expect(statusResponse.status()).toBe(200);
    const readback = await statusResponse.json();
    expect(readback.job_id).toBe(jobId);
    expect(readback.status).toBe('queued');
    expect(readback.uploaded_file_count).toBe(1);
    expect(readback.uploaded_byte_count).toBe(bytes.length);
    console.log('account-import materialization commit receipt', JSON.stringify({
      job_id: jobId,
      observed_at: new Date().toISOString(),
      source_conversation_id: sourceConversationId,
      source_message_ids: [userMessageId, assistantMessageId],
      relative_path: 'openai-export/conversations.json',
      file_count: 1,
      byte_count: bytes.length,
      sha256,
      create_status: createResponse.status(),
      upload_status: uploadResponse.status(),
      commit_status: commitResponse.status(),
      readback_status: statusResponse.status(),
      job_status: readback.status,
    }));
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true });
  }
});

test.describe('ChatGPT migration import', () => {
  for (const importFixture of IMPORT_FIXTURE_CASES) {
    test(`imports ${importFixture.label} and recalls a fact through post-import completion`, async ({ page, context }) => {
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
    let uploadedMultipartBody = '';
    let uploadedContentType = '';
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
        uploadedContentType = request.headers()['content-type'] ?? '';
        uploadedMultipartBody = request.postDataBuffer()?.toString('utf8') ?? '';
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
    await expect(page.getByRole('tab', { name: 'Appearance' })).toBeVisible();

    const dataTab = page.getByRole('tab', { name: 'Data' }).first();
    await dataTab.click();
    await expect(page.getByText('Migrate from ChatGPT')).toBeVisible();

    const importButton = page.getByRole('button', { name: 'Import ChatGPT history' });
    await expect(importButton).toBeVisible();
    await importButton.click();

    await expect(page.getByRole('heading', { name: 'Import account data' })).toBeVisible();

    const fixturePath = fileURLToPath(
      new URL(importFixture.fixtureUrl, import.meta.url)
    );
    const fileInput = page.locator('input[type="file"]:not([webkitdirectory])');
    await fileInput.setInputFiles(fixturePath);
    await expect(page.getByText(importFixture.expectedFilename)).toBeVisible();
    const selectedFileText = await fileInput.evaluate(async (element) => {
      const input = element as HTMLInputElement;
      return (await input.files?.item(0)?.text()) ?? '';
    });
    for (const marker of importFixture.contentMarkers) {
      expect(selectedFileText).toContain(marker);
    }

    await page.getByRole('button', { name: 'Upload & Migrate' }).click();
    await expect(page.getByText(/Migration Successful/i)).toBeVisible();
    await expect.poll(() => canonicalUploadHits).toBe(1);
    expect(legacyUploadHits).toBe(0);
    expect(uploadedContentType).toContain('multipart/form-data');
    expect(uploadedMultipartBody).toContain(`filename="${importFixture.expectedFilename}"`);

    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('heading', { name: 'Import account data' })).toHaveCount(0);

    const guardianTab = page.getByRole('button', { name: 'Guardian' }).first();
    await expect(guardianTab).toBeVisible();
    await guardianTab.click();

    const showSidebar = page.getByRole('button', { name: 'Show sidebar' });
    if (await showSidebar.isVisible()) await showSidebar.click();
    const importedThreadTile = page.getByTestId(`thread-tile-${importedThread.id}`);
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
  }

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
    await expect(page.getByRole('tab', { name: 'Appearance' })).toBeVisible();

    const dataTab = page.getByRole('tab', { name: 'Data' }).first();
    await dataTab.click();
    await expect(page.getByText('Migrate from ChatGPT')).toBeVisible();

    const importButton = page.getByRole('button', { name: 'Import ChatGPT history' });
    await expect(importButton).toBeVisible();
    await importButton.click();

    await expect(page.getByRole('heading', { name: 'Import account data' })).toBeVisible();

    const tempDir = mkdtempSync(join(tmpdir(), 'codexify-chatgpt-import-'));
    const largeFixturePath = join(tempDir, 'chatgpt_export_large.json');
    const largePayload = Buffer.alloc(51 * 1024 * 1024, ' ');
    writeFileSync(largeFixturePath, largePayload);
    const fileInput = page.locator('input[type="file"]:not([webkitdirectory])');
    try {
      await fileInput.setInputFiles(largeFixturePath);

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
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});
