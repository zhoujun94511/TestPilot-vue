import http, { del, get, post, put } from './http';
import {
  asArray as coreAsArray,
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  paginationAdapter,
  pickCompatField
} from './core';
import { generateCasesFromAnalysis as generateCasesFromAnalysisApi, type CaseRecord } from './cases';

export type DocumentAnalysisType = 'requirements' | 'test_points' | 'business_rules' | 'comprehensive';

export interface DocumentRecord {
  id: string | number;
  document_key: string;
  filename: string;
  original_filename?: string;
  display_name?: string;
  file_name?: string;
  file_path?: string;
  relative_path?: string;
  analysis_path: string;
  file_type?: string;
  file_size?: number;
  created_time?: string | null;
  updated_time?: string | null;
  status?: string;
  analysis_status?: string;
  analysis_type?: DocumentAnalysisType | string | null;
  description?: string;
  requirements_count?: number;
  functional_count?: number;
  business_count?: number;
  document_count?: number;
  raw?: Record<string, unknown>;
}

export interface DocumentPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export interface DocumentListResponse {
  documents: DocumentRecord[];
  pagination: DocumentPagination;
  total: number;
}

export interface UploadedDocumentInfo {
  filename: string;
  file_path: string;
  size?: number;
  document_key: string;
  analysis_path: string;
  raw: Record<string, unknown>;
}

export interface DocumentUploadResponse {
  file_info?: UploadedDocumentInfo;
  message?: string;
  raw?: Record<string, unknown>;
}

export interface DocumentRequirementRecord {
  req_id: string;
  title: string;
  content: string;
  type?: string;
  priority?: string;
  category?: string;
  status?: string;
  source_file?: string;
  is_test_point?: boolean;
  is_business_rule?: boolean;
  raw?: Record<string, unknown>;
}

export interface DocumentRequirementListResponse {
  requirements: DocumentRequirementRecord[];
  pagination: DocumentPagination;
  total: number;
}

export interface DocumentAnalysisSummary {
  requirements_count?: number;
  test_points_count?: number;
  business_rules_count?: number;
  total_count?: number;
}

export interface DocumentAnalysisResult {
  success?: boolean;
  message?: string;
  analysis_type?: DocumentAnalysisType | string;
  requirements: DocumentRequirementRecord[];
  test_points: DocumentRequirementRecord[];
  business_rules: DocumentRequirementRecord[];
  saved_requirements: DocumentRequirementRecord[];
  summary?: DocumentAnalysisSummary;
  tokens_used?: number;
  analysis_time?: number;
  content_length?: number;
  raw_response?: unknown;
  raw?: Record<string, unknown>;
}

export interface DocumentAnalysisPayload {
  file_path?: string;
  content?: string;
  analysis_type?: DocumentAnalysisType;
}

export interface RequirementUpdatePayload {
  title?: string;
  content?: string;
  type?: string;
  priority?: string;
  status?: string;
}

export interface DocumentRequirementsQuery {
  page?: number;
  per_page?: number;
  type?: string;
  priority?: string;
  status?: string;
  source_file?: string;
  search?: string;
}

export interface DocumentGenerateCasesPayload {
  requirements: DocumentRequirementRecord[];
  use_rag?: boolean;
}

export interface DocumentPreviewResult {
  content: string;
  content_type?: string;
  filename?: string;
  file_size?: number;
  file_type?: string;
  is_truncated?: boolean;
  raw?: Record<string, unknown>;
}

export interface GenerateCasesResponse {
  cases?: CaseRecord[];
  total?: number;
  message?: string;
  failed_count?: number;
  summary?: Record<string, unknown>;
  raw?: Record<string, unknown>;
}

