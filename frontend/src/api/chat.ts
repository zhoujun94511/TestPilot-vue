import http, { ApiError, del, get, post } from './http';
import {
  asArray as coreAsArray,
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  paginationAdapter,
  pickCompatField
} from './core';

export type ChatRole = 'system' | 'user' | 'assistant';
export type ChatMessageType = 'chat' | 'test_case' | 'requirement_analysis';
export type ChatMode = 'chat' | 'action';
export type ChatExportFormat = 'json' | 'txt' | 'excel';
export type ChatStreamEventType = 'start' | 'chunk' | 'end' | 'error';

export interface ChatSessionRecord {
  session_id: string;
  title: string;
  last_activity?: string | null;
  message_count?: number;
  total_tokens?: number;
  raw?: Record<string, unknown>;
}

export interface ChatSessionPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export interface ChatSessionListResponse {
  sessions: ChatSessionRecord[];
  pagination: ChatSessionPagination;
  total: number;
}

export interface ChatMessageRecord {
  id?: number;
  session_id: string;
  role: ChatRole | string;
  content: string;
  message_type?: ChatMessageType | string;
  created_time?: string | null;
  tokens_used?: number;
  model_name?: string;
  raw?: Record<string, unknown>;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessageRecord[];
  pagination: ChatSessionPagination;
  total_messages: number;
}

export interface ChatConfig {
  company?: string;
  default_model?: string;
  available_models?: string[];
  capabilities?: {
    supports_knowledge?: boolean;
    supports_streaming?: boolean;
    [key: string]: unknown;
  };
  default_temperature?: number;
  default_max_tokens?: number;
  experimental_actions_enabled?: boolean;
  raw?: Record<string, unknown>;
}

export interface ChatTemplateRecord {
  id?: string;
  key?: string;
  title?: string;
  content?: string;
  type?: string;
  description?: string;
  raw?: Record<string, unknown>;
}

export interface ChatTemplateResponse {
  templates: ChatTemplateRecord[];
  raw?: Record<string, unknown>;
}

export interface ChatSingleTemplateResponse {
  template: ChatTemplateRecord | null;
  raw?: Record<string, unknown>;
}

export interface ChatMessagePayload {
  session_id?: string;
  message: string;
  type?: ChatMessageType;
  use_context?: boolean;
  use_knowledge?: boolean;
  use_rag?: boolean;
  auto_suggest?: boolean;
  use_smart_reply?: boolean;
  temperature?: number;
  max_tokens?: number;
  settings?: Record<string, unknown>;
  mode?: ChatMode;
  require_confirmation?: boolean;
  metadata?: Record<string, unknown>;
}

export interface QuickReplyFeedbackPayload {
  suggestion_text: string;
  was_clicked: boolean;
  session_id?: string;
  user_id?: string;
}

export interface ChatMessageResult {
  success: boolean;
  session_id: string;
  response: string;
  message_id?: number;
  tokens_used?: number;
  model_name?: string;
  timestamp?: string;
  suggestions?: string[];
  mode?: ChatMode;
  status?: string;
  execution_id?: string;
  action_plan?: Record<string, unknown> | null;
  tool_results?: Record<string, unknown> | null;
  error?: string;
  raw?: Record<string, unknown>;
}

export interface ChatCreateSessionPayload {
  title?: string;
}

export interface ChatCreateSessionResult {
  success: boolean;
  session_id: string;
  session?: ChatSessionRecord;
  raw?: Record<string, unknown>;
}

export interface ChatExportResult {
  blob: Blob;
  filename: string;
  format: ChatExportFormat;
  mimeType?: string;
}

export interface ChatStreamEvent {
  type: ChatStreamEventType;
  timestamp?: string;
  content?: string;
  message?: string;
  session_id?: string;
  suggestions?: string[];
  full_response?: string;
  raw: Record<string, unknown>;
}

export interface ChatSuggestionResponse {
  suggestions: string[];
  raw?: Record<string, unknown>;
}

export interface QuickReplyStats {
  total_suggestions?: number;
  clicked_suggestions?: number;
  click_rate?: number;
  [key: string]: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function extractMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) return error.message || fallback;
  if (error instanceof Error) return error.message || fallback;
  return fallback;
}

function normalizeTextArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item ?? '').trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  }
  return [];
}

function normalizeSessionRecord(raw: Record<string, unknown>): ChatSessionRecord {
  return {
    session_id: String(pickCompatField(raw, ['session_id', 'id'], '')),
    title: String(pickCompatField(raw, ['title'], '')),
    last_activity: pickCompatField(raw, ['last_activity', 'updated_time', 'updated_at'], null),
    message_count: raw.message_count != null ? Number(raw.message_count) : undefined,
    total_tokens: raw.total_tokens != null ? Number(raw.total_tokens) : undefined,
    raw
  };
}

