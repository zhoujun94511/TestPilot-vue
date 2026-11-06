import { ref, type Ref } from 'vue';
import { getChatHistory, type ChatMessageRecord } from '@/api/chat';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import type { ChatSessionPagination } from '@/composables/useChatSessions';

export interface UseChatHistoryOptions<TMessage> {
  messages: Ref<TMessage[]>;
  perPage?: number;
  loadHistoryFailedMessage: () => string;
  normalizeMessages: (records: ChatMessageRecord[]) => TMessage[];
  resolveSessionTitle: (sessionId: string) => string;
  updateSessionTitle: (title: string) => void;
  onLoaded?: (payload: { sessionId: string; messages: TMessage[] }) => void | Promise<void>;
  onEmptyHistory?: () => void;
  onLoadFailed?: (message: string) => void;
}

export function useChatHistory<TMessage>(options: UseChatHistoryOptions<TMessage>) {
  const historyLoading = ref(false);
  const historyError = ref('');
  const historyPagination = ref<ChatSessionPagination>({
    page: 1,
    per_page: options.perPage ?? 50,
    total: 0,
    pages: 0,
    has_prev: false,
    has_next: false
  });

  let loadHistoryRequestSeq = 0;

  async function loadHistory(sessionId: string, page: number | 'last' = historyPagination.value.page || 1) {
    const requestSeq = ++loadHistoryRequestSeq;
    try {
      historyLoading.value = true;
      historyError.value = '';
      const response = await getChatHistory(sessionId, { page, per_page: historyPagination.value.per_page });
      if (requestSeq !== loadHistoryRequestSeq) return;
      options.messages.value = options.normalizeMessages(response.messages);
      historyPagination.value = response.pagination;
      options.updateSessionTitle(options.resolveSessionTitle(sessionId));
      if (!options.messages.value.length) {
        options.onEmptyHistory?.();
      }
      await options.onLoaded?.({ sessionId, messages: options.messages.value });
    } catch (error) {
      if (requestSeq !== loadHistoryRequestSeq) return;
      const message = getUserFacingErrorMessage(error, options.loadHistoryFailedMessage());
      historyError.value = message;
      options.onLoadFailed?.(message);
    } finally {
      if (requestSeq === loadHistoryRequestSeq) {
        historyLoading.value = false;
      }
    }
  }

  async function reloadCurrentHistory(currentSessionId: string) {
    if (!currentSessionId) return;
    await loadHistory(currentSessionId, historyPagination.value.page);
  }

  async function changeHistoryPage(currentSessionId: string, page: number) {
    if (!currentSessionId) return;
    if (page < 1 || page > (historyPagination.value.pages || 1)) return;
    await loadHistory(currentSessionId, page);
  }

  function resetHistoryPage() {
    historyPagination.value.page = 1;
  }

  /** 只刷新分页信息（总条数、页数），不替换当前消息列表；用于发送后同步计数。 */
  async function refreshHistoryPagination(sessionId: string) {
    if (!sessionId) return;
    try {
      const response = await getChatHistory(sessionId, {
        page: historyPagination.value.page || 1,
        per_page: historyPagination.value.per_page
      });
      historyPagination.value = response.pagination;
    } catch {
      // 计数同步失败不影响对话本身，保留旧值即可
    }
  }

  return {
    historyLoading,
    historyError,
    historyPagination,
    loadHistory,
    reloadCurrentHistory,
    changeHistoryPage,
    refreshHistoryPagination,
    resetHistoryPage
  };
}
