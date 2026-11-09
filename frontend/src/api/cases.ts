import http, {
  ApiError,
  del,
  errorCodeFromPayload,
  get,
  LONG_TASK_TIMEOUT_MS,
  notifyPasswordChangeRequired,
  notifyUnauthorized,
  post,
  put,
  resolveProjectHeaders
} from './http';
import { authorizationHeader } from './sessionToken';
import {
  asArray as coreAsArray,
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  paginationAdapter,
  pickCompatField
} from './core';

export type CasePriority = 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
export type CaseStatus = 'draft' | 'active' | 'deprecated';
export type CaseProcessMode = 'sequential' | 'parallel';
export type CaseExportFormat = 'excel' | 'csv' | 'json';
export type CaseTemplateFormat = 'excel' | 'csv';

export interface CaseRecord {
  case_id: string;
  display_id?: string;
  title: string;
  description?: string;
  precondition?: string;
  steps: string[];
  expected_result: string[];
  priority: CasePriority | string;
  category?: string;
  tags: string[];
  status?: CaseStatus | string;
  created_time?: string | null;
  updated_time?: string | null;
  created_by?: string;
  requirement_id?: string;
  module?: string;
  test_method?: string;
  raw?: Record<string, unknown>;
}

export interface CasePagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export interface CaseListResponse {
  cases: CaseRecord[];
  pagination: CasePagination;
  total: number;
}

export interface CaseCountOption {
  value: number;
  label: string;
}

export interface CaseGenerationConfig {
  case_count_options: CaseCountOption[];
  test_type_options: Array<{ value: string; label: string }>;
  max_case_num?: number;
  max_cases_per_requirement?: number;
  default_case_count?: number;
  priority_auto_determined?: boolean;
  enable_case_generation_rag?: boolean;
  raw?: Record<string, unknown>;
}

export interface CaseStats {
  total_cases: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  raw?: Record<string, unknown>;
}

export interface CaseGeneratePayload {
  requirement_text: string;
  case_count?: number;
  category?: string;
  use_rag?: boolean;
  priority?: string;
}

export interface CaseBatchGeneratePayload {
  requirements: string[];
  case_count_per_req?: number;
  use_rag?: boolean;
  process_mode?: CaseProcessMode;
}

export interface CaseGenerateResult {
  cases: CaseRecord[];
  total: number;
  message?: string;
  generation_time?: number;
  processing_rate?: number;
  use_rag?: boolean;
  enhanced_context_length?: number;
  performance_stats?: Record<string, unknown>;
  hallucination_detection?: Record<string, unknown>;
  failed_count?: number;
  raw?: Record<string, unknown>;
}

export interface CaseBatchGenerateResult {
  cases: CaseRecord[];
  total_cases: number;
  results?: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
  message?: string;
  raw?: Record<string, unknown>;
}

export interface CaseStreamEvent {
  type: 'start' | 'requirement_done' | 'requirement_failed' | 'done' | 'error';
  index: number;
  total: number;
  savedCount: number;
  failedCount: number;
  message: string;
  cases: CaseRecord[];
}

export interface CaseExportPayload {
  category?: string;
  priority?: string;
  status?: string;
  search?: string;
  case_ids?: Array<string | number>;
}

export interface CaseUpdatePayload {
  title?: string;
  description?: string;
  precondition?: string;
  steps?: string[];
  expected_result?: string[];
  priority?: string;
  category?: string;
  tags?: string[];
  status?: string;
  module?: string;
  test_method?: string;
  updated_time?: string | null;
}

export interface CaseGenerateFromAnalysisPayload {
  requirements: object[];
  use_rag?: boolean;
}

export interface CaseExportResult {
  blob: Blob;
  filename: string;
  format: CaseExportFormat;
  mimeType?: string;
}

export interface CaseTemplateResult {
  blob: Blob;
  filename: string;
  format: CaseTemplateFormat;
  mimeType?: string;
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
    return value
      .map((item) => {
        if (typeof item === 'string') return item.trim();
        if (isRecord(item)) {
          return String(pickCompatField(item, ['description', 'text', 'content', 'title', 'name'], '')).trim();
        }
        return String(item ?? '').trim();
      })
      .filter(Boolean);
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return [];

    if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
      try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) {
          return normalizeTextArray(parsed);
        }
      } catch {
        // fall through to line splitting
      }
    }

    return trimmed.split(/\r?\n|;|,|、/g).map((item) => item.trim()).filter(Boolean);
  }

  return [];
}

