import { ApiError } from '@/api/http';
import { streamChatMessage, type ChatMessagePayload, type ChatStreamEvent } from '@/api/chat';

export interface ChatStreamRunnerOptions {
  payload: ChatMessagePayload;
  signal: AbortSignal;
  streamSessionId: string;
  currentSessionId: () => string;
  assistantIndex: number;
  thinkingLabel: string;
  sendFailedLabel: string;
  defaultModel?: string;
  flushIntervalMs?: number;
  onFlush: (assistantIndex: number, text: string, timestamp: string | undefined, modelName: string | undefined) => void;
  onChunkProgress: (markUnread: boolean) => void | Promise<void>;
  onSuggestions: (suggestions: string[]) => void;
}

export interface ChatStreamRunnerResult {
  streamText: string;
  streamTimestamp?: string;
  streamErrored: boolean;
}

export async function runChatStream(options: ChatStreamRunnerOptions): Promise<ChatStreamRunnerResult> {
  const flushIntervalMs = options.flushIntervalMs ?? 50;
  const stream = await streamChatMessage(options.payload, options.signal);
  let streamText = '';
  let streamTimestamp: string | undefined;
  let streamErrored = false;
  const modelName = options.defaultModel;
  let lastFlushAt = 0;
  let streamFlushTimer: number | null = null;

  const scheduleFlush = (force = false) => {
    if (options.currentSessionId() !== options.streamSessionId) return;
    const now = Date.now();
    if (force || now - lastFlushAt >= flushIntervalMs) {
      if (streamFlushTimer !== null) {
        window.clearTimeout(streamFlushTimer);
        streamFlushTimer = null;
      }
      options.onFlush(options.assistantIndex, streamText, streamTimestamp, modelName);
      lastFlushAt = now;
      return;
    }
    if (streamFlushTimer !== null) return;
    streamFlushTimer = window.setTimeout(() => {
      streamFlushTimer = null;
      options.onFlush(options.assistantIndex, streamText, streamTimestamp, modelName);
      lastFlushAt = Date.now();
    }, flushIntervalMs);
  };

  try {
    for await (const event of stream as AsyncIterable<ChatStreamEvent>) {
      if (options.signal.aborted || options.currentSessionId() !== options.streamSessionId) break;
      if (event.type === 'error') {
        streamErrored = true;
        const statusCode = Number((event.raw as Record<string, unknown> | undefined)?.status_code || 0);
        const errorCode = String((event.raw as Record<string, unknown> | undefined)?.error_code || '');
        throw new ApiError(String(event.message || options.sendFailedLabel), {
          code: Number.isFinite(statusCode) && statusCode > 0 ? statusCode : undefined,
          errorCode: errorCode || undefined,
          details: event.raw
        });
      }

      if (event.type === 'chunk') {
        streamText += String(event.content || '');
      }

      if (event.type === 'end') {
        if (event.full_response) {
          streamText = String(event.full_response);
        }
        streamTimestamp = event.timestamp || streamTimestamp;
        options.onSuggestions(
          Array.isArray(event.suggestions)
            ? event.suggestions.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
            : []
        );
      }

      scheduleFlush(event.type === 'end');
      const shouldMarkUnread = event.type === 'chunk' || event.type === 'end';
      await options.onChunkProgress(shouldMarkUnread);
    }
  } finally {
    // 出错或中断时也要清掉待刷新的定时器，否则它会在调用方写入错误提示后把半截回复写回去
    if (streamFlushTimer !== null) {
      window.clearTimeout(streamFlushTimer);
      streamFlushTimer = null;
    }
  }

  return { streamText, streamTimestamp, streamErrored };
}