export interface DocumentRequirementsExportResult {
  blob: Blob;
  filename: string;
  mimeType?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeDocumentRecord(raw: Record<string, unknown>): DocumentRecord {
  const filename = String(pickCompatField(raw, ['filename', 'file_name', 'name'], ''));
  const relativePath = String(pickCompatField(raw, ['relative_path'], filename));
  const filePath = String(pickCompatField(raw, ['file_path'], ''));
  return {
    id: pickCompatField(raw, ['id', 'document_id'], filename),
    document_key: filename || relativePath || filePath || String(pickCompatField(raw, ['id', 'document_id'], '')),
    filename,
    original_filename: pickCompatField(raw, ['original_filename'], undefined),
    display_name: pickCompatField(raw, ['display_name', 'original_filename'], filename),
    file_name: pickCompatField(raw, ['file_name', 'display_name', 'original_filename'], filename),
    file_path: filePath || undefined,
    relative_path: relativePath || undefined,
    analysis_path: filePath || (filename ? `documents/${filename}` : relativePath) || filename,
    file_type: pickCompatField(raw, ['file_type'], undefined),
    file_size: raw.file_size != null ? Number(raw.file_size) : undefined,
    created_time: pickCompatField(raw, ['created_time', 'created_at'], null),
    updated_time: pickCompatField(raw, ['updated_time', 'updated_at'], null),
    status: pickCompatField(raw, ['status', 'analysis_status'], undefined),
    analysis_status: pickCompatField(raw, ['analysis_status', 'status'], undefined),
    analysis_type: pickCompatField(raw, ['analysis_type'], null) as DocumentAnalysisType | null,
    description: pickCompatField(raw, ['description'], undefined),
    requirements_count: raw.requirements_count != null ? Number(raw.requirements_count) : undefined,
    functional_count: raw.functional_count != null ? Number(raw.functional_count) : undefined,
    business_count: raw.business_count != null ? Number(raw.business_count) : undefined,
    document_count: raw.document_count != null ? Number(raw.document_count) : undefined,
    raw
  };
}

function normalizeRequirementRecord(raw: Record<string, unknown>, index = 0, options: Partial<DocumentRequirementRecord> = {}): DocumentRequirementRecord {
  const reqId = String(pickCompatField(raw, ['req_id', 'id', 'requirement_id'], options.req_id || `REQ_${index + 1}`));
  return {
    req_id: reqId,
    title: String(pickCompatField(raw, ['title', 'name', 'summary'], options.title || `Requirement ${index + 1}`)),
    content: String(pickCompatField(raw, ['content', 'description', 'text'], options.content || '')),
    type: String(pickCompatField(raw, ['type', 'kind'], options.type || 'functional')),
    priority: String(pickCompatField(raw, ['priority'], options.priority || 'medium')),
    category: String(pickCompatField(raw, ['category'], options.category || '')),
    status: String(pickCompatField(raw, ['status'], options.status || '')),
    source_file: String(pickCompatField(raw, ['source_file', 'source'], options.source_file || '')),
    is_test_point: Boolean(pickCompatField(raw, ['is_test_point'], options.is_test_point || false)),
    is_business_rule: Boolean(pickCompatField(raw, ['is_business_rule'], options.is_business_rule || false)),
    raw
  };
}

function normalizeRequirementArray(items: unknown, options: Partial<DocumentRequirementRecord> = {}): DocumentRequirementRecord[] {
  return coreAsArray<Record<string, unknown>>(items).map((item, index) => normalizeRequirementRecord(item, index, options));
}

function normalizeAnalysisResult(payload: Record<string, unknown>): DocumentAnalysisResult {
  const analysisType = String(pickCompatField(payload, ['analysis_type'], 'requirements'));
  const requirements = normalizeRequirementArray(pickCompatField(payload, ['requirements', 'saved_requirements'], []), {
    category: analysisType
  });
  const testPoints = normalizeRequirementArray(pickCompatField(payload, ['test_points'], []), {
    is_test_point: true,
    type: 'functional',
    category: 'test_point'
  });
  const businessRules = normalizeRequirementArray(pickCompatField(payload, ['business_rules'], []), {
    is_business_rule: true,
    type: 'business',
    category: 'business_rule'
  });
  const savedRequirements = normalizeRequirementArray(pickCompatField(payload, ['saved_requirements'], []), {
    category: analysisType
  });

  const combinedRequirements =
    analysisType === 'comprehensive'
      ? [...requirements, ...testPoints, ...businessRules]
      : requirements.length > 0
        ? requirements
        : savedRequirements.length > 0
          ? savedRequirements
          : analysisType === 'test_points'
            ? testPoints.map((item, index) => ({
                ...item,
                req_id: item.req_id || `TP_${index + 1}`,
                is_test_point: true
              }))
            : analysisType === 'business_rules'
              ? businessRules.map((item, index) => ({
                  ...item,
                  req_id: item.req_id || `BR_${index + 1}`,
                  is_business_rule: true
                }))
              : [...requirements, ...testPoints, ...businessRules];

  return {
    success: Boolean(payload.success),
    message: String(pickCompatField(payload, ['message'], '')),
    analysis_type: analysisType,
    requirements: combinedRequirements,
    test_points: testPoints,
    business_rules: businessRules,
    saved_requirements: savedRequirements,
    summary: isRecord(payload.summary)
      ? {
          requirements_count: payload.summary.requirements_count != null ? Number(payload.summary.requirements_count) : undefined,
          test_points_count: payload.summary.test_points_count != null ? Number(payload.summary.test_points_count) : undefined,
          business_rules_count: payload.summary.business_rules_count != null ? Number(payload.summary.business_rules_count) : undefined,
          total_count: payload.summary.total_count != null ? Number(payload.summary.total_count) : undefined
        }
      : undefined,
    tokens_used: payload.tokens_used != null ? Number(payload.tokens_used) : undefined,
    analysis_time: payload.analysis_time != null ? Number(payload.analysis_time) : undefined,
    content_length: payload.content_length != null ? Number(payload.content_length) : undefined,
    raw_response: pickCompatField(payload, ['raw_response'], undefined),
    raw: payload
  };
}

function extractMessage(payload: unknown, fallback: string) {
  if (isRecord(payload)) {
    return String(pickCompatField(payload, ['message'], fallback));
  }
  return fallback;
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

export async function listDocuments(
  params: DocumentRequirementsQuery & { page?: number; per_page?: number; analysis_type?: DocumentAnalysisType | string } = {}
): Promise<DocumentListResponse> {
  try {
    const response = await get<unknown>('/documents/list', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load document list'
    });
    const documents = coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['documents', 'items', 'data'], [])).map((raw) => normalizeDocumentRecord(raw));
    const pagination = paginationAdapter(pickCompatField(payload, ['pagination'], {}), {
      page: Number(params.page ?? 1),
      per_page: Number(params.per_page ?? 10),
      total: documents.length,
      pages: documents.length > 0 ? 1 : 0
    });
    return {
      documents,
      pagination,
      total: Number(pickCompatField(payload, ['total'], documents.length))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load document list');
  }
}

