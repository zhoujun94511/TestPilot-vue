import { expect, test } from '@playwright/test';
import { installMinimalAppMocks } from './helpers/mock-api';

test.describe('表格与模块 Tab', () => {
  test('Documents 子 Tab 可切换', async ({ page }) => {
    await page.goto('/documents/manage');
    await expect(page.getByRole('tab', { name: /需求文档上传|Upload/i })).toBeVisible();
    await page.getByRole('tab', { name: /需求历史|Requirement History/i }).click();
    await expect(page).toHaveURL(/\/documents\/history/);
    await expect(page.getByPlaceholder(/搜索需求编号|Search by req id/i)).toBeVisible();
  });

  test('Documents 历史：类型与优先级筛选', async ({ page }) => {
    await page.goto('/documents/history');
    const typeSelect = page.locator('select').filter({
      has: page.locator('option[value="functional"]')
    });
    const prioritySelect = page.locator('select').filter({
      has: page.locator('option[value="P0"]')
    });
    await expect(typeSelect).toBeVisible();
    await expect(prioritySelect).toBeVisible();
  });
});

test.describe('Chat Markdown（API 桩）', () => {
  test.beforeEach(async ({ page }) => {
    await installMinimalAppMocks(page);
  });

  test('渲染表格与代码块复制按钮', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/chat');
    await page.waitForResponse(
      (response) => response.url().includes('/chat/sessions') && response.ok(),
      { timeout: 15_000 }
    );
    const sessionRow = page.locator('.grid.gap-2').getByText('E2E Markdown', { exact: true });
    await expect(sessionRow).toBeVisible({ timeout: 10_000 });
    await sessionRow.click();
    await expect(page.locator('.chat-rich-content__table')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('.chat-rich-content__table-hint')).toBeVisible();
    await expect(page.locator('.chat-rich-content__copy-btn[data-role="copy-code"]').first()).toBeVisible();
    await expect(page.locator('.chat-rich-content__code code')).toContainText('console.log');
  });

  test('深浅色下 Markdown 文本色随主题切换', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/chat');
    await page.waitForResponse(
      (response) => response.url().includes('/chat/sessions') && response.ok(),
      { timeout: 15_000 }
    );
    await page.locator('.grid.gap-2').getByText('E2E Markdown', { exact: true }).click();
    const richRoot = page.locator('.chat-rich-content').first();
    await expect(richRoot).toBeVisible({ timeout: 15_000 });

    const readThemeText = () =>
      richRoot.evaluate((el) => {
        const root = el as HTMLElement;
        const node = (root.querySelector('h3, p, td, th, li') ?? root) as HTMLElement;
        return {
          theme: document.documentElement.getAttribute('data-theme'),
          color: getComputedStyle(node).color,
          tokenFg: getComputedStyle(document.documentElement).getPropertyValue('--tp-foreground').trim()
        };
      });

    const light = await readThemeText();
    expect(light.theme).toBe('light');
    expect(light.color).toMatch(/^rgb/);
    expect(light.tokenFg.length).toBeGreaterThan(0);

    await page.getByRole('button', { name: /Switch to Dark|Switch to Light|深色|浅色/i }).click();
    const dark = await readThemeText();
    expect(dark.theme).toBe('dark');
    expect(dark.color).not.toBe(light.color);
  });
});