function normalizeHistoryRecord(raw: Record<string, unknown>): ChatMessageRecord {
  return {
    id: raw.id != null ? Number(raw.id) : undefined,
    session_id: String(pickCompatField(raw, ['session_id'], '')),
    role: String(pickCompatField(raw, ['role'], '')),
    content: String(pickCompatField(raw, ['content'], '')),
    message_type: pickCompatField(raw, ['message_type'], undefined),
    created_time: pickCompatField(raw, ['created_time', 'created_at'], null),
    tokens_used: raw.tokens_used != null ? Number(raw.tokens_used) : undefined,
    model_name: pickCompatField(raw, ['model_name'], undefined),
    raw
  };
}

function normalizeSessionList(payload: unknown): ChatSessionListResponse {
  const normalized = isRecord(payload) ? payload : {};
  const sessions = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['sessions', 'items', 'data'], []))
    .map(normalizeSessionRecord);
  const pagination = paginationAdapter(pickCompatField(normalized, ['pagination'], {}), {
    page: 1,
    per_page: sessions.length || 10,
    total: sessions.length,
    pages: sessions.length > 0 ? 1 : 0
  });

  return {
    sessions,
    pagination,
    total: Number(pickCompatField(normalized, ['total'], sessions.length))
  };
}

function normalizeHistory(payload: unknown): ChatHistoryResponse {
  const normalized = isRecord(payload) ? payload : {};
  const messages = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['messages', 'items', 'data'], []))
    .map(normalizeHistoryRecord);
  const pagination = paginationAdapter(pickCompatField(normalized, ['pagination'], {}), {
    page: 1,
    per_page: messages.length || 20,
    total: messages.length,
    pages: messages.length > 0 ? 1 : 0
  });

  return {
    session_id: String(pickCompatField(normalized, ['session_id'], '')),
    messages,
    pagination,
    total_messages: Number(pickCompatField(normalized, ['total_messages', 'total'], messages.length))
  };
}

function normalizeConfig(payload: unknown): ChatConfig {
  const normalized = isRecord(payload) ? payload : {};
  return {
    company: pickCompatField(normalized, ['company'], undefined),
    default_model: pickCompatField(normalized, ['default_model'], undefined),
    available_models: normalizeTextArray(pickCompatField(normalized, ['available_models'], [])),
    capabilities: isRecord(normalized.capabilities) ? normalized.capabilities : undefined,
    default_temperature: normalized.default_temperature != null ? Number(normalized.default_temperature) : undefined,
    default_max_tokens: normalized.default_max_tokens != null ? Number(normalized.default_max_tokens) : undefined,
    experimental_actions_enabled: Boolean(pickCompatField(normalized, ['experimental_actions_enabled'], false)),
    raw: normalized
  };
}

function normalizeTemplates(payload: unknown): ChatTemplateResponse {
  const normalized = isRecord(payload) ? payload : {};
  const templates = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['templates', 'items', 'data'], []))
    .map((raw) => ({
      id: pickCompatField(raw, ['id'], undefined),
      key: pickCompatField(raw, ['key'], undefined),
      title: pickCompatField(raw, ['title'], undefined),
      content: pickCompatField(raw, ['content'], undefined),
      type: pickCompatField(raw, ['type'], undefined),
      description: pickCompatField(raw, ['description'], undefined),
      raw
    }));

  return { templates, raw: normalized };
}

function parseFilename(headers: unknown, fallback: string) {
  if (!isRecord(headers)) return fallback;
  const disposition = String(pickCompatField(headers, ['content-disposition', 'Content-Disposition'], ''));
  if (!disposition) return fallback;

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  if (plainMatch?.[1]) {
    return plainMatch[1];
  }

  return fallback;
}

function buildApiBase(): string {
  const base = import.meta.env.VITE_API_BASE_URL || '/api';
  return base.endsWith('/') ? base.slice(0, -1) : base;
}