export async function uploadDocument(formData: FormData): Promise<DocumentUploadResponse> {
  try {
    const response = await post<unknown>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to upload document'
    });
    const nestedRaw = pickCompatField(payload, ['data'], undefined);
    const nestedData = isRecord(nestedRaw) ? nestedRaw : undefined;
    const fileInfoRaw = pickCompatField(payload, ['file_info'], undefined);
    const fileInfo = isRecord(fileInfoRaw) ? fileInfoRaw : nestedData ?? payload;
    const filename = String(pickCompatField(fileInfo, ['filename', 'file_name', 'name'], ''));
    const displayName = String(
      pickCompatField(fileInfo, ['display_name', 'original_filename'], filename)
    );
    const filePath = String(pickCompatField(fileInfo, ['file_path'], ''));
    return {
      file_info: {
        filename,
        file_path: filePath,
        size: fileInfo.size != null ? Number(fileInfo.size) : undefined,
        document_key: filename || filePath,
        analysis_path: filePath || (filename ? `documents/${filename}` : ''),
        raw: { ...fileInfo, display_name: displayName, original_filename: displayName }
      },
      message: extractMessage(response, 'Failed to upload document'),
      raw: isRecord(response) ? response : undefined
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to upload document');
  }
}

export async function analyzeDocument(payload: DocumentAnalysisPayload): Promise<DocumentAnalysisResult> {
  try {
    const response = await post<unknown>('/documents/analyze', payload);
    const rawPayload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to analyze document'
    });
    return normalizeAnalysisResult(rawPayload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to analyze document');
  }
}

export async function getDocumentRequirements(params: DocumentRequirementsQuery = {}): Promise<DocumentRequirementListResponse> {
  try {
    const response = await get<unknown>('/documents/requirements', params);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load document requirements'
    });
    const requirements = coreAsArray<Record<string, unknown>>(pickCompatField(payload, ['requirements', 'items', 'data'], [])).map((raw) => normalizeRequirementRecord(raw));
    const pagination = paginationAdapter(pickCompatField(payload, ['pagination'], {}), {
      page: Number(params.page ?? 1),
      per_page: Number(params.per_page ?? 20),
      total: requirements.length,
      pages: requirements.length > 0 ? 1 : 0
    });
    return {
      requirements,
      pagination,
      total: Number(pickCompatField(payload, ['total'], requirements.length))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load document requirements');
  }
}

