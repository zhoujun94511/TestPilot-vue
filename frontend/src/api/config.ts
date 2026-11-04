import { ApiError, del, get, post, put } from './http';
import {
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  pickCompatField
} from './core';

export type ConfigFieldKind =
  | 'string'
  | 'number'
  | 'boolean'
  | 'select'
  | 'password'
  | 'textarea'
  | 'dedup_weights';

/** 内容去重权重 JSON 的固定字段（与后端 CONTENT_DEDUP_WEIGHTS 一致） */
export const CONTENT_DEDUP_WEIGHT_KEYS = ['title', 'steps', 'expected', 'preconditions'] as const;

export type ContentDedupWeightKey = (typeof CONTENT_DEDUP_WEIGHT_KEYS)[number];

export const DEFAULT_CONTENT_DEDUP_WEIGHTS: Record<ContentDedupWeightKey, number> = {
  title: 0.4,
  steps: 0.3,
  expected: 0.2,
  preconditions: 0.1
};

export function parseContentDedupWeights(value: unknown): Record<ContentDedupWeightKey, number> {
  const base = { ...DEFAULT_CONTENT_DEDUP_WEIGHTS };
  if (value == null || value === '') return base;
  try {
    const raw = typeof value === 'string' ? JSON.parse(value) : value;
    if (!raw || typeof raw !== 'object') return base;
    for (const key of CONTENT_DEDUP_WEIGHT_KEYS) {
      const n = Number((raw as Record<string, unknown>)[key]);
      if (!Number.isNaN(n)) base[key] = n;
    }
  } catch {
    // keep defaults
  }
  return base;
}

export function serializeContentDedupWeights(weights: Record<ContentDedupWeightKey, number>): string {
  return JSON.stringify(weights);
}

export interface ConfigCategory {
  id: string;
  name?: string;
  name_key?: string;
  description?: string;
  description_key?: string;
  icon?: string;
  priority?: number;
  raw?: Record<string, unknown>;
}

export interface ConfigOption {
  label: string;
  value: string | number | boolean;
}

export interface ConfigItem {
  id?: number;
  key: string;
  value: string | number | boolean | null;
  value_type?: string;
  category?: string;
  description?: string;
  label_key?: string;
  description_key?: string;
  is_sensitive?: boolean;
  configured?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  options?: ConfigOption[];
  inputKind: ConfigFieldKind;
  dirty?: boolean;
  touched?: boolean;
  error?: string;
  raw?: Record<string, unknown>;
}

export interface ConfigSaveResult {
  updated_count?: number;
  failed_configs?: Array<{
    key: string;
    error: string;
  }>;
}

export interface ConfigImportResult {
  imported_count?: number;
}

export interface ConfigCategoryResponse {
  success?: boolean;
  data?: ConfigCategory[];
  message?: string;
  error_code?: string;
}

export interface ConfigItemsResponse {
  success?: boolean;
  data?: ConfigItem[];
  message?: string;
  error_code?: string;
}

export interface ValidateResponse {
  success?: boolean;
  data?: {
    valid?: boolean;
    message?: string;
  };
  message?: string;
  error_code?: string;
}

export interface SaveConfigPayload {
  configs: ConfigItem[];
}

export interface ConfigAuditLogRecord {
  id?: number;
  key?: string;
  action?: string;
  operator?: string;
  old_value?: unknown;
  new_value?: unknown;
  created_at?: string | null;
  raw?: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function extractMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) return error.message || fallback;
  if (error instanceof Error) return error.message || fallback;
  return fallback;
}

function normalizeError(error: unknown, fallback: string): never {
  throw new ApiError(extractMessage(error, fallback), {
    errorCode: error instanceof ApiError ? error.errorCode : undefined,
    code: error instanceof ApiError ? error.code : undefined,
    details: error instanceof ApiError ? error.details : undefined
  });
}

function toBoolean(value: unknown): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  return ['true', '1', 'yes', 'on', 'enabled'].includes(String(value).toLowerCase());
}