function normalizeCaseRecord(raw: Record<string, unknown>): CaseRecord {
  const steps = normalizeTextArray(pickCompatField(raw, ['steps'], []));
  const expected = normalizeTextArray(pickCompatField(raw, ['expected_result', 'expected'], []));

  return {
    case_id: String(pickCompatField(raw, ['case_id', 'id'], '')),
    display_id: pickCompatField(raw, ['display_id'], undefined),
    title: String(pickCompatField(raw, ['title', 'name'], '')),
    description: pickCompatField(raw, ['description'], undefined),
    precondition: pickCompatField(raw, ['precondition', 'preconditions'], undefined),
    steps,
    expected_result: expected,
    priority: String(pickCompatField(raw, ['priority'], 'P2')) as CasePriority | string,
    category: pickCompatField(raw, ['category', 'test_type'], undefined),
    tags: normalizeTextArray(pickCompatField(raw, ['tags'], [])),
    status: pickCompatField(raw, ['status'], undefined),
    created_time: pickCompatField(raw, ['created_time', 'created_at'], null),
    updated_time: pickCompatField(raw, ['updated_time', 'updated_at'], null),
    created_by: pickCompatField(raw, ['created_by'], undefined),
    requirement_id: pickCompatField(raw, ['requirement_id'], undefined),
    module: pickCompatField(raw, ['module'], undefined),
    test_method: pickCompatField(raw, ['test_method'], undefined),
    raw
  };
}

function normalizeCaseList(payload: unknown, fallbackPage = 1, fallbackPerPage = 20): CaseListResponse {
  const normalized = isRecord(payload) ? payload : {};
  const cases = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['cases', 'items', 'data'], [])).map(normalizeCaseRecord);
  const pagination = paginationAdapter(pickCompatField(normalized, ['pagination'], {}), {
    page: Number(pickCompatField(normalized, ['page'], fallbackPage)),
    per_page: Number(pickCompatField(normalized, ['per_page'], fallbackPerPage)),
    total: Number(pickCompatField(normalized, ['total'], cases.length)),
    pages: Number(pickCompatField(normalized, ['total_pages', 'pages'], cases.length > 0 ? 1 : 0))
  });

  return {
    cases,
    pagination,
    total: Number(pickCompatField(normalized, ['total'], cases.length))
  };
}

function normalizeGenerationConfig(payload: unknown): CaseGenerationConfig {
  const normalized = isRecord(payload) ? payload : {};
  const countOptions = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['case_count_options'], []))
    .map((item) => ({
      value: Number(pickCompatField(item, ['value'], 0)),
      label: String(pickCompatField(item, ['label'], ''))
    }))
    .filter((item) => Number.isFinite(item.value) && item.value > 0);

  const testTypeOptions = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['test_type_options'], []))
    .map((item) => ({
      value: String(pickCompatField(item, ['value'], '')),
      label: String(pickCompatField(item, ['label'], ''))
    }))
    .filter((item) => Boolean(item.value));

  return {
    case_count_options: countOptions,
    test_type_options: testTypeOptions,
    max_case_num: normalized.max_case_num != null ? Number(normalized.max_case_num) : undefined,
    max_cases_per_requirement: normalized.max_cases_per_requirement != null
      ? Number(normalized.max_cases_per_requirement)
      : undefined,
    default_case_count: normalized.default_case_count != null ? Number(normalized.default_case_count) : undefined,
    priority_auto_determined: Boolean(normalized.priority_auto_determined),
    enable_case_generation_rag: Boolean(normalized.enable_case_generation_rag),
    raw: normalized
  };
}

function normalizeStats(payload: unknown): CaseStats {
  const normalized = isRecord(payload) ? payload : {};
  return {
    total_cases: Number(pickCompatField(normalized, ['total_cases', 'total'], 0)),
    by_status: isRecord(normalized.by_status) ? (normalized.by_status as Record<string, number>) : {},
    by_priority: isRecord(normalized.by_priority) ? (normalized.by_priority as Record<string, number>) : {},
    by_category: isRecord(normalized.by_category) ? (normalized.by_category as Record<string, number>) : {},
    raw: normalized
  };
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

function normalizeExportFilename(filename: string, format: CaseExportFormat) {
  if (format !== 'excel') return filename;
  const safeName = String(filename || '').trim() || 'test_cases.xlsx';
  // Excel 导出兼容 .xlsx / .xls；若缺少后缀则补默认 .xlsx
  if (/\.xlsx?$/i.test(safeName)) {
    return safeName;
  }
  return `${safeName}.xlsx`;
}

function exportPath(format: CaseExportFormat) {
  if (format === 'csv') return '/export/cases/csv';
  if (format === 'json') return '/export/cases/json';
  return '/export/cases/excel';
}

function templateFilename(format: CaseTemplateFormat) {
  return format === 'csv' ? 'test_cases_template.csv' : 'test_cases_template.xlsx';
}

function normalizeGenerateResponse(payload: Record<string, unknown>): CaseGenerateResult {
  const cases = coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['cases'], [])).map(normalizeCaseRecord);
  return {
    cases,
    total: Number(pickCompatField(payload, ['total'], cases.length)),
    message: String(pickCompatField(payload, ['message'], '')),
    generation_time: payload.generation_time != null ? Number(payload.generation_time) : undefined,
    processing_rate: payload.processing_rate != null ? Number(payload.processing_rate) : undefined,
    use_rag: pickCompatField(payload, ['use_rag'], undefined),
    enhanced_context_length: payload.enhanced_context_length != null ? Number(payload.enhanced_context_length) : undefined,
    performance_stats: isRecord(payload.performance_stats) ? payload.performance_stats : undefined,
    hallucination_detection: isRecord(payload.hallucination_detection) ? payload.hallucination_detection : undefined,
    raw: payload
  };
}

