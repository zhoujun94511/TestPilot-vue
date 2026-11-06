import { publicFileLabel } from '@/lib/public-file-label';
import { ApiError, del, get, LONG_TASK_TIMEOUT_MS, post, put } from './http';
import {
  asArray as coreAsArray,
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  paginationAdapter,
  pickCompatField
} from './core';

export type KnowledgeCategory =
  | 'test_cases'
  | 'requirements'
  | 'business_rules'
  | 'best_practices'
  | 'templates'
  | 'other';

export interface KnowledgeFileRecord {
  id: number;
  file_name: string;
  filename?: string;
  file_path?: string;
  file_type?: string;
  file_size?: number;
  description?: string;
  category?: KnowledgeCategory | string;
  status?: string;
  document_count?: number;
  created_time?: string | null;
  updated_time?: string | null;
  is_duplicate?: boolean;
  raw?: Record<string, unknown>;
}

export interface KnowledgeSearchResult {
  content: string;
  score?: number;
  file_id?: number;
  file_name?: string;
  source?: string;
  chunk_index?: number;
  metadata?: Record<string, unknown>;
  relevance?: string;
  raw?: Record<string, unknown>;
}

export interface KnowledgeStats {
  total_files: number;
  total_chunks: number;
  storage_size: number;
  last_update?: string | null;
  category_distribution?: Record<string, number>;
  upload_trend?: Array<{ date: string; count: number }>;
  raw?: Record<string, unknown>;
}

export interface KnowledgePagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export interface KnowledgeListResponse {
  files: KnowledgeFileRecord[];
  pagination: KnowledgePagination;
}

export interface KnowledgeSearchResponse {
  documents: KnowledgeSearchResult[];
  total: number;
  query: string;
  pagination: KnowledgePagination;
}

export interface KnowledgeUploadResponse {
  success?: boolean;
  file_info?: KnowledgeFileRecord & Record<string, unknown>;
  summary?: {
    total?: number;
    success_count?: number;
    failed_count?: number;
  };
  results?: Array<Record<string, unknown>>;
  message?: string;
  [key: string]: unknown;
}

export interface KnowledgeFileDetailResponse {
  file_detail: KnowledgeFileRecord & {
    preview?: string;
    preview_type?: string;
    preview_truncated?: boolean;
    chunk_count?: number;
  };
}

export interface KnowledgeDeleteResponse {
  deleted_count?: number;
  failed_count?: number;
  message?: string;
  [key: string]: unknown;
}

export interface KnowledgeRebuildResponse {
  rebuild_info?: Record<string, unknown>;
  message?: string;
  [key: string]: unknown;
}

export interface KnowledgeUploadPayload {
  file: File;
  category?: string;
  description?: string;
  relative_path?: string;
}

export interface KnowledgeRebuildPayload {
  clear_all?: boolean;
}