function toNumber(value: unknown): number | string | null {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return value;
  const next = Number(value);
  return Number.isNaN(next) ? String(value) : next;
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function extractList<T>(payload: unknown, candidateKeys: string[]): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (!isRecord(payload)) return [];

  for (const key of candidateKeys) {
    const candidate = payload[key];
    if (Array.isArray(candidate)) {
      return candidate as T[];
    }
  }

  if ('data' in payload) {
    return extractList<T>(payload.data, candidateKeys);
  }

  if ('items' in payload) {
    return extractList<T>(payload.items, candidateKeys);
  }

  if ('configs' in payload) {
    return extractList<T>(payload.configs, candidateKeys);
  }

  return [];
}

function extractObject<T extends object>(payload: unknown): T {
  if (isRecord(payload)) return payload as T;
  return {} as T;
}

function normalizeOptions(raw: Record<string, unknown>): ConfigOption[] | undefined {
  const sources = [
    raw.options,
    raw.enum_values,
    raw.values,
    raw.choices,
    raw.validation_config && typeof raw.validation_config === 'object'
      ? (raw.validation_config as Record<string, unknown>).values
      : undefined
  ];

  for (const source of sources) {
    if (Array.isArray(source)) {
      return source
        .map((item) => {
          if (typeof item === 'object' && item !== null) {
            const entry = item as Record<string, unknown>;
            const value = entry.value ?? entry.key ?? entry.id ?? entry.label;
            if (value === undefined || value === null) return null;
            return {
              label: String(entry.label ?? entry.name ?? value),
              value: value as string | number | boolean
            };
          }
          return {
            label: String(item),
            value: item as string | number | boolean
          };
        })
        .filter(Boolean) as ConfigOption[];
    }
  }

  return undefined;
}

/** max_tokens / 会话熔断等：键名含 TOKEN 但是整数配置，不能按 API 密钥渲染 */
function isNumericTokenLimitKey(key: string): boolean {
  const normalized = key.toUpperCase();
  if (normalized === 'MAX_TOKENS' || normalized === 'TR_MAX_TOKENS') return true;
  if (normalized === 'TOKEN_MAX_PER_SESSION' || normalized === 'TOKEN_MAX_CALLS_PER_SESSION') {
    return true;
  }
  return /^TR_[A-Z0-9]+_MAX_TOKENS$/.test(normalized);
}

function isSecretConfigField(key: string, description: string): boolean {
  const upperKey = key.toUpperCase();
  if (/(?:^|_)API_KEY$|SECRET|PASSWORD|PRIVATE_KEY/.test(upperKey)) return true;
  if (/\bapi\s*key\b|api密钥|密钥|secret|password/i.test(description)) return true;
  return false;
}

function inferInputKind(raw: Record<string, unknown>): ConfigFieldKind {
  const key = String(raw.key || '');
  const description = String(raw.description || '').toLowerCase();
  const valueType = String(raw.value_type || raw.type || raw.field_type || raw.input_type || '').toLowerCase();
  const options = normalizeOptions(raw);
  const hasOptions = Boolean(options && options.length > 0);

  if (hasOptions || ['select', 'enum', 'choice'].includes(valueType)) {
    return 'select';
  }

  if (['bool', 'boolean', 'switch'].includes(valueType)) {
    return 'boolean';
  }

  if (isNumericTokenLimitKey(key) || ['int', 'integer', 'float', 'number', 'decimal'].includes(valueType)) {
    return 'number';
  }

  if (raw.is_sensitive === true || isSecretConfigField(key, description)) {
    return 'password';
  }

  if (['textarea', 'text-area', 'longtext'].includes(valueType)) {
    return 'textarea';
  }

  if (key === 'CONTENT_DEDUP_WEIGHTS') {
    return 'dedup_weights';
  }

  if (['json'].includes(valueType)) {
    return 'textarea';
  }

  if ((raw.value != null && String(raw.value).length > 120) || /\n/.test(String(raw.value ?? ''))) {
    return 'textarea';
  }

  return 'string';
}