export async function reanalyzeDocument(documentId: string, payload: { analysis_type?: DocumentAnalysisType } = {}): Promise<DocumentAnalysisResult> {
  try {
    const response = await post<unknown>(`/documents/${encodeURIComponent(documentId)}/reanalyze`, payload);
    const rawPayload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to reanalyze document'
    });
    return normalizeAnalysisResult(rawPayload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to reanalyze document');
  }
}

export async function generateCasesFromAnalysis(payload: DocumentGenerateCasesPayload): Promise<GenerateCasesResponse> {
  try {
    const result = await generateCasesFromAnalysisApi(payload);
    return {
      cases: result.cases,
      total: result.total,
      message: result.message,
      failed_count: Number(result.failed_count || 0),
      summary: isRecord(result.raw?.summary) ? result.raw.summary : undefined,
      raw: result.raw
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to generate test cases');
  }
}

export function resolveAnalysisRequirements(result: DocumentAnalysisResult | null | undefined): DocumentRequirementRecord[] {
  if (!result) return [];
  return result.requirements || [];
}

export async function deleteDocument(documentId: string): Promise<{ success: boolean; message?: string; raw?: Record<string, unknown> }> {
  try {
    const response = await del<unknown>(`/documents/${encodeURIComponent(documentId)}`);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to delete document'
    });
    return {
      success: true,
      message: String(pickCompatField(payload, ['message'], '')),
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to delete document');
  }
}

export async function getRequirement(reqId: string): Promise<DocumentRequirementRecord> {
  try {
    const response = await get<unknown>(`/documents/requirements/${encodeURIComponent(reqId)}`);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load requirement'
    });
    const raw = pickCompatField(payload, ['requirement'], payload);
    return normalizeRequirementRecord(isRecord(raw) ? raw : {}, 0, { req_id: reqId });
  } catch (error) {
    coreNormalizeError(error, 'Failed to load requirement');
  }
}

export async function updateRequirement(
  reqId: string,
  body: RequirementUpdatePayload
): Promise<DocumentRequirementRecord> {
  try {
    const response = await put<unknown>(`/documents/requirements/${encodeURIComponent(reqId)}`, body);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to update requirement'
    });
    const raw = pickCompatField(payload, ['requirement'], payload);
    return normalizeRequirementRecord(isRecord(raw) ? raw : {}, 0, { req_id: reqId });
  } catch (error) {
    coreNormalizeError(error, 'Failed to update requirement');
  }
}

export async function deleteRequirement(reqId: string): Promise<{ success: boolean; message?: string; raw?: Record<string, unknown> }> {
  try {
    const response = await del<unknown>(`/documents/requirements/${encodeURIComponent(reqId)}`);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to delete requirement'
    });
    return {
      success: true,
      message: String(pickCompatField(payload, ['message'], '')),
      raw: payload
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to delete requirement');
  }
}

export async function getDocumentPreview(documentId: string): Promise<DocumentPreviewResult> {
  try {
    const response = await get<unknown>(`/documents/${encodeURIComponent(documentId)}/preview`);
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load document preview'
    });
    const preview = pickCompatField(payload, ['preview', 'data'], {});
    const normalized = isRecord(preview) ? preview : {};
    return {
      content: String(pickCompatField(normalized, ['content'], '')),
      content_type: pickCompatField(normalized, ['content_type'], undefined),
      filename: pickCompatField(normalized, ['filename'], undefined),
      file_size: normalized.file_size != null ? Number(normalized.file_size) : undefined,
      file_type: pickCompatField(normalized, ['file_type'], undefined),
      is_truncated: Boolean(pickCompatField(normalized, ['is_truncated'], false)),
      raw: normalized
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load document preview');
  }
}

export async function exportRequirementsExcel(params: {
  type?: string;
  priority?: string;
  status?: string;
  req_ids?: string[];
} = {}): Promise<DocumentRequirementsExportResult> {
  try {
    const response = await http.request<Blob>({
      url: '/export/requirements/excel',
      method: 'GET',
      params: {
        type: params.type,
        priority: params.priority,
        status: params.status,
        req_ids: Array.isArray(params.req_ids) && params.req_ids.length ? params.req_ids.join(',') : undefined
      },
      responseType: 'blob'
    });
    return {
      blob: response.data as Blob,
      filename: parseFilename(response.headers, 'requirements.xlsx'),
      mimeType: String(pickCompatField(response.headers, ['content-type', 'Content-Type'], ''))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to export requirements');
  }
}
