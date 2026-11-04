import { expect, test, type Route } from '@playwright/test';

test.describe('API 错误文案 i18n', () => {
  test('无业务 message 的 500 不展示 Axios 英文', async ({ page }) => {
    await page.route('**/api/stats/network**', async (route: Route) => {
      await route.fulfill({ status: 500, body: '' });
    });
    await page.route('**/api/stats/logs**', async (route: Route) => {
      await route.fulfill({ status: 500, body: '' });
    });

    await page.goto('/');
    await page.waitForTimeout(800);

    await expect(page.locator('body')).not.toContainText('Request failed with status code 500');
    await expect(page.getByText(/服务暂时不可用|Service temporarily unavailable/i).first()).toBeVisible({
      timeout: 15_000
    });
  });
});