export function normalizeCategory(raw: Record<string, unknown>): ConfigCategory {
  return {
    id: String(pickCompatField(raw, ['id', 'key', 'category'], '')),
    name: pickCompatField(raw, ['name'], undefined),
    description: pickCompatField(raw, ['description'], undefined),
    icon: pickCompatField(raw, ['icon'], undefined),
    priority: raw.priority != null ? Number(raw.priority) : undefined,
    raw
  };
}

export function normalizeConfigItem(raw: Record<string, unknown>): ConfigItem {
  const inputKind = inferInputKind(raw);
  const options = normalizeOptions(raw);
  const value = raw.value ?? null;

  return {
    id: raw.id != null ? Number(raw.id) : undefined,
    key: String(raw.key ?? ''),
    value:
      inputKind === 'boolean'
        ? toBoolean(value)
        : inputKind === 'number'
          ? toNumber(value)
          : (value as string | number | boolean | null),
    value_type: raw.value_type != null ? String(raw.value_type) : undefined,
    category: raw.category != null ? String(raw.category) : undefined,
    description: raw.description != null ? String(raw.description) : undefined,
    is_sensitive: Boolean(raw.is_sensitive),
    configured: raw.configured === true,
    created_at: raw.created_at != null ? String(raw.created_at) : undefined,
    updated_at: raw.updated_at != null ? String(raw.updated_at) : undefined,
    options,
    inputKind,
    dirty: false,
    touched: false,
    error: undefined,
    raw
  };
}

function resolveCategoryList(payload: unknown): ConfigCategory[] {
  return extractList<Record<string, unknown>>(payload, ['categories', 'items']).map((item) => normalizeCategory(item));
}

function resolveConfigList(payload: unknown): ConfigItem[] {
  return extractList<Record<string, unknown>>(payload, ['configs', 'items', 'data']).map((item) => normalizeConfigItem(item));
}

function resolveValueType(item: ConfigItem): string {
  if (item.value_type) return item.value_type;
  if (item.raw && typeof item.raw.value_type === 'string') {
    return String(item.raw.value_type);
  }

  switch (item.inputKind) {
    case 'number':
      if (typeof item.value === 'number') {
        return Number.isInteger(item.value) ? 'int' : 'float';
      }
      if (typeof item.value === 'string' && item.value.includes('.')) {
        return 'float';
      }
      return 'int';
    case 'boolean':
      return 'bool';
    case 'password':
      return 'string';
    case 'textarea':
      return 'string';
    default:
      return 'string';
  }
}

function toPayloadItem(item: ConfigItem, category: string) {
  const baseValue = item.inputKind === 'boolean' ? Boolean(item.value) : item.value;
  return {
    key: item.key,
    value: baseValue,
    value_type: resolveValueType(item),
    category: item.category || category,
    description: item.description || '',
    is_sensitive: item.is_sensitive ?? item.inputKind === 'password'
  };
}

export async function getCategories(): Promise<ConfigCategory[]> {
  try {
    const response = await get<ConfigCategoryResponse>('/config/categories');
    return resolveCategoryList(coreNormalizeResponse(response, {
      dataKeys: ['categories', 'items', 'data'],
      fallbackMessage: 'Failed to load categories'
    }));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load categories');
  }
}

export async function getConfigCategories(): Promise<ConfigCategory[]> {
  return getCategories();
}

export async function getCategoryConfig(category: string): Promise<ConfigItem[]> {
  try {
    const response = await get<ConfigItemsResponse>(`/config/${encodeURIComponent(category)}`);
    return resolveConfigList(coreNormalizeResponse(response, {
      dataKeys: ['configs', 'items', 'data'],
      fallbackMessage: 'Failed to load configuration items'
    }));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load configuration items');
  }
}

export async function getConfigsByCategory(category: string): Promise<ConfigItem[]> {
  return getCategoryConfig(category);
}

function extractSaveItems(data: SaveConfigPayload | ConfigItem[]): ConfigItem[] {
  return Array.isArray(data) ? data : data.configs;
}

