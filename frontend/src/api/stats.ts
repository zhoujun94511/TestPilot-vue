import http, { LONG_TASK_TIMEOUT_MS, download, get } from './http';
import {
  asArray as coreAsArray,
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  pickCompatField
} from './core';

export interface OverviewTotals {
  test_cases: number;
  requirements: number;
  knowledge_files: number;
  chat_sessions: number;
  chat_messages?: number;
  raw?: Record<string, unknown>;
}

export interface OverviewRecentActivity {
  period_days?: number;
  test_cases: number;
  requirements: number;
  knowledge_files: number;
  chat_messages: number;
  raw?: Record<string, unknown>;
}

export interface OverviewStats {
  totals: OverviewTotals;
  recent_activity?: OverviewRecentActivity;
  distributions?: Record<string, unknown>;
  generated_at?: string;
  processing_time?: number;
  raw?: Record<string, unknown>;
}

export interface HealthComponentRecord {
  status?: string;
  [key: string]: unknown;
}

export interface DashboardServiceRecord {
  status?: string;
  model?: string;
  response_time?: number | string;
  docs?: number | string;
  vectors?: number | string;
  cpu?: number | string;
  memory?: number | string;
  disk?: number | string;
  [key: string]: unknown;
}

export interface HealthStatus {
  success: boolean;
  status?: string;
  message?: string;
  timestamp?: string;
  health?: {
    status?: string;
    message?: string;
    timestamp?: string;
    components?: {
      ai_service?: DashboardServiceRecord;
      knowledge?: DashboardServiceRecord;
      performance?: DashboardServiceRecord;
      [key: string]: DashboardServiceRecord | undefined;
    };
    [key: string]: unknown;
  };
  components?: Record<string, HealthComponentRecord>;
  raw?: Record<string, unknown>;
}

export interface SystemStatus {
  success: boolean;
  message?: string;
  system?: {
    ai_service?: DashboardServiceRecord;
    knowledge?: DashboardServiceRecord;
    performance?: DashboardServiceRecord;
    [key: string]: unknown;
  };
  timestamp?: string;
  raw?: Record<string, unknown>;
}

export interface RecentActivityRecord {
  type: string;
  /** @deprecated 使用 subject + 前端 i18n；保留兼容旧 API */
  message: string;
  /** 活动主体（用例标题、文件名、聊天摘要等），不含前缀说明 */
  subject?: string;
  time?: string | null;
  icon?: string;
  color?: string;
  raw?: Record<string, unknown>;
}

export interface RecentActivitiesResponse {
  activities: RecentActivityRecord[];
  counts?: Record<string, number>;
  periodDays?: number;
  raw?: Record<string, unknown>;
}

export interface PerformanceStatsResponse {
  period_hours?: number;
  metrics?: Record<string, Array<{ name?: string; value?: number; unit?: string; timestamp?: string }>>;
  summary?: Record<string, { avg?: number; min?: number; max?: number; count?: number }>;
  raw?: Record<string, unknown>;
}

export interface UsageStatsResponse {
  period_days?: number;
  daily_trends?: {
    test_cases?: Array<{ date: string; count: number }>;
    requirements?: Array<{ date: string; count: number }>;
    chat_messages?: Array<{ date: string; count: number }>;
  };
  category_distribution?: Record<string, number>;
  raw?: Record<string, unknown>;
}

export interface TokenStatsResponse {
  period_days?: number;
  source?: string;
  included_scopes?: string[];
  summary?: {
    total_tokens?: number;
    avg_tokens_per_call?: number;
    total_calls?: number;
    avg_tokens_per_message?: number;
    total_messages?: number;
  };
  by_source?: Array<{ source?: string; total_tokens?: number; call_count?: number }>;
  by_model?: Array<{ model?: string; total_tokens?: number; message_count?: number; call_count?: number }>;
  daily_usage?: Array<{ date: string; total_tokens: number }>;
  raw?: Record<string, unknown>;
}

export interface NetworkInfoResponse {
  status?: string;
  local_ip?: string | null;
  raw?: Record<string, unknown>;
}

export interface LogStatsResponse {
  period_hours?: number;
  level_distribution?: Record<string, number>;
  top_modules?: Array<{ module?: string; count?: number }>;
  recent_errors?: Array<{ id?: number; level?: string; message?: string; module?: string; timestamp?: string }>;
  raw?: Record<string, unknown>;
}

export interface ExportStatsParams {
  type?: 'overview' | 'performance' | 'usage' | 'tokens' | string;
  format?: 'json' | 'excel' | 'csv';
  days?: number;
}

