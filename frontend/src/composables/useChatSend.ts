import { nextTick, type Ref } from 'vue';
import { createChatSession, getChatConfig, sendChatMessage } from '@/api/chat';
import { isModelInitError, resolveSendErrorMessage } from '@/composables/chat/chatSendErrors';
import { runChatStream } from '@/composables/useChatStreamRunner';

/** 消息发送来源：智能建议始终走对话通道，不触发实验工具编排。 */
export type ChatSendSource = 'composer' | 'quick_reply';

export interface ChatSendDisplayMessage {
  key: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_time?: string | null;
  pending?: boolean;
  tokens_used?: number;
  model_name?: string;
}

export interface ChatSendInvokeOptions {
  source?: ChatSendSource;
}

export interface UseChatSendOptions {
  t: (key: string) => string;
  draftMessage: Ref<string>;
  messages: Ref<ChatSendDisplayMessage[]>;
  currentSessionId: Ref<string>;
  currentSessionTitle: Ref<string>;
  chatConfig: Ref<Awaited<ReturnType<typeof getChatConfig>> | null>;
  pendingAssistantKey: Ref<string>;
  suggestedQuestions: Ref<string[]>;
  streamEnabled: Ref<boolean>;
  smartReplyEnabled: Ref<boolean>;
  messageCounter: Ref<number>;
  autoScrollEnabled: Ref<boolean>;
  sendLoading: Ref<boolean>;
  abortActiveChat: () => void;
  beginAbortableRequest: () => AbortController;
  isAbortError: (error: unknown) => boolean;
  resetPendingAction: () => void;
  clearChatBanner: () => void;
  ensureSessionVisible: (sessionId: string, title: string) => void;
  createPlaceholderAssistant: () => void;
  enableForceFollow: (ms: number) => void;
  scrollMessagesToBottom: (force: boolean) => void;
  flushStreamUpdate: (
    assistantIndex: number,
    content: string,
    createdTime: string | undefined,
    modelName: string | undefined
  ) => void;
  updateAssistantMessage: (
    assistantIndex: number,
    content: string,
    options?: {
      createdTime?: string;
      modelName?: string;
      pending?: boolean;
      role?: ChatSendDisplayMessage['role'];
    }
  ) => void;
  followOrNotifyNewMessage: (markUnread: boolean) => void | Promise<void>;
  resetHistoryPage: () => void;
  /** 发送成功后同步当前会话的总消息数（分页总数），保证计数标签实时 */
  refreshHistoryPagination: () => void | Promise<void>;
  loadSessions: (showLoading?: boolean, page?: number, silent?: boolean) => Promise<void>;
  requestSessionTitle: (sessionId: string) => Promise<void>;
  setNotice: (type: 'success' | 'danger' | 'warning' | 'info', message: string) => void;
}

