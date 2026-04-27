import http, { download, get } from './http';
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
  message: string;
  time?: string | null;
  icon?: string;
  color?: string;
  raw?: Record<string, unknown>;
}

export interface RecentActivitiesResponse {
  activities: RecentActivityRecord[];
  raw?: Record<string, unknown>;
}

export interface DashboardSummary {
  overview: OverviewStats | null;
  health: HealthStatus | null;
  system: SystemStatus | null;
  activities: RecentActivitiesResponse | null;
  errors: Partial<Record<'overview' | 'health' | 'system' | 'activities' | 'network', string>>;
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
  summary?: {
    total_tokens?: number;
    avg_tokens_per_message?: number;
    total_messages?: number;
  };
  by_model?: Array<{ model?: string; total_tokens?: number; message_count?: number }>;
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
  cases?: Array<Record<string, unknown>>;
  case_formats?: Array<'excel' | 'csv' | 'json'>;
  export_requirements?: boolean;
  requirements?: Array<Record<string, unknown>>;
  export_chat?: boolean;
  chat_history?: Array<Record<string, unknown>>;
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
  const normalized = isRecord(payload) ? payload : {};
  const activities = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['activities', 'items', 'data'], []))
    .map((raw) => ({
      type: String(pickCompatField(raw, ['type'], 'unknown')),
      message: String(pickCompatField(raw, ['message'], '')),
      time: pickCompatField(raw, ['time', 'timestamp', 'created_time'], null),
      icon: pickCompatField(raw, ['icon'], undefined),
      color: pickCompatField(raw, ['color'], undefined),
      raw
    }));

  return { activities, raw: normalized };
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

function extractActivitiesPayload(payload: unknown): unknown {
  if (!isRecord(payload)) return payload;
  return pickCompatField(payload, ['activities', 'data'], payload);
}

function fallbackDashboardError(message: string): string {
  return message;
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

export async function getHealthStatus(): Promise<HealthStatus> {
  try {
    const response = await get<unknown>('/stats/health');
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
      dataKeys: ['activities', 'data'],
      fallbackMessage: 'Failed to load recent activities'
    });
    return normalizeRecentActivities(extractActivitiesPayload(payload));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load recent activities');
  }
}

export async function getSystemStatus(): Promise<SystemStatus> {
  try {
    const response = await get<unknown>('/stats/system-status');
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

export async function getTokenStats(params: Record<string, unknown> = {}): Promise<TokenStatsResponse> {
  try {
    const response = await get<unknown>('/stats/tokens', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['tokens', 'data'],
      fallbackMessage: 'Failed to load token stats'
    });
    return {
      period_days: payload.period_days != null ? Number(payload.period_days) : undefined,
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
    responseType: 'blob'
  });
  return response.data as Blob;
}

export async function getNetworkInfo(): Promise<NetworkInfoResponse> {
  try {
    const response = await get<unknown>('/stats/network/info');
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

export async function loadDashboardSummary(): Promise<DashboardSummary> {
  const settled = await Promise.allSettled([
    getOverviewStats(),
    getHealthStatus(),
    getSystemStatus(),
    getRecentActivities()
  ]);

  const [overviewResult, healthResult, systemResult, activitiesResult] = settled;

  const errors: DashboardSummary['errors'] = {};

  const overview = overviewResult.status === 'fulfilled' ? overviewResult.value : null;
  if (overviewResult.status === 'rejected') errors.overview = fallbackDashboardError(overviewResult.reason instanceof Error ? overviewResult.reason.message : 'Failed to load dashboard overview');

  const health = healthResult.status === 'fulfilled' ? healthResult.value : null;
  if (healthResult.status === 'rejected') errors.health = fallbackDashboardError(healthResult.reason instanceof Error ? healthResult.reason.message : 'Failed to load system health');

  const system = systemResult.status === 'fulfilled' ? systemResult.value : null;
  if (systemResult.status === 'rejected') errors.system = fallbackDashboardError(systemResult.reason instanceof Error ? systemResult.reason.message : 'Failed to load system status');

  const activities = activitiesResult.status === 'fulfilled' ? activitiesResult.value : null;
  if (activitiesResult.status === 'rejected') errors.activities = fallbackDashboardError(activitiesResult.reason instanceof Error ? activitiesResult.reason.message : 'Failed to load recent activities');

  return {
    overview,
    health,
    system,
    activities,
    errors
  };
}
