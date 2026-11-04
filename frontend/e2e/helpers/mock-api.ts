import type { Page, Route } from '@playwright/test';

function jsonRoute(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ success: true, data: body })
  };
}

/** 壳层与 Chat 页最小 API 桩，便于无后端冒烟 Markdown / 表格渲染 */
export async function installMinimalAppMocks(page: Page) {
  await page.route('**/api/**', async (route: Route) => {
    const url = route.request().url();

    if (url.includes('/stats/feature-flags')) {
      await route.fulfill(
        jsonRoute({
          enable_vector_store: true,
          experimental_actions_enabled: false
        })
      );
      return;
    }

    if (url.includes('/chat/config')) {
      await route.fulfill(
        jsonRoute({
          company: 'TestPilot',
          default_model: 'mock',
          capabilities: { supports_knowledge: true, supports_streaming: false }
        })
      );
      return;
    }

    if (url.includes('/chat/sessions')) {
      await route.fulfill(
        jsonRoute({
          sessions: [
            {
              session_id: 'e2e-session-1',
              title: 'E2E Markdown',
              message_count: 1,
              last_activity: new Date().toISOString()
            }
          ],
          pagination: { page: 1, per_page: 10, total: 1, pages: 1, has_prev: false, has_next: false },
          total: 1
        })
      );
      return;
    }

    if (url.includes('/chat/history')) {
      const markdown = [
        '### Smoke table',
        '',
        '| Col A | Col B |',
        '| --- | --- |',
        '| alpha | beta |',
        '',
        '```js',
        'console.log("e2e");',
        '```'
      ].join('\n');

      await route.fulfill(
        jsonRoute({
          session_id: 'e2e-session-1',
          messages: [
            {
              session_id: 'e2e-session-1',
              role: 'assistant',
              content: markdown,
              message_type: 'chat'
            }
          ],
          pagination: { page: 1, per_page: 50, total: 1, pages: 1, has_prev: false, has_next: false },
          total_messages: 1
        })
      );
      return;
    }

    if (url.includes('/chat/templates') || url.includes('/chat/suggestions')) {
      await route.fulfill(jsonRoute({ templates: [], suggestions: [] }));
      return;
    }

    await route.fulfill(jsonRoute({}));
  });
}