export async function saveConfig(category: string, data: SaveConfigPayload | ConfigItem[]): Promise<ConfigSaveResult> {
  const items = extractSaveItems(data);

  try {
    const response = await post<{ data?: ConfigSaveResult }>(`/config/${encodeURIComponent(category)}`, {
      configs: items.map((item) => toPayloadItem(item, category))
    });
    return extractObject<ConfigSaveResult>(coreNormalizeResponse(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to save configuration'
    }));
  } catch (error) {
    coreNormalizeError(error, 'Failed to save configuration');
  }
}

export async function saveConfigsByCategory(category: string, payload: SaveConfigPayload): Promise<ConfigSaveResult> {
  return saveConfig(category, payload);
}

export async function validateConfig(key: string, value: unknown): Promise<{ valid: boolean; message?: string }> {
  try {
    const response = await post<ValidateResponse>(`/config/validate/${encodeURIComponent(key)}`, { value });
    const responseData = extractObject<{ valid?: boolean; message?: string }>(coreNormalizeResponse(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Validation failed'
    }));
    const valid = responseData.valid !== false;
    return {
      valid: Boolean(valid),
      message: responseData.message || response.message
    };
  } catch (error) {
    return {
      valid: false,
      message: extractMessage(error, 'Validation failed')
    };
  }
}

export async function validateConfigItem(key: string, value: unknown): Promise<{ valid: boolean; message?: string }> {
  return validateConfig(key, value);
}

export async function exportConfig(format: 'json' | 'yaml' = 'json'): Promise<{ content: string; filename: string; format: string }> {
  try {
    const response = await get<{ data?: { content?: string; filename?: string; format?: string } }>(`/config/export`, { format });
    const data = extractObject<{ content?: string; filename?: string; format?: string }>(coreNormalizeResponse(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to export configuration'
    }));
    return {
      content: String(data.content ?? ''),
      filename: String(data.filename ?? `config_export.${format}`),
      format: String(data.format ?? format)
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to export configuration');
  }
}

export async function exportConfigs(format: 'json' | 'yaml' = 'json') {
  return exportConfig(format);
}

export async function importConfig(file: File): Promise<ConfigImportResult> {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await post<unknown>('/config/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    const payload = extractObject<ConfigImportResult>(
      coreNormalizeResponse(response, {
        dataKeys: ['data'],
        fallbackMessage: 'Failed to import configuration'
      })
    );
    return {
      imported_count: Number(payload.imported_count ?? 0)
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to import configuration');
  }
}

export async function getConfigItem(key: string) {
  return get(`/config/item/${encodeURIComponent(key)}`);
}

export async function updateConfigItem(key: string, payload: Record<string, unknown>) {
  return put(`/config/item/${encodeURIComponent(key)}`, payload);
}

export async function deleteConfigItem(key: string) {
  return del(`/config/item/${encodeURIComponent(key)}`);
}

export async function getConfigAuditLogs(params: { limit?: number; offset?: number } = {}): Promise<ConfigAuditLogRecord[]> {
  try {
    const response = await get<unknown>('/config/audit-logs', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data', 'logs', 'items'],
      fallbackMessage: 'Failed to load config audit logs'
    });
    const logs = extractList<Record<string, unknown>>(payload, ['logs', 'items', 'data']);
    return logs.map((item) => ({
      id: item.id != null ? Number(item.id) : undefined,
      key: pickCompatField(item, ['key', 'config_key'], undefined) != null ? String(pickCompatField(item, ['key', 'config_key'], '')) : undefined,
      action: pickCompatField(item, ['action', 'operation_type'], undefined) != null ? String(pickCompatField(item, ['action', 'operation_type'], '')) : undefined,
      operator: item.operator != null ? String(item.operator) : undefined,
      old_value: item.old_value,
      new_value: item.new_value,
      created_at: pickCompatField(item, ['created_at', 'created_time'], null),
      raw: item
    }));
  } catch (error) {
    coreNormalizeError(error, 'Failed to load config audit logs');
  }
}