export function createChatSendHandler(options: UseChatSendOptions) {
  return async function handleSend(invokeOptions?: ChatSendInvokeOptions) {
    const text = options.draftMessage.value.trim();
    if (!text || options.sendLoading.value) return;

    const sendSource: ChatSendSource = invokeOptions?.source ?? 'composer';

    try {
      options.sendLoading.value = true;
      options.clearChatBanner();
      options.suggestedQuestions.value = [];
      options.resetPendingAction();

      if (!options.currentSessionId.value) {
        const created = await createChatSession();
        options.currentSessionId.value = created.session_id || created.session?.session_id || '';
        options.currentSessionTitle.value = created.session?.title || options.t('chat.sessions.defaultTitle');
      }
      options.ensureSessionVisible(options.currentSessionId.value, options.currentSessionTitle.value);

      const userKey = `user-${Date.now()}-${(options.messageCounter.value += 1)}`;
      options.messages.value.push({
        key: userKey,
        role: 'user',
        content: text,
        created_time: new Date().toISOString()
      });
      options.draftMessage.value = '';
      options.createPlaceholderAssistant();
      options.enableForceFollow(7000);
      await nextTick();
      options.scrollMessagesToBottom(true);

      // 回复期间翻历史页会整体替换 messages，下标会指到别的消息上，每次写入都按 key 重新找
      const assistantKey = options.pendingAssistantKey.value;
      const findAssistantIndex = () => options.messages.value.findIndex((item) => item.key === assistantKey);
      const assistantIndex = findAssistantIndex();
      const sentSessionId = options.currentSessionId.value;
      const sessionChanged = () => options.currentSessionId.value !== sentSessionId;
      const supportsKnowledge = Boolean(options.chatConfig.value?.capabilities?.supports_knowledge);
      const useKnowledgeEnhance = supportsKnowledge && text.length >= 8;
      const requestPayload = {
        session_id: options.currentSessionId.value,
        message: text,
        mode: 'chat' as const,
        type: 'chat' as const,
        use_context: true,
        use_knowledge: useKnowledgeEnhance,
        use_rag: useKnowledgeEnhance,
        auto_suggest: options.smartReplyEnabled.value,
        use_smart_reply: options.smartReplyEnabled.value,
        settings: {
          model: options.chatConfig.value?.default_model,
          max_tokens: options.chatConfig.value?.default_max_tokens,
          temperature: options.chatConfig.value?.default_temperature
        },
        metadata: { send_source: sendSource }
      };

      if (options.streamEnabled.value) {
        options.abortActiveChat();
        const streamController = options.beginAbortableRequest();
        const streamSessionId = options.currentSessionId.value;
        let streamUnreadMarked = false;

        const { streamText, streamTimestamp, streamErrored } = await runChatStream({
          payload: requestPayload,
          signal: streamController.signal,
          streamSessionId,
          currentSessionId: () => options.currentSessionId.value,
          assistantIndex,
          thinkingLabel: options.t('chat.state.thinking'),
          sendFailedLabel: options.t('chat.message.sendFailed'),
          defaultModel: options.chatConfig.value?.default_model,
          onFlush: (_index, content, createdTime, modelName) => {
            const index = findAssistantIndex();
            if (index >= 0) options.flushStreamUpdate(index, content, createdTime, modelName);
          },
          onChunkProgress: async (isChunkOrEnd) => {
            const shouldMarkUnread = !streamUnreadMarked && isChunkOrEnd;
            await options.followOrNotifyNewMessage(shouldMarkUnread);
            if (shouldMarkUnread && !options.autoScrollEnabled.value) {
              streamUnreadMarked = true;
            }
          },
          onSuggestions: (suggestions) => {
            if (!sessionChanged()) options.suggestedQuestions.value = suggestions;
          }
        });

        if (sessionChanged()) {
          options.pendingAssistantKey.value = '';
          return;
        }
        if (streamController.signal.aborted) {
          throw new DOMException('Aborted', 'AbortError');
        }
        const finalIndex = findAssistantIndex();
        if (!streamErrored && finalIndex >= 0) {
          options.updateAssistantMessage(finalIndex, streamText, {
            createdTime: streamTimestamp,
            modelName: options.chatConfig.value?.default_model || undefined,
            pending: false
          });
        }
      } else {
        const result = await sendChatMessage(requestPayload);
        if (sessionChanged()) {
          options.pendingAssistantKey.value = '';
          return;
        }
        options.suggestedQuestions.value = Array.isArray(result.suggestions)
          ? result.suggestions.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
          : [];
        const finalIndex = findAssistantIndex();
        if (finalIndex >= 0) {
          options.updateAssistantMessage(finalIndex, result.response || options.t('chat.state.emptyMessage'), {
            createdTime: result.timestamp || new Date().toISOString(),
            modelName: result.model_name || options.chatConfig.value?.default_model,
            pending: false
          });
        }
        await options.followOrNotifyNewMessage(true);
      }

      options.pendingAssistantKey.value = '';
      options.resetHistoryPage();
      void options.refreshHistoryPagination();
      void options.loadSessions(false, 1, true).then(() => options.requestSessionTitle(sentSessionId));
      options.setNotice('success', options.t('chat.message.sendSuccess'));
    } catch (error) {
      if (options.isAbortError(error)) {
        const abortedIndex = options.messages.value.findIndex((item) => item.key === options.pendingAssistantKey.value);
        if (abortedIndex >= 0) {
          const aborted = options.messages.value[abortedIndex];
          const partial = String(aborted.content || '').trim();
          if (!partial || partial === options.t('chat.state.thinking')) {
            options.messages.value.splice(abortedIndex, 1);
          } else {
            options.messages.value[abortedIndex] = { ...aborted, pending: false };
          }
          void options.refreshHistoryPagination();
        }
        options.pendingAssistantKey.value = '';
        return;
      }
      const assistantIndex = options.messages.value.findIndex((item) => item.key === options.pendingAssistantKey.value);
      const fallback = resolveSendErrorMessage(error, options.t);
      const modelInitError = isModelInitError(error);
      if (assistantIndex >= 0) {
        options.messages.value[assistantIndex] = {
          ...options.messages.value[assistantIndex],
          role: modelInitError ? 'system' : options.messages.value[assistantIndex].role,
          content: modelInitError ? options.t('chat.message.llmNotInitialized') : fallback,
          pending: false,
          model_name: options.chatConfig.value?.default_model || undefined
        };
      }
      options.pendingAssistantKey.value = '';
      options.setNotice(
        modelInitError ? 'warning' : 'danger',
        modelInitError ? options.t('chat.message.llmNotInitialized') : fallback
      );
    } finally {
      options.sendLoading.value = false;
    }
  };
}
