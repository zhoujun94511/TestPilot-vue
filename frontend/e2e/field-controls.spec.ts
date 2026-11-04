import { expect, test } from '@playwright/test';
import type { Page, Route } from '@playwright/test';

function jsonRoute(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ success: true, data: body })
  };
}

async function installConfigAiModelMocks(page: Page) {
  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(jsonRoute({ enable_vector_store: true, experimental_actions_enabled: false }));
      return;
    }

    if (url.includes('/config/categories')) {
      await route.fulfill(
        jsonRoute({
          categories: [{ id: 'ai_model', name: 'AI Model', priority: 1 }]
        })
      );
      return;
    }

    if (url.includes('/config/ai_model')) {
      await route.fulfill(
        jsonRoute({
          configs: [
            {
              key: 'OPENAI_API_KEY',
              value: '',
              value_type: 'password',
              inputKind: 'password',
              category: 'ai_model'
            },
            {
              key: 'DEFAULT_COMPANY',
              value: 'OPENAI',
              value_type: 'select',
              inputKind: 'select',
              category: 'ai_model',
              options: [{ label: 'OpenAI', value: 'OPENAI' }]
            }
          ]
        })
      );
      return;
    }

    await route.continue();
  });
}

test.describe('field-control 视觉回归', () => {
  test('Config API Key 输入框背景与边框可见', async ({ page }) => {
    await installConfigAiModelMocks(page);
    await page.goto('/config');
    await page.waitForResponse((r) => r.url().includes('/config/categories') && r.ok(), { timeout: 15_000 });

    const apiKeyInput = page.locator('input[type="password"]').first();
    await expect(apiKeyInput).toBeVisible({ timeout: 10_000 });

    const styles = await apiKeyInput.evaluate((el) => {
      const node = el as HTMLInputElement;
      const computed = getComputedStyle(node);
      return {
        backgroundColor: computed.backgroundColor,
        borderTopWidth: computed.borderTopWidth,
        borderTopStyle: computed.borderTopStyle
      };
    });

    expect(styles.backgroundColor).not.toBe('rgba(0, 0, 0, 0)');
    expect(styles.backgroundColor).not.toBe('transparent');
    expect(Number.parseFloat(styles.borderTopWidth)).toBeGreaterThan(0);
    expect(styles.borderTopStyle).not.toBe('none');
  });
});
