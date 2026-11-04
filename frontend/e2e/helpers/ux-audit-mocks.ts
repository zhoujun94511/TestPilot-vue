import type { Page, Route } from '@playwright/test';

function jsonOk(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ success: true, data: body })
  };
}

function jsonFail(status: number, message: string) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify({ success: false, message })
  };
}

/** 文档管理：单条长描述，用于 Tooltip / 截断回归 */
export async function installDocumentsManageMocks(page: Page) {
  const longDescription =
    'E2E_LONG_DESCRIPTION_' +
    '这是一段用于验证 Tooltip 与截断样式的超长说明文字，应在悬停时出现完整浮层。'.repeat(3);

  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(jsonOk({ enable_vector_store: true, experimental_actions_enabled: false }));
      return;
    }

    if (url.includes('/documents/list')) {
      await route.fulfill(
        jsonOk({
          documents: [
            {
              id: 1,
              document_key: 'e2e-doc-1',
              filename: 'e2e-requirements.md',
              file_type: 'markdown',
              analysis_status: 'completed',
              status: 'completed',
              description: longDescription,
              updated_time: new Date().toISOString()
            }
          ],
          pagination: { page: 1, per_page: 10, total: 1, pages: 1, has_prev: false, has_next: false },
          total: 1
        })
      );
      return;
    }

    await route.fulfill(jsonOk({}));
  });

  return { longDescription };
}

/** 配置中心：分类加载失败 → 顶栏 backend hint */
export async function installConfigCategoriesFailure(page: Page) {
  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(jsonOk({ enable_vector_store: true, experimental_actions_enabled: false }));
      return;
    }

    if (url.includes('/config/categories')) {
      await route.fulfill(jsonFail(503, 'Backend unavailable (e2e-config)'));
      return;
    }

    await route.fulfill(jsonOk({}));
  });
}

/** Chat：会话列表失败 → 顶栏 backend hint */
export async function installChatSessionsFailure(page: Page) {
  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(jsonOk({ enable_vector_store: true, experimental_actions_enabled: false }));
      return;
    }

    if (url.includes('/chat/config')) {
      await route.fulfill(
        jsonOk({
          company: 'TestPilot',
          default_model: 'mock',
          capabilities: { supports_knowledge: true, supports_streaming: false }
        })
      );
      return;
    }

    if (url.includes('/chat/sessions')) {
      await route.fulfill(jsonFail(503, 'Backend unavailable (e2e-chat)'));
      return;
    }

    if (url.includes('/chat/templates') || url.includes('/chat/suggestions')) {
      await route.fulfill(jsonOk({ templates: [], suggestions: [] }));
      return;
    }

    await route.fulfill(jsonOk({}));
  });
}

/** 总览：核心接口失败 → 顶栏 partial 错误，系统区块不重复大块错误 */
export async function installDashboardPartialFailure(page: Page) {
  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(jsonOk({ enable_vector_store: true, experimental_actions_enabled: false }));
      return;
    }

    if (
      url.includes('/stats/overview')
      || url.includes('/stats/health')
      || url.includes('/stats/system-status')
      || url.includes('/stats/recent-activities')
    ) {
      await route.fulfill(jsonFail(500, 'Dashboard partial failure (e2e)'));
      return;
    }

    if (
      url.includes('/stats/performance')
      || url.includes('/stats/usage')
      || url.includes('/stats/tokens')
      || url.includes('/stats/network')
      || url.includes('/stats/logs')
    ) {
      await route.fulfill(
        jsonOk({
          summary: {},
          category_distribution: {},
          by_model: [],
          distribution: {},
          interfaces: []
        })
      );
      return;
    }

    await route.fulfill(jsonOk({}));
  });
}
