import { expect, test } from '@playwright/test';

test.describe('应用壳层', () => {
  test('侧栏、面包屑与页面 kicker', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('complementary', { name: /主导航|Main navigation/i })).toBeVisible();
    await expect(page.getByRole('navigation', { name: /面包屑|Breadcrumb/i })).toBeVisible();
    const kicker = page.locator('text=/AI 测试控制台|Enterprise AI Testing/i').first();
    if (page.viewportSize() && page.viewportSize()!.width >= 1200) {
      await expect(kicker).toBeHidden();
    } else {
      await expect(kicker).toBeVisible();
    }
  });

  test('侧栏折叠按钮可点击', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');
    const collapse = page.getByRole('button', { name: /收起侧边栏|展开侧边栏|Collapse|Expand sidebar/i });
    await expect(collapse).toBeVisible();
    await collapse.click();
    await collapse.click();
  });

  test('窄屏抽屉菜单', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/chat');
    const openMenu = page.getByRole('button', { name: /打开菜单|Open menu/i });
    await expect(openMenu).toBeVisible();
    await openMenu.click();
    await expect(
      page.getByRole('complementary', { name: /主导航|Main navigation/i }).getByRole('link', {
        name: /总览|Dashboard/i
      })
    ).toBeVisible();
    await page.getByRole('button', { name: /关闭菜单|Close menu/i }).click();
    await expect(openMenu).toBeVisible();
  });

  test('主题切换更新 data-theme', async ({ page }) => {
    await page.goto('/');
    const html = page.locator('html');
    const before = await html.getAttribute('data-theme');
    await page.getByRole('button', { name: /Switch to Dark|Switch to Light|深色|浅色/i }).click();
    const after = await html.getAttribute('data-theme');
    expect(after).not.toBe(before);
  });
});

test.describe('关键页面壳', () => {
  test('Chat  composer 与 Markdown 容器', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.locator('form label').filter({ hasText: /^(Message|输入消息)$/ })).toBeVisible();
    await expect(page.getByText(/^Sessions$|^会话列表$/)).toBeVisible();
  });

  test('Config 分类侧栏', async ({ page }) => {
    await page.goto('/config');
    await expect(page.getByText(/^Categories$|^配置分类$/)).toBeVisible();
  });

  test('Cases 管理表格工具栏', async ({ page }) => {
    await page.goto('/cases/manage');
    await expect(page.getByText(/搜索与筛选|Search & filters/i)).toBeVisible();
  });

  test('侧栏切换模块时 Shell 与 Tab 同步', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/documents/history');
    await expect(page.getByRole('tab', { name: /需求历史|Requirement History/i })).toHaveAttribute(
      'aria-selected',
      'true'
    );

    await page.getByRole('complementary').getByRole('link', { name: /知识库|Knowledge Base/i }).click();
    await expect(page).toHaveURL(/\/knowledge\/upload/);
    await expect(page.getByRole('tab', { name: /知识库上传|Knowledge Upload/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /需求历史|Requirement History/i })).toHaveCount(0);
  });
});