export async function listCases(params: Record<string, unknown> = {}): Promise<CaseListResponse> {
  try {
    const response = await get<unknown>('/cases/list', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load test case list'
    });
    return normalizeCaseList(payload, Number(params.page ?? 1), Number(params.per_page ?? 20));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load test case list');
  }
}

export async function getCase(caseId: string): Promise<CaseRecord> {
  try {
    const response = await get<unknown>(`/cases/${encodeURIComponent(caseId)}`);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to load test case'
    });
    return normalizeCaseRecord(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load test case');
  }
}

export async function generateCases(payload: CaseGeneratePayload): Promise<CaseGenerateResult> {
  try {
    const response = await post<unknown>('/cases/generate', payload, { timeout: LONG_TASK_TIMEOUT_MS });
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to generate test cases'
    });
    return normalizeGenerateResponse(normalized);
  } catch (error) {
    coreNormalizeError(error, 'Failed to generate test cases');
  }
}

function buildApiBase(): string {
  const base = import.meta.env.VITE_API_BASE_URL || '/api';
  return base.endsWith('/') ? base.slice(0, -1) : base;
}

async function fetchSse(url: string, body: unknown, signal?: AbortSignal): Promise<Response> {
  const response = await fetch(`${buildApiBase()}${url}`, {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      'Accept-Language': localStorage.getItem('testpilot_locale') || 'zh-CN',
      'X-Requested-With': 'XMLHttpRequest',
      ...authorizationHeader(),
      ...(await resolveProjectHeaders())
    },
    credentials: 'include',
    body: JSON.stringify(body)
  });
  if (!response.ok || !response.body) {
    notifyUnauthorized(response.status, url);
    let errorMessage = `HTTP ${response.status}`;
    let errorCode: string | undefined;
    try {
      const payload = await response.json();
      if (isRecord(payload)) {
        notifyPasswordChangeRequired(response.status, payload.code);
        const message = pickCompatField(payload, ['message', 'error'], '');
        if (message) errorMessage = String(message);
        errorCode = errorCodeFromPayload(payload);
      }
    } catch {
      // 保留 HTTP 状态说明
    }
    throw new ApiError(errorMessage, { code: response.status, errorCode });
  }
  return response;
}

async function* readSse(response: Response): AsyncGenerator<Record<string, unknown>> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: !done });
      if (done) {
        buffer += decoder.decode();
        if (buffer.trim() && !buffer.endsWith('\n\n')) buffer += '\n\n';
      }
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
        try {
          const parsed = JSON.parse(dataLine) as unknown;
          if (isRecord(parsed)) yield parsed;
        } catch {
          yield { type: 'error', message: dataLine };
        }
      }
      if (done) break;
    }
  } finally {
    // 调用方中途 break 时要取消底层流，否则连接会一直挂到服务端结束
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

function toStreamEvent(raw: Record<string, unknown>): CaseStreamEvent {
  const typeValue = String(pickCompatField(raw, ['type'], 'error'));
  const type = (
    typeValue === 'start' || typeValue === 'requirement_done' || typeValue === 'requirement_failed' || typeValue === 'done'
      ? typeValue
      : 'error'
  ) as CaseStreamEvent['type'];
  return {
    type,
    index: Number(pickCompatField(raw, ['index'], 0)),
    total: Number(pickCompatField(raw, ['total'], 0)),
    savedCount: Number(pickCompatField(raw, ['saved_count'], 0)),
    failedCount: Number(pickCompatField(raw, ['failed_count'], 0)),
    message: String(pickCompatField(raw, ['message'], '')),
    cases: coreAsArray<Record<string, unknown>>(pickCompatField(raw, ['cases'], [])).map(normalizeCaseRecord)
  };
}

export async function streamBatchGenerateCases(
  payload: { requirements: Array<string | object>; case_count_per_req?: number },
  onEvent?: (event: CaseStreamEvent) => void,
  signal?: AbortSignal
): Promise<CaseBatchGenerateResult> {
  const response = await fetchSse('/cases/batch-generate/stream', payload, signal);
  const cases: CaseRecord[] = [];
  let savedCount = 0;
  let failedCount = 0;
  let message = '';
  for await (const raw of readSse(response)) {
    const event = toStreamEvent(raw);
    savedCount = event.savedCount;
    failedCount = event.failedCount;
    if (event.message) message = event.message;
    if (event.type === 'requirement_done') cases.push(...event.cases);
    onEvent?.(event);
    if (event.type === 'error') {
      throw new ApiError(event.message || 'Batch generation failed');
    }
  }
  return {
    cases,
    total_cases: savedCount || cases.length,
    message,
    summary: { failed_count: failedCount }
  };
}

export async function batchGenerateCases(payload: CaseBatchGeneratePayload): Promise<CaseBatchGenerateResult> {
  try {
    const response = await post<unknown>('/cases/batch-generate', payload, { timeout: LONG_TASK_TIMEOUT_MS });
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to batch generate test cases'
    });
    const cases = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['cases', 'saved_cases'], []))
      .map(normalizeCaseRecord);
    return {
      cases,
      total_cases: Number(pickCompatField(normalized, ['total_cases', 'total'], cases.length)),
      results: coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['results'], [])),
      summary: isRecord(normalized.summary) ? normalized.summary : undefined,
      message: String(pickCompatField(normalized, ['message'], '')),
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to batch generate test cases');
  }
}