async function fetchSse(url: string, body: ChatMessagePayload): Promise<AsyncGenerator<ChatStreamEvent>> {
  const response = await fetch(`${buildApiBase()}${url}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept-Language': localStorage.getItem('testpilot_locale') || 'zh-CN',
      'X-Requested-With': 'XMLHttpRequest'
    },
    credentials: 'include',
    body: JSON.stringify(body)
  });

  if (!response.ok || !response.body) {
    let errorMessage = `HTTP ${response.status}`;
    let errorCode: string | undefined;
    let errorDetails: unknown;
    try {
      const payload = await response.json();
      if (isRecord(payload)) {
        const message = pickCompatField(payload, ['message', 'error', 'details'], '');
        if (message) {
          errorMessage = String(message);
        }
        const normalizedErrorCode = pickCompatField(payload, ['error_code'], '');
        if (normalizedErrorCode) {
          errorCode = String(normalizedErrorCode);
        }
        const details = pickCompatField(payload, ['details'], undefined);
        if (details !== undefined) {
          errorDetails = details;
        }
      }
    } catch {
      // ignore JSON parse failures and keep HTTP status fallback
    }
    throw new ApiError(errorMessage, {
      code: response.status,
      errorCode,
      details: errorDetails
    });
  }

  async function* iterator(): AsyncGenerator<ChatStreamEvent> {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf('\n\n');
        while (boundary !== -1) {
          const packet = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          boundary = buffer.indexOf('\n\n');

          const dataLine = packet
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trimStart())
            .join('\n');
          if (!dataLine) continue;

          let parsed: Record<string, unknown>;
          try {
            parsed = JSON.parse(dataLine) as Record<string, unknown>;
          } catch {
            parsed = { type: 'error', message: dataLine };
          }

          const type = String(pickCompatField(parsed, ['type'], 'error')) as ChatStreamEventType;
          yield {
            type,
            timestamp: pickCompatField(parsed, ['timestamp'], undefined),
            content: pickCompatField(parsed, ['content'], undefined),
            message: pickCompatField(parsed, ['message'], undefined),
            session_id: pickCompatField(parsed, ['session_id'], undefined),
            suggestions: coreAsArray<string>(pickCompatField(parsed, ['suggestions'], [])),
            full_response: pickCompatField(parsed, ['full_response'], undefined),
            raw: parsed
          };
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  return iterator();
}

export async function listChatSessions(params: Record<string, unknown> = {}): Promise<ChatSessionListResponse> {
  try {
    const response = await get<unknown>('/chat/sessions', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load chat sessions'
    });
    return normalizeSessionList(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load chat sessions');
  }
}

export async function getChatHistory(sessionId: string, params: Record<string, unknown> = {}): Promise<ChatHistoryResponse> {
  try {
    const response = await get<unknown>('/chat/history', {
      session_id: sessionId,
      ...params
    });
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load chat history'
    });
    return normalizeHistory(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load chat history');
  }
}

export async function sendChatMessage(payload: ChatMessagePayload): Promise<ChatMessageResult> {
  try {
    const response = await post<unknown>('/chat/message', payload);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to send chat message'
    });
    return {
      success: true,
      session_id: String(pickCompatField(normalized, ['session_id'], payload.session_id || '')),
      response: String(pickCompatField(normalized, ['response', 'message'], '')),
      message_id: normalized.message_id != null ? Number(normalized.message_id) : undefined,
      tokens_used: normalized.tokens_used != null ? Number(normalized.tokens_used) : undefined,
      model_name: pickCompatField(normalized, ['model_name'], undefined),
      timestamp: pickCompatField(normalized, ['timestamp'], undefined),
      suggestions: coreAsArray<string>(pickCompatField(normalized, ['suggestions'], [])),
      mode: pickCompatField(normalized, ['mode'], undefined),
      status: pickCompatField(normalized, ['status'], undefined),
      execution_id: pickCompatField(normalized, ['execution_id'], undefined),
      action_plan: isRecord(pickCompatField(normalized, ['action_plan'], null))
        ? pickCompatField(normalized, ['action_plan'], null) as Record<string, unknown>
        : null,
      tool_results: isRecord(pickCompatField(normalized, ['tool_results'], null))
        ? pickCompatField(normalized, ['tool_results'], null) as Record<string, unknown>
        : null,
      error: pickCompatField(normalized, ['error'], undefined),
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to send chat message');
  }
}

export async function confirmExperimentalAction(executionId: string, metadata: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
  try {
    const response = await post<unknown>('/experimental-actions/confirm', {
      execution_id: executionId,
      metadata
    });
    return coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to confirm experimental action'
    });
  } catch (error) {
    coreNormalizeError(error, 'Failed to confirm experimental action');
  }
}

export async function cancelExperimentalAction(executionId: string, reason = ''): Promise<Record<string, unknown>> {
  try {
    const response = await post<unknown>('/experimental-actions/cancel', {
      execution_id: executionId,
      reason
    });
    return coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to cancel experimental action'
    });
  } catch (error) {
    coreNormalizeError(error, 'Failed to cancel experimental action');
  }
}

export async function streamChatMessage(payload: ChatMessagePayload): Promise<AsyncGenerator<ChatStreamEvent>> {
  try {
    return await fetchSse('/chat/stream', payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to stream chat message');
  }
}

export async function createChatSession(payload: ChatCreateSessionPayload = {}): Promise<ChatCreateSessionResult> {
  try {
    const response = await post<unknown>('/chat/sessions', payload);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to create chat session'
    });
    const session = isRecord(normalized.session) ? normalizeSessionRecord(normalized.session) : undefined;
    return {
      success: true,
      session_id: String(pickCompatField(normalized, ['session_id'], session?.session_id || '')),
      session,
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to create chat session');
  }
}

export async function deleteChatSession(sessionId: string): Promise<{ success: boolean; raw?: Record<string, unknown> }> {
  try {
    const response = await del<unknown>(`/chat/session/${encodeURIComponent(sessionId)}`);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to delete chat session'
    });
    return {
      success: true,
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to delete chat session');
  }
}

export async function clearChatHistory(sessionId?: string): Promise<{ success: boolean; deleted_count?: number; raw?: Record<string, unknown> }> {
  try {
    const response = await post<unknown>('/chat/clear', sessionId ? { session_id: sessionId } : {});
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to clear chat history'
    });
    return {
      success: true,
      deleted_count: normalized.deleted_count != null ? Number(normalized.deleted_count) : undefined,
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to clear chat history');
  }
}

export async function getChatTemplates(type = 'chat', locale?: string): Promise<ChatTemplateResponse> {
  try {
    const response = await get<unknown>('/chat/templates', { type, locale });
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load chat templates'
    });
    return normalizeTemplates(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load chat templates');
  }
}

export async function getChatTemplate(templateType = 'chat', locale?: string): Promise<ChatSingleTemplateResponse> {
  try {
    const response = await get<unknown>(`/chat/template/${encodeURIComponent(templateType)}`, { locale });
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['template', 'data'],
      fallbackMessage: 'Failed to load chat template'
    });
    const templateRaw = isRecord(payload) ? payload : {};
    const template: ChatTemplateRecord = {
      id: pickCompatField(templateRaw, ['id'], undefined),
      key: pickCompatField(templateRaw, ['key'], undefined),
      title: pickCompatField(templateRaw, ['title'], undefined),
      content: pickCompatField(templateRaw, ['content', 'template', 'text'], undefined),
      type: pickCompatField(templateRaw, ['type'], undefined),
      description: pickCompatField(templateRaw, ['description'], undefined),
      raw: templateRaw
    };
    return { template, raw: templateRaw };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load chat template');
  }
}

export async function getChatConfig(): Promise<ChatConfig> {
  try {
    const response = await get<unknown>('/chat/config');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['config', 'data'],
      fallbackMessage: 'Failed to load chat config'
    });
    return normalizeConfig(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load chat config');
  }
}

export async function exportChatHistory(sessionId: string, format: ChatExportFormat = 'json'): Promise<ChatExportResult> {
  try {
    const response = await http.request<Blob>({
      url: '/export/chat/history',
      method: 'GET',
      params: { session_id: sessionId, format },
      responseType: 'blob'
    });

    return {
      blob: response.data as Blob,
      filename: parseFilename(response.headers, `chat_history.${format === 'excel' ? 'xlsx' : format}`),
      format,
      mimeType: String(pickCompatField(response.headers, ['content-type', 'Content-Type'], ''))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to export chat history');
  }
}

export async function trackQuickReplyFeedback(payload: QuickReplyFeedbackPayload): Promise<{ success: boolean; raw?: Record<string, unknown> }> {
  try {
    const response = await post<unknown>('/chat/quick-reply/feedback', payload);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to track quick reply feedback'
    });
    return {
      success: true,
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to track quick reply feedback');
  }
}

export async function getChatSuggestions(context = ''): Promise<ChatSuggestionResponse> {
  try {
    const response = await post<unknown>('/chat/suggestions', { context });
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load chat suggestions'
    });
    return {
      suggestions: coreAsArray<string>(pickCompatField(normalized, ['suggestions'], [])),
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load chat suggestions');
  }
}

export async function getQuickReplyStats(): Promise<QuickReplyStats> {
  try {
    const response = await get<unknown>('/chat/quick-reply/stats');
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load quick reply stats'
    });
    const stats = pickCompatField(normalized, ['statistics', 'stats', 'data'], {});
    return isRecord(stats) ? (stats as QuickReplyStats) : {};
  } catch (error) {
    coreNormalizeError(error, 'Failed to load quick reply stats');
  }
}
