import { computed, ref, type Ref } from 'vue';
import {
  generateChatSessionTitle,
  listChatSessions,
  type ChatSessionRecord,
  type ChatSessionTitleSource
} from '@/api/chat';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';

export interface ChatSessionPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export interface UseChatSessionsOptions {
  defaultSessionTitle: () => string;
  loadSessionsFailedMessage: () => string;
  currentSessionId: Ref<string>;
  currentSessionTitle: Ref<string>;
  /** 选中会话（含加载历史等）；loadSessions 自动选中时 reloadHistory 通常为 false */
  selectSession: (sessionId: string, reloadHistory?: boolean) => Promise<void>;
  resetConversation: () => void;
  /** 静默刷新失败且需 Toast 时调用 */
  onSilentLoadError?: (message: string) => void;
  shouldNotifySilentError?: () => boolean;
  perPage?: number;
}

export function useChatSessions(options: UseChatSessionsOptions) {
  const sessions = ref<ChatSessionRecord[]>([]);
  const sessionLoading = ref(false);
  const sessionError = ref('');
  const sessionPagination = ref<ChatSessionPagination>({
    page: 1,
    per_page: options.perPage ?? 10,
    total: 0,
    pages: 0,
    has_prev: false,
    has_next: false
  });

  let loadSessionsRequestSeq = 0;

  const sessionTotalCount = computed(() => sessionPagination.value.total || sessions.value.length);

  function findSessionTitle(sessionId: string) {
    return sessions.value.find((item) => item.session_id === sessionId)?.title || options.defaultSessionTitle();
  }

  function ensureSessionVisible(sessionId: string, title: string) {
    if (!sessionId) return;
    const index = sessions.value.findIndex((item) => item.session_id === sessionId);
    if (index >= 0) {
      const current = sessions.value[index];
      sessions.value[index] = {
        ...current,
        title: title || current.title || options.defaultSessionTitle(),
        last_activity: new Date().toISOString()
      };
    } else {
      sessions.value = [
        {
          session_id: sessionId,
          title: title || options.defaultSessionTitle(),
          last_activity: new Date().toISOString(),
          message_count: 0,
          total_tokens: 0
        },
        ...sessions.value
      ];
    }
    sessionPagination.value.total = Math.max(sessionPagination.value.total || 0, sessions.value.length);
  }

  async function loadSessions(selectFirstIfNeeded = true, page = sessionPagination.value.page || 1, silent = false) {
    const requestSeq = ++loadSessionsRequestSeq;
    try {
      if (!silent) {
        sessionLoading.value = true;
        sessionError.value = '';
      }
      const response = await listChatSessions({ page, per_page: sessionPagination.value.per_page });
      if (requestSeq !== loadSessionsRequestSeq) return;
      sessions.value = response.sessions;
      sessionPagination.value = response.pagination;

      const current = sessions.value.find((item) => item.session_id === options.currentSessionId.value);
      if (current) {
        options.currentSessionTitle.value = current.title;
      } else if (silent) {
        ensureSessionVisible(options.currentSessionId.value, options.currentSessionTitle.value);
      }

      if (!options.currentSessionId.value && selectFirstIfNeeded && sessions.value.length > 0) {
        await options.selectSession(sessions.value[0].session_id, false);
      } else if (
        options.currentSessionId.value
        && !sessions.value.some((item) => item.session_id === options.currentSessionId.value)
      ) {
        if (selectFirstIfNeeded) {
          if (sessions.value.length > 0) {
            await options.selectSession(sessions.value[0].session_id, false);
          } else {
            options.currentSessionId.value = '';
            options.currentSessionTitle.value = options.defaultSessionTitle();
            options.resetConversation();
          }
        }
      }
    } catch (error) {
      if (requestSeq !== loadSessionsRequestSeq) return;
      const message = getUserFacingErrorMessage(error, options.loadSessionsFailedMessage());
      if (!silent) {
        sessionError.value = message;
      } else if (options.shouldNotifySilentError?.() !== false && options.onSilentLoadError) {
        options.onSilentLoadError(message);
      }
    } finally {
      if (!silent && requestSeq === loadSessionsRequestSeq) {
        sessionLoading.value = false;
      }
    }
  }

  function applySessionTitle(sessionId: string, title: string, titleSource: ChatSessionTitleSource) {
    const index = sessions.value.findIndex((item) => item.session_id === sessionId);
    if (index >= 0) {
      sessions.value[index] = { ...sessions.value[index], title, title_source: titleSource };
    }
    if (options.currentSessionId.value === sessionId) {
      options.currentSessionTitle.value = title;
    }
  }

  const pendingTitleRequests = new Set<string>();

  /** 标题未定的会话在回复完成后请求一次标题；失败不提示，下次回复后再试 */
  async function requestSessionTitle(sessionId: string) {
    if (!sessionId || pendingTitleRequests.has(sessionId)) return;
    if (sessions.value.find((item) => item.session_id === sessionId)?.title_source) return;
    pendingTitleRequests.add(sessionId);
    try {
      const record = await generateChatSessionTitle(sessionId);
      const local = sessions.value.find((item) => item.session_id === sessionId);
      // 等标题期间用户手动改了名，以手动名称为准
      if (local?.title_source === 'manual') return;
      if (record?.title_source) applySessionTitle(sessionId, record.title, record.title_source);
    } catch {
      // 标题生成失败不影响对话
    } finally {
      pendingTitleRequests.delete(sessionId);
    }
  }

  async function changeSessionPage(page: number) {
    if (page < 1 || page > (sessionPagination.value.pages || 1)) return;
    await loadSessions(false, page);
  }

  return {
    sessions,
    sessionLoading,
    sessionError,
    sessionPagination,
    sessionTotalCount,
    loadSessions,
    changeSessionPage,
    findSessionTitle,
    ensureSessionVisible,
    applySessionTitle,
    requestSessionTitle
  };
}