export async function getCaseStats(): Promise<CaseStats> {
  try {
    const response = await get<unknown>('/cases/stats');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['stats', 'data'],
      fallbackMessage: 'Failed to load test case statistics'
    });
    return normalizeStats(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load test case statistics');
  }
}

export async function getCaseConfig(): Promise<CaseGenerationConfig> {
  try {
    const response = await get<unknown>('/cases/config');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['config', 'data'],
      fallbackMessage: 'Failed to load test case config'
    });
    return normalizeGenerationConfig(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load test case config');
  }
}

export async function updateCase(caseId: string, payload: CaseUpdatePayload): Promise<CaseRecord> {
  try {
    const response = await put<unknown>(`/cases/${encodeURIComponent(caseId)}`, payload);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['case', 'data'],
      fallbackMessage: 'Failed to update test case'
    });
    return normalizeCaseRecord(normalized);
  } catch (error) {
    coreNormalizeError(error, 'Failed to update test case');
  }
}

export async function deleteCase(caseId: string): Promise<{ success: boolean; raw?: Record<string, unknown> }> {
  try {
    const response = await del<unknown>(`/cases/${encodeURIComponent(caseId)}`);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to delete test case'
    });
    return {
      success: true,
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to delete test case');
  }
}

export async function exportCases(payload: CaseExportPayload = {}, format: CaseExportFormat = 'excel'): Promise<CaseExportResult> {
  try {
    const response = await http.request<Blob>({
      url: exportPath(format),
      method: 'POST',
      data: payload,
      responseType: 'blob',
      timeout: LONG_TASK_TIMEOUT_MS
    });

    const blob = response.data as Blob;
    const headers = response.headers || {};
    return {
      blob,
      filename: normalizeExportFilename(
        parseFilename(headers, `test_cases.${format === 'excel' ? 'xlsx' : format}`),
        format
      ),
      format,
      mimeType: String(pickCompatField(headers, ['content-type', 'Content-Type'], ''))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to export test cases');
  }
}

export async function downloadCasesTemplate(format: CaseTemplateFormat = 'excel'): Promise<CaseTemplateResult> {
  try {
    const response = await http.request<Blob>({
      url: '/export/template/cases',
      method: 'GET',
      params: { type: format },
      responseType: 'blob',
      timeout: LONG_TASK_TIMEOUT_MS
    });

    const blob = response.data as Blob;
    const headers = response.headers || {};
    return {
      blob,
      filename: parseFilename(headers, templateFilename(format)),
      format,
      mimeType: String(pickCompatField(headers, ['content-type', 'Content-Type'], ''))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to download test case template');
  }
}

export async function generateCasesFromAnalysis(payload: CaseGenerateFromAnalysisPayload): Promise<CaseGenerateResult> {
  try {
    const response = await post<unknown>('/cases/generate-from-analysis', payload, { timeout: LONG_TASK_TIMEOUT_MS });
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to generate test cases from analysis'
    });
    const cases = coreAsArray<Record<string, unknown>>(pickCompatField(normalized, ['cases'], [])).map(normalizeCaseRecord);
    return {
      cases,
      total: Number(pickCompatField(normalized, ['total'], cases.length)),
      message: String(pickCompatField(normalized, ['message'], '')),
      failed_count: Number(pickCompatField(normalized, ['failed_count'], 0)),
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to generate test cases from analysis');
  }
}
