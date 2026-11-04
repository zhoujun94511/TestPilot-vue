import { ref } from 'vue';

/** Chat 发送/流式请求的 AbortController 与 loading 状态 */
export function useChatAbort() {
  const sendLoading = ref(false);
  let activeChatAbort: AbortController | null = null;

  function abortActiveChat() {
    activeChatAbort?.abort();
    activeChatAbort = null;
  }

  function beginAbortableRequest(): AbortController {
    abortActiveChat();
    const controller = new AbortController();
    activeChatAbort = controller;
    return controller;
  }

  function isAbortError(error: unknown): boolean {
    if (activeChatAbort?.signal.aborted) return true;
    return error instanceof DOMException && error.name === 'AbortError';
  }

  return {
    sendLoading,
    abortActiveChat,
    beginAbortableRequest,
    isAbortError
  };
}