export interface KnowledgeConfig {
  max_file_size?: number;
  max_total_size?: number;
  allowed_extensions?: string[];
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

function extractData<T>(payload: unknown, keys: string[]): T {
  if (isRecord(payload)) {
    for (const key of keys) {
      if (key in payload) {
        return payload[key] as T;
      }
    }
    if ('data' in payload) {
      return extractData<T>(payload.data, keys);
    }
  }
  return undefined as T;
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function normalizeFileRecord(raw: Record<string, unknown>): KnowledgeFileRecord {
  return {
    id: Number(pickCompatField(raw, ['id', 'file_id'], 0)),
    file_name: String(pickCompatField(raw, ['file_name', 'filename', 'name'], '')),
    filename: pickCompatField(raw, ['filename'], undefined),
    file_path: pickCompatField(raw, ['file_path'], undefined),
    file_type: pickCompatField(raw, ['file_type'], undefined),
    file_size: raw.file_size != null ? Number(raw.file_size) : undefined,
    description: pickCompatField(raw, ['description'], undefined),
    category: pickCompatField(raw, ['category'], undefined),
    status: pickCompatField(raw, ['status'], undefined),
    document_count: raw.document_count != null ? Number(raw.document_count) : undefined,
    created_time: pickCompatField(raw, ['created_time'], undefined),
    updated_time: pickCompatField(raw, ['updated_time'], undefined),
    is_duplicate: Boolean(raw.is_duplicate),
    raw
  };
}

function displayFileField(value: unknown) {
  if (value == null || value === '') return undefined;
  const label = publicFileLabel(String(value));
  return label || undefined;
}

function normalizeSearchResult(raw: Record<string, unknown>): KnowledgeSearchResult {
  const metadata = isRecord(raw.metadata) ? { ...raw.metadata } : {};
  if (typeof metadata.source === 'string') metadata.source = publicFileLabel(metadata.source);
  if (typeof metadata.file_path === 'string') metadata.file_path = publicFileLabel(metadata.file_path);
  if (typeof metadata.file_name === 'string') metadata.file_name = publicFileLabel(metadata.file_name);
  const fileName = displayFileField(
    pickCompatField(raw, ['file_name'], metadata.file_name != null ? String(metadata.file_name) : undefined)
  );
  const source = displayFileField(
    pickCompatField(raw, ['source'], metadata.source != null ? String(metadata.source) : undefined)
  );
  return {
    content: String(pickCompatField(raw, ['content', 'text', 'chunk'], '')),
    score: raw.score != null ? Number(raw.score) : undefined,
    file_id: raw.file_id != null ? Number(raw.file_id) : undefined,
    file_name: fileName,
    source,
    metadata,
    relevance: pickCompatField(raw, ['relevance'], undefined),
    raw
  };
}

function normalizeStats(raw: Record<string, unknown>): KnowledgeStats {
  return {
    total_files: Number(pickCompatField(raw, ['total_files', 'total_documents'], 0)),
    total_chunks: Number(pickCompatField(raw, ['total_chunks'], 0)),
    storage_size: Number(pickCompatField(raw, ['storage_size', 'database_size'], 0)),
    last_update: pickCompatField(raw, ['last_update', 'last_updated'], null),
    category_distribution: isRecord(raw.category_distribution)
      ? (raw.category_distribution as Record<string, number>)
      : isRecord(raw.category_stats)
        ? (raw.category_stats as Record<string, number>)
        : undefined,
    upload_trend: coreAsArray<{ date: string; count: number }>(raw.upload_trend),
    raw
  };
}

function isSuccess(payload: unknown): boolean {
  if (!isRecord(payload)) return false;
  if (payload.success === false) return false;
  if (payload.code !== undefined && Number(payload.code) !== 0) return false;
  return true;
}

export async function listKnowledge(params: Record<string, unknown> = {}): Promise<KnowledgeListResponse> {
  try {
    const response = await get<unknown>('/knowledge/list', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to load knowledge files'
    });
    const filesRaw = coreAsArray<Record<string, unknown>>(
      pickCompatField(payload, ['files', 'items', 'data'], [])
    );
    const files = filesRaw.map(normalizeFileRecord);
    const pagination = paginationAdapter(pickCompatField(payload, ['pagination'], {}), {
      page: Number(params.page ?? 1),
      per_page: Number(params.per_page ?? 20),
      total: files.length,
      pages: 1
    }) as KnowledgePagination;

    return { files, pagination };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load knowledge files');
  }
}

export async function searchKnowledge(params: {
  query: string;
  top_k?: number;
  limit?: number;
  score_threshold?: number;
  page?: number;
  per_page?: number;
}): Promise<KnowledgeSearchResponse> {
  try {
    const page = Number(params.page ?? 1);
    const perPage = Number(params.per_page ?? 10);
    const response = await post<unknown>('/knowledge/search', {
      query: params.query,
      top_k: params.top_k ?? params.limit,
      score_threshold: params.score_threshold,
      page,
      per_page: perPage
    });

    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to search knowledge base'
    });
    const documents = coreAsArray<Record<string, unknown>>(
      pickCompatField(payload, ['documents', 'results', 'items', 'data'], [])
    ).map(normalizeSearchResult);
    const total = Number(pickCompatField(payload, ['total'], documents.length));
    const pagination = paginationAdapter(pickCompatField(payload, ['pagination'], {}), {
      page,
      per_page: perPage,
      total,
      pages: total > 0 ? Math.ceil(total / Math.max(perPage, 1)) : 0
    }) as KnowledgePagination;

    return {
      documents,
      total,
      query: String(pickCompatField(payload, ['query'], params.query)),
      pagination
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to search knowledge base');
  }
}