export interface BatchExportConfig {
  export_cases?: boolean;
  all_cases?: boolean;
  cases?: object[];
  case_formats?: Array<'excel' | 'csv' | 'json'>;
  export_requirements?: boolean;
  all_requirements?: boolean;
  requirements?: object[];
  export_chat?: boolean;
  chat_history?: object[];
  chat_formats?: Array<'excel' | 'txt' | 'json'>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeOverview(payload: unknown): OverviewStats {
  const normalized = isRecord(payload) ? payload : {};
  const totals = isRecord(normalized.totals) ? normalized.totals : normalized;
  const recentActivity = isRecord(normalized.recent_activity) ? normalized.recent_activity : undefined;

  return {
    totals: {
      test_cases: Number(pickCompatField(totals, ['test_cases', 'total_cases'], 0)),
      requirements: Number(pickCompatField(totals, ['requirements', 'total_requirements'], 0)),
      knowledge_files: Number(pickCompatField(totals, ['knowledge_files', 'total_knowledge_files'], 0)),
      chat_sessions: Number(pickCompatField(totals, ['chat_sessions', 'total_chat_sessions'], 0)),
      chat_messages: totals.chat_messages != null ? Number(totals.chat_messages) : undefined,
      raw: totals
    },
    recent_activity: recentActivity
      ? {
          period_days: recentActivity.period_days != null ? Number(recentActivity.period_days) : undefined,
          test_cases: Number(pickCompatField(recentActivity, ['test_cases', 'new_cases'], 0)),
          requirements: Number(pickCompatField(recentActivity, ['requirements', 'new_requirements'], 0)),
          knowledge_files: Number(pickCompatField(recentActivity, ['knowledge_files', 'new_knowledge_files'], 0)),
          chat_messages: Number(pickCompatField(recentActivity, ['chat_messages', 'chat_messages_count'], 0)),
          raw: recentActivity
        }
      : undefined,
    distributions: isRecord(normalized.distributions) ? normalized.distributions : undefined,
    generated_at: pickCompatField(normalized, ['generated_at', 'timestamp'], undefined),
    processing_time: normalized.processing_time != null ? Number(normalized.processing_time) : undefined,
    raw: normalized
  };
}

function normalizeHealth(payload: unknown): HealthStatus {
  const normalized = isRecord(payload) ? payload : {};
  const health = isRecord(normalized.health) ? normalized.health : normalized;
  const components = isRecord(health.components) ? health.components : isRecord(normalized.components) ? normalized.components : undefined;

  return {
    success: payload === undefined ? false : normalized.success !== false,
    status: pickCompatField(normalized, ['status'], undefined),
    message: pickCompatField(normalized, ['message'], undefined),
    timestamp: pickCompatField(normalized, ['timestamp'], undefined),
    health,
    components: components ? (components as Record<string, HealthComponentRecord>) : undefined,
    raw: normalized
  };
}

function normalizeSystemStatus(payload: unknown): SystemStatus {
  const normalized = isRecord(payload) ? payload : {};
  return {
    success: normalized.success !== false,
    message: pickCompatField(normalized, ['message'], undefined),
    system: isRecord(normalized.system) ? normalized.system : normalized,
    timestamp: pickCompatField(normalized, ['timestamp'], undefined),
    raw: normalized
  };
}

function normalizeRecentActivities(payload: unknown): RecentActivitiesResponse {
  const normalized = Array.isArray(payload)
    ? { activities: payload }
    : isRecord(payload)
      ? payload
      : {};
  const activities = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['activities', 'items', 'data'], []))
    .map((raw) => {
      const subjectRaw = pickCompatField(raw, ['subject', 'title', 'detail'], undefined);
      const subject =
        subjectRaw === undefined || subjectRaw === null ? undefined : String(subjectRaw);
      return {
        type: String(pickCompatField(raw, ['type'], 'unknown')),
        message: String(pickCompatField(raw, ['message'], '')),
        subject,
        time: pickCompatField(raw, ['time', 'timestamp', 'created_time'], null),
        icon: pickCompatField(raw, ['icon'], undefined),
        color: pickCompatField(raw, ['color'], undefined),
        raw
      };
    });

  const countsRaw = isRecord(normalized.counts) ? normalized.counts : undefined;
  const counts = countsRaw
    ? Object.fromEntries(Object.entries(countsRaw).map(([key, value]) => [key, Number(value || 0)]))
    : undefined;
  const periodDays = normalized.period_days != null ? Number(normalized.period_days) : undefined;

  return { activities, counts, periodDays, raw: normalized };
}

