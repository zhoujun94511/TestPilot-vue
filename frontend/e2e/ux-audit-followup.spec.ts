import { expect, test } from '@playwright/test';
import {
  installChatSessionsFailure,
  installConfigCategoriesFailure,
  installDashboardPartialFailure,
  installDocumentsManageMocks
} from './helpers/ux-audit-mocks';

test.describe('UX 审计后续 · 壳层与提示', () => {
  test('子 Tab 页（面包屑≥2）窄屏也不显示 kicker', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/documents/manage');
    await expect(page.getByText(/^AI 测试控制台$|^Enterprise AI Testing$/i)).toHaveCount(0);

    await page.goto('/');
    await expect(page.getByText(/^AI 测试控制台$|^Enterprise AI Testing$/i).first()).toBeVisible();
  });

  test('配置分类加载失败时显示 backend hint', async ({ page }) => {
    await installConfigCategoriesFailure(page);
    await page.goto('/config');
    await expect(
      page.getByText(/无法加载配置分类|If categories fail to load/i)
    ).toBeVisible();
  });

  test('Chat 会话列表失败时显示 backend hint', async ({ page }) => {
    await installChatSessionsFailure(page);
    await page.goto('/chat');
    await expect(
      page.getByText(/会话列表加载失败|If sessions fail to load/i)
    ).toBeVisible();
  });

  test('总览 partial 错误时页面仅保留顶栏一处重试', async ({ page }) => {
    await installDashboardPartialFailure(page);
    await page.goto('/');
    await expect(page.getByText(/部分数据加载失败|partial/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /^重试$|^Retry$/i })).toHaveCount(1);
  });
});

test.describe('UX 审计后续 · Tooltip', () => {
  test('文档描述截断悬停显示 Tooltip', async ({ page }) => {
    const { longDescription } = await installDocumentsManageMocks(page);
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/documents/manage');

    await expect(page.getByText('e2e-requirements.md', { exact: true })).toBeVisible();
    const trigger = page.locator('table tbody').getByText('E2E_LONG_DESCRIPTION_', { exact: false });
    await trigger.hover();
    await expect(page.getByRole('tooltip')).toContainText('E2E_LONG_DESCRIPTION_', { timeout: 8000 });
  });
});
