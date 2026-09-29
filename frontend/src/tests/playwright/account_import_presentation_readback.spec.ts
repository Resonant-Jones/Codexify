import { expect, test } from '@playwright/test';

const sourceTitle = 'Axis Import Materialization Probe';
const userSentinel = 'CODEXIFY_IMPORT_USER_SENTINEL_20260923';
const assistantSentinel = 'CODEXIFY_IMPORT_ASSISTANT_SENTINEL_20260923';

test.use({ viewport: { width: 1440, height: 900 } });

test('renders and rehydrates a canonically imported conversation', async ({ page, context }) => {
  const threadId = Number(process.env.CODEXIFY_IMPORT_PRESENTATION_THREAD_ID);
  const projectId = Number(process.env.CODEXIFY_IMPORT_PRESENTATION_PROJECT_ID);
  const expectedTitle = process.env.CODEXIFY_IMPORT_PRESENTATION_TITLE;
  const messageIds = (process.env.CODEXIFY_IMPORT_PRESENTATION_MESSAGE_IDS ?? '')
    .split(',').map((value) => Number(value.trim()));
  if (!Number.isInteger(threadId) || threadId <= 0 || !Number.isInteger(projectId) || projectId <= 0 ||
      messageIds.length !== 2 || messageIds.some((id) => !Number.isInteger(id) || id <= 0) || !expectedTitle) {
    throw new Error('Read-only imported thread/project/message preflight IDs and title are required');
  }
  expect(expectedTitle).toBe(sourceTitle);
  expect((await context.storageState()).origins).toEqual([]);

  const forbiddenRequests: string[] = [];
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    const method = request.method();
    if (
      /\/complete(?:\/|$)/.test(path) ||
      /\/search(?:\/|$)/.test(path) ||
      /^\/(?:api\/)?imports\//.test(path) ||
      (method !== 'GET' && method !== 'OPTIONS' && /\/(?:api\/)?chat\/(?:threads|\d+\/messages)/.test(path))
    ) {
      forbiddenRequests.push(`${method} ${path}`);
    }
  });

  const projectsResponsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === '/api/projects' && response.request().method() === 'GET'
  );
  await page.goto('/');
  const welcomeEntry = page.getByRole('button', { name: 'Enter Codexify' });
  if (await welcomeEntry.isVisible().catch(() => false)) await welcomeEntry.click();
  const projectsResponse = await projectsResponsePromise;
  expect(projectsResponse.status()).toBe(200);
  const projectsBody = await projectsResponse.json();
  const projects = Array.isArray(projectsBody) ? projectsBody : projectsBody.projects;
  expect(projects).toEqual(expect.arrayContaining([
    expect.objectContaining({ id: projectId, user_id: 'local', name: 'Imports' }),
  ]));

  const sidebarToggle = page.getByRole('button', { name: /Show sidebar|Hide sidebar/ }).first();
  await expect(sidebarToggle).toBeVisible();
  if ((await sidebarToggle.getAttribute('aria-label')) === 'Show sidebar') await sidebarToggle.click();

  await page.getByTestId('sidebar-projects-tab').click();
  const projectTile = page.locator('.project-tile', { hasText: 'Imports' });
  await expect(projectTile).toBeVisible();
  const scopedListResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === '/api/chat/threads' &&
      url.searchParams.get('project_id') === String(projectId) &&
      response.request().method() === 'GET';
  });
  await projectTile.click();
  const scopedListResponse = await scopedListResponsePromise;
  expect(scopedListResponse.status()).toBe(200);
  const scopedRequestUrl = new URL(scopedListResponse.url());
  expect(scopedRequestUrl.searchParams.has('origin_system')).toBe(false);
  const scopedList = await scopedListResponse.json();
  expect(scopedList.threads).toEqual(expect.arrayContaining([
    expect.objectContaining({ id: threadId, project_id: projectId, origin_system: 'openai', title: sourceTitle }),
  ]));
  expect(scopedList.has_more).toBe(false);
  await expect(page.getByTestId('sidebar-threads-tab')).toHaveAttribute('data-state', 'active');
  await page.getByTestId('sidebar-projects-tab').click();
  await expect(projectTile).toHaveAttribute('aria-pressed', 'true');
  await page.getByTestId('sidebar-threads-tab').click();
  await expect(page.getByRole('toolbar', { name: 'Canonical conversation origin filter' })
    .getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'true');

  const tile = page.getByTestId(`thread-tile-${threadId}`);
  await expect(tile).toBeVisible();
  await expect(tile).toContainText(sourceTitle);
  const messageResponsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `/api/chat/${threadId}/messages` &&
    response.request().method() === 'GET'
  );
  await tile.click();
  await expect(page).toHaveURL(new RegExp(`/chat/${threadId}$`));
  await expect(page.getByTestId(`thread-row-${threadId}`).getByRole('button', { name: 'Thread actions' })).toBeVisible();

  const assertMessageResponse = async (response: Awaited<typeof messageResponsePromise>) => {
    expect(response.status()).toBe(200);
    const url = new URL(response.url());
    expect(url.searchParams.get('offset')).toBe('0');
    expect(Number(url.searchParams.get('limit'))).toBeGreaterThanOrEqual(2);
    const body = await response.json();
    expect(body.total).toBe(2);
    expect(body.messages).toHaveLength(2);
    expect(body.messages.map((message: { id: number; role: string }) => [message.id, message.role])).toEqual([
      [messageIds[0], 'user'],
      [messageIds[1], 'assistant'],
    ]);
    expect(body.messages[0].content).toContain(userSentinel);
    expect(body.messages[1].content).toContain(assistantSentinel);
  };
  const messageResponse = await messageResponsePromise;
  await assertMessageResponse(messageResponse);

  const renderedMessages = page.getByTestId('chat-message');
  await expect(renderedMessages).toHaveCount(2);
  await expect(renderedMessages.nth(0)).toContainText(userSentinel);
  await expect(renderedMessages.nth(0).getByTestId('chat-user-message-bubble')).toBeVisible();
  await expect(renderedMessages.nth(1)).toContainText(assistantSentinel);
  await expect(renderedMessages.nth(1).getByTestId('chat-user-message-bubble')).toHaveCount(0);

  const reloadMessageResponsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `/api/chat/${threadId}/messages` &&
    response.request().method() === 'GET'
  );
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(new RegExp(`/chat/${threadId}$`));
  const reloadMessageResponse = await reloadMessageResponsePromise;
  await assertMessageResponse(reloadMessageResponse);
  await expect(page.getByTestId('chat-message')).toHaveCount(2);
  await expect(page.getByTestId('chat-message').nth(0)).toContainText(userSentinel);
  await expect(page.getByTestId('chat-message').nth(1)).toContainText(assistantSentinel);
  await expect(page.getByTestId(`thread-tile-${threadId}`)).toContainText(sourceTitle);
  expect(forbiddenRequests).toEqual([]);

  console.log('account-import presentation receipt', JSON.stringify({
    thread_id: threadId,
    project_id: projectId,
    project_api_status: projectsResponse.status(),
    scoped_list_status: scopedListResponse.status(),
    selected_project_id: projectId,
    origin_filter: 'all',
    selected_route: new URL(page.url()).pathname,
    message_ids: messageIds,
    message_query: new URL(messageResponse.url()).search,
    rendered_message_count: 2,
    reload_message_status: reloadMessageResponse.status(),
    reload_message_query: new URL(reloadMessageResponse.url()).search,
    forbidden_request_count: forbiddenRequests.length,
  }));
});