function extractOverviewPayload(payload: unknown): unknown {
  if (!isRecord(payload)) return payload;
  return pickCompatField(payload, ['overview', 'data'], payload);
}

function extractHealthPayload(payload: unknown): unknown {
  if (!isRecord(payload)) return payload;
  return pickCompatField(payload, ['health', 'data'], payload);
}

function extractSystemPayload(payload: unknown): unknown {
  if (!isRecord(payload)) return payload;
  return pickCompatField(payload, ['system', 'data'], payload);
}

export async function getOverviewStats(params: Record<string, unknown> = {}): Promise<OverviewStats> {
  try {
    const response = await get<unknown>('/stats/overview', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['overview', 'data'],
      fallbackMessage: 'Failed to load dashboard overview'
    });
    return normalizeOverview(extractOverviewPayload(payload));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load dashboard overview');
  }
}

export async function getHealthStatus(params: Record<string, unknown> = {}): Promise<HealthStatus> {
  try {
    const response = await get<unknown>('/stats/health', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['health', 'data'],
      fallbackMessage: 'Failed to load system health'
    });
    return normalizeHealth(extractHealthPayload(payload));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load system health');
  }
}

export async function getRecentActivities(params: Record<string, unknown> = {}): Promise<RecentActivitiesResponse> {
  try {
    const response = await get<unknown>('/stats/recent-activities', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to load recent activities'
    });
    const envelope = isRecord(payload) ? payload : isRecord(response) ? response : {};
    return normalizeRecentActivities(envelope);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load recent activities');
  }
}

export async function getSystemStatus(params: Record<string, unknown> = {}): Promise<SystemStatus> {
  try {
    const response = await get<unknown>('/stats/system-status', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['system', 'data'],
      fallbackMessage: 'Failed to load system status'
    });
    return normalizeSystemStatus(extractSystemPayload(payload));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load system status');
  }
}

export async function getPerformanceStats(params: Record<string, unknown> = {}): Promise<PerformanceStatsResponse> {
  try {
    const response = await get<unknown>('/stats/performance', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['performance', 'data'],
      fallbackMessage: 'Failed to load performance stats'
    });
    return {
      period_hours: payload.period_hours != null ? Number(payload.period_hours) : undefined,
      metrics: isRecord(payload.metrics) ? (payload.metrics as PerformanceStatsResponse['metrics']) : undefined,
      summary: isRecord(payload.summary) ? (payload.summary as PerformanceStatsResponse['summary']) : undefined,
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load performance stats');
  }
}

export async function getUsageStats(params: Record<string, unknown> = {}): Promise<UsageStatsResponse> {
  try {
    const response = await get<unknown>('/stats/usage', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['usage', 'data'],
      fallbackMessage: 'Failed to load usage stats'
    });
    return {
      period_days: payload.period_days != null ? Number(payload.period_days) : undefined,
      daily_trends: isRecord(payload.daily_trends) ? (payload.daily_trends as UsageStatsResponse['daily_trends']) : undefined,
      category_distribution: isRecord(payload.category_distribution)
        ? (payload.category_distribution as Record<string, number>)
        : undefined,
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load usage stats');
  }
}

export interface TokenSessionUsageSlice {
  used: number;
  max: number;
  percent: number;
}

export interface TokenSessionStatus {
  level: 'ok' | 'warning';
  warn_threshold_percent: number;
  tokens: TokenSessionUsageSlice;
  calls: TokenSessionUsageSlice;
  message_key?: string | null;
  message_params?: Record<string, unknown>;
  notice_signature?: string | null;
}

export async function getTokenSessionStatus(): Promise<TokenSessionStatus> {
  try {
    const response = await get<unknown>('/stats/token-session');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to load token session status'
    });
    const tokens = isRecord(payload.tokens) ? payload.tokens : {};
    const calls = isRecord(payload.calls) ? payload.calls : {};
    return {
      level: payload.level === 'warning' ? 'warning' : 'ok',
      warn_threshold_percent: Number(payload.warn_threshold_percent ?? 80),
      tokens: {
        used: Number(tokens.used ?? 0),
        max: Number(tokens.max ?? 0),
        percent: Number(tokens.percent ?? 0)
      },
      calls: {
        used: Number(calls.used ?? 0),
        max: Number(calls.max ?? 0),
        percent: Number(calls.percent ?? 0)
      },
      message_key: pickCompatField(payload, ['message_key'], null),
      message_params: isRecord(payload.message_params)
        ? (payload.message_params as Record<string, unknown>)
        : undefined,
      notice_signature: pickCompatField(payload, ['notice_signature'], null)
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load token session status');
  }
}

