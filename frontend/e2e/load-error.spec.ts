import { expect, test, type Page, type Route } from '@playwright/test';

function jsonOk(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ success: true, data: body })
  };
}

async function installKnowledgeListFailure(page: Page) {
  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(jsonOk({ enable_vector_store: true, experimental_actions_enabled: false }));
      return;
    }

    if (url.includes('/knowledge/list')) {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ success: false, message: 'Backend unavailable (e2e)' })
      });
      return;
    }

    if (url.includes('/knowledge/stats')) {
      await route.fulfill(jsonOk({ total_files: 0, total_chunks: 0, categories: [] }));
      return;
    }

    await route.fulfill(jsonOk({}));
  });
}

test.describe('加载失败态', () => {
  test('Knowledge 列表 API 失败时显示错误与重试，而非空表文案', async ({ page }) => {
    await installKnowledgeListFailure(page);
    await page.goto('/knowledge/files');

    await expect(page.getByText(/Load failed|加载失败/i).first()).toBeVisible();
    await expect(page.getByText(/Backend unavailable \(e2e\)/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /重试|Retry/i })).toBeVisible();
  });
});