export async function uploadKnowledge(
  formData: FormData,
  options?: { onUploadProgress?: (percent: number) => void }
): Promise<KnowledgeUploadResponse> {
  try {
    const response = await post<unknown>('/knowledge/upload', formData, {
      timeout: LONG_TASK_TIMEOUT_MS,
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (!options?.onUploadProgress) return;
        const total = event.total || 0;
        if (!total) return;
        const percent = Math.max(0, Math.min(100, Math.round((event.loaded / total) * 100)));
        options.onUploadProgress(percent);
      }
    });
    return coreNormalizeResponse<KnowledgeUploadResponse>(response, {
      fallbackMessage: 'Failed to upload knowledge file'
    });
  } catch (error) {
    coreNormalizeError(error, 'Failed to upload knowledge file');
  }
}

export async function getKnowledgeFileDetail(fileId: number): Promise<KnowledgeFileDetailResponse['file_detail']> {
  try {
    const response = await get<unknown>(`/knowledge/${fileId}`);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data'],
      fallbackMessage: 'Failed to load knowledge file detail'
    });
    const detailRaw = pickCompatField(payload, ['file_detail', 'file', 'data'], {}) as Record<string, unknown>;
    const detail = normalizeFileRecord(detailRaw) as KnowledgeFileDetailResponse['file_detail'];
    detail.preview = pickCompatField(detailRaw, ['preview'], undefined);
    detail.preview_type = pickCompatField(detailRaw, ['preview_type'], 'text');
    detail.preview_truncated = Boolean(pickCompatField(detailRaw, ['preview_truncated'], false));
    detail.chunk_count = Number(pickCompatField(detailRaw, ['chunk_count', 'document_count'], 0));
    return detail;
  } catch (error) {
    coreNormalizeError(error, 'Failed to load knowledge file detail');
  }
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  try {
    const response = await get<unknown>('/knowledge/stats');
    const statsRaw = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['stats', 'statistics', 'data'],
      fallbackMessage: 'Failed to load knowledge statistics'
    }) || {};
    return normalizeStats(statsRaw);
  } catch (error) {
    coreNormalizeError(error, 'Failed to load knowledge statistics');
  }
}

export async function batchDeleteKnowledge(ids: number[]): Promise<KnowledgeDeleteResponse> {
  try {
    const response = await post<unknown>('/knowledge/batch-delete', { file_ids: ids });
    return coreNormalizeResponse<KnowledgeDeleteResponse>(response, {
      fallbackMessage: 'Failed to delete knowledge files'
    });
  } catch (error) {
    coreNormalizeError(error, 'Failed to delete knowledge files');
  }
}

export async function rebuildKnowledgeIndex(payload: KnowledgeRebuildPayload = {}): Promise<KnowledgeRebuildResponse> {
  try {
    const response = await post<unknown>('/knowledge/rebuild', payload, { timeout: LONG_TASK_TIMEOUT_MS });
    return coreNormalizeResponse<KnowledgeRebuildResponse>(response, {
      fallbackMessage: 'Failed to rebuild knowledge index'
    });
  } catch (error) {
    coreNormalizeError(error, 'Failed to rebuild knowledge index');
  }
}

export interface KnowledgeFileUpdatePayload {
  description?: string;
  category?: string;
}

export async function updateKnowledgeFile(
  fileId: number,
  payload: KnowledgeFileUpdatePayload
): Promise<KnowledgeFileRecord> {
  try {
    const response = await put<unknown>(`/knowledge/${fileId}`, payload);
    const normalized = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['data', 'file'],
      fallbackMessage: 'Failed to update knowledge file'
    });
    const raw = isRecord(normalized) ? normalized : {};
    const merged = {
      ...raw,
      id: fileId,
      description: pickCompatField(raw, ['description'], payload.description),
      category: pickCompatField(raw, ['category'], payload.category)
    };
    return normalizeFileRecord(merged as Record<string, unknown>);
  } catch (error) {
    coreNormalizeError(error, 'Failed to update knowledge file');
  }
}

export async function getKnowledgeConfig(): Promise<KnowledgeConfig> {
  try {
    const response = await get<unknown>('/knowledge/config');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      dataKeys: ['config', 'data'],
      fallbackMessage: 'Failed to load knowledge config'
    });
    return {
      max_file_size: payload.max_file_size != null ? Number(payload.max_file_size) : undefined,
      max_total_size: payload.max_total_size != null ? Number(payload.max_total_size) : undefined,
      allowed_extensions: coreAsArray<string>(pickCompatField(payload, ['allowed_extensions'], []))
        .map((item) => String(item || '').trim().toLowerCase())
        .filter(Boolean),
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load knowledge config');
  }
}
