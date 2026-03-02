import { test, expect } from '@playwright/test';

test.describe('Sidebar project context persistence', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('keeps project selected after thread selection', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('cfy.lastView', 'guardian');
    });

    const projects = [{ id: 'proj-1', name: 'Apex', icon: 'P' }];
    const threads = [
      { id: 101, title: 'Apex Thread', lastMessage: 'Hello', project_id: 'proj-1' },
      { id: 102, title: 'Loose Thread', lastMessage: 'Loose', project_id: null },
    ];

    await page.route('**/api/projects**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ projects }),
      });
    });

    await page.route('**/api/chat/threads**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ threads }),
      });
    });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const guardianTab = page.getByRole('button', { name: 'Guardian' }).first();
    if (await guardianTab.isVisible().catch(() => false)) {
      await guardianTab.click();
    }

    const sidebarToggle = page.getByRole('button', { name: /Show sidebar|Hide sidebar/ }).first();
    await expect(sidebarToggle).toBeVisible();

    if ((await sidebarToggle.getAttribute('aria-label')) === 'Show sidebar') {
      await sidebarToggle.click();
    }

    const drawer = page.locator('[data-testid="mobile-sidebar-drawer"]');
    await expect(drawer).toBeVisible();

    const threadsTab = drawer.getByTestId('sidebar-threads-tab');
    await threadsTab.click();
    await expect(threadsTab).toHaveAttribute('data-state', 'active');

    const searchInput = drawer.getByTestId('sidebar-search-input');
    await expect(searchInput).toBeVisible();
    const searchBox = await searchInput.boundingBox();
    expect(searchBox).not.toBeNull();
    if (!searchBox) throw new Error('Sidebar search input bounding box is null');
    expect(searchBox.height).toBeGreaterThanOrEqual(40);

    const panelBox = await drawer.boundingBox();
    expect(panelBox).not.toBeNull();
    if (!panelBox) throw new Error('Sidebar drawer bounding box is null');

    const threadTile = drawer.locator('.thread-preview', { hasText: 'Apex Thread' });
    await expect(threadTile).toBeVisible();
    const threadTileBox = await threadTile.first().boundingBox();
    expect(threadTileBox).not.toBeNull();
    if (!threadTileBox) throw new Error('Thread tile bounding box is null');
    expect(threadTileBox.x + threadTileBox.width).toBeLessThanOrEqual(panelBox.x + panelBox.width + 1);

    await drawer.getByTestId('sidebar-projects-tab').click();

    const projectTile = drawer.locator('.project-tile', { hasText: 'Apex' });
    await expect(projectTile).toBeVisible();
    const projectTileBox = await projectTile.first().boundingBox();
    expect(projectTileBox).not.toBeNull();
    if (!projectTileBox) throw new Error('Project tile bounding box is null');
    expect(Math.abs(threadTileBox.height - projectTileBox.height)).toBeLessThanOrEqual(2);
    expect(projectTileBox.x + projectTileBox.width).toBeLessThanOrEqual(panelBox.x + panelBox.width + 1);
    await projectTile.click();

    await threadsTab.click();
    await expect(threadsTab).toHaveAttribute('data-state', 'active');
    await threadTile.click();

    await expect(drawer.locator('.thread-preview')).not.toHaveCount(0);

    await drawer.getByTestId('sidebar-projects-tab').click();
    await expect(drawer.locator('.project-tile--active', { hasText: 'Apex' })).toBeVisible();
  });
});