export async function getTokenStats(params: Record<string, unknown> = {}): Promise<TokenStatsResponse> {
  try {
    const response = await get<unknown>('/stats/tokens', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['tokens', 'data'],
      fallbackMessage: 'Failed to load token stats'
    });
    return {
      period_days: payload.period_days != null ? Number(payload.period_days) : undefined,
      source: payload.source != null ? String(payload.source) : undefined,
      included_scopes: coreAsArray<string>(pickCompatField(payload, ['included_scopes'], [])).map(String),
      by_source: coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['by_source'], [])).map((item) => ({
        source: item.source != null ? String(item.source) : undefined,
        total_tokens: item.total_tokens != null ? Number(item.total_tokens) : 0,
        call_count: item.call_count != null ? Number(item.call_count) : 0
      })),
      summary: isRecord(payload.summary) ? (payload.summary as TokenStatsResponse['summary']) : undefined,
      by_model: coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['by_model'], []))
        .map((item) => ({
          model: item.model != null ? String(item.model) : undefined,
          total_tokens: item.total_tokens != null ? Number(item.total_tokens) : 0,
          message_count: item.message_count != null ? Number(item.message_count) : 0
        })),
      daily_usage: coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['daily_usage'], []))
        .map((item) => ({
          date: String(item.date ?? ''),
          total_tokens: Number(item.total_tokens ?? 0)
        })),
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load token stats');
  }
}

export async function exportStats(params: ExportStatsParams = {}): Promise<Blob> {
  const exportType = params.type || 'overview';
  const formatType = params.format || 'csv';
  const days = params.days ?? 7;
  return download('/stats/export', {
    params: {
      type: exportType,
      format: formatType,
      days
    }
  });
}

export async function exportBatchZip(config: BatchExportConfig): Promise<Blob> {
  const response = await http.request<Blob>({
    url: '/export/batch',
    method: 'POST',
    data: { config },
    responseType: 'blob',
    timeout: LONG_TASK_TIMEOUT_MS
  });
  return response.data as Blob;
}

export async function getNetworkInfo(params: Record<string, unknown> = {}): Promise<NetworkInfoResponse> {
  try {
    const response = await get<unknown>('/stats/network/info', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['network_info', 'data'],
      fallbackMessage: 'Failed to load network info'
    });
    return {
      status: payload.status != null ? String(payload.status) : undefined,
      local_ip: payload.local_ip != null ? String(payload.local_ip) : null,
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load network info');
  }
}

export async function getLogStats(params: { hours?: number } = {}): Promise<LogStatsResponse> {
  try {
    const response = await get<unknown>('/stats/logs', {
      hours: params.hours ?? 24
    });
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['logs', 'data'],
      fallbackMessage: 'Failed to load log stats'
    });
    return {
      period_hours: payload.period_hours != null ? Number(payload.period_hours) : undefined,
      level_distribution: isRecord(payload.level_distribution)
        ? Object.fromEntries(
            Object.entries(payload.level_distribution).map(([key, value]) => [key, Number(value || 0)])
          )
        : undefined,
      top_modules: coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['top_modules'], []))
        .map((item) => ({
          module: item.module != null ? String(item.module) : undefined,
          count: item.count != null ? Number(item.count) : 0
        })),
      recent_errors: coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['recent_errors'], []))
        .map((item) => ({
          id: item.id != null ? Number(item.id) : undefined,
          level: item.level != null ? String(item.level) : undefined,
          message: item.message != null ? String(item.message) : undefined,
          module: item.module != null ? String(item.module) : undefined,
          timestamp: item.timestamp != null ? String(item.timestamp) : undefined
        })),
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load log stats');
  }
}

export interface AppFeatureFlagsResponse {
  enableVectorStore: boolean;
  experimentalActionsEnabled: boolean;
}

export async function getFeatureFlags(): Promise<AppFeatureFlagsResponse> {
  try {
    const response = await get<unknown>('/stats/feature-flags');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['feature_flags', 'data'],
      fallbackMessage: 'Failed to load feature flags'
    });
    return {
      enableVectorStore: Boolean(pickCompatField(payload, ['enable_vector_store'], true)),
      experimentalActionsEnabled: Boolean(pickCompatField(payload, ['experimental_actions_enabled'], false))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load feature flags');
  }
}
