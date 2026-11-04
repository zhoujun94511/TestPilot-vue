import { resolveUserFacingErrorMessage } from '@/lib/user-facing-error';
import { ApiError } from './http';

export interface NormalizedResponseOptions {
  dataKeys?: string[];
  fallbackMessage?: string;
}

export interface NormalizedPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function pickCompatField<T = unknown>(source: unknown, keys: string[], fallback?: T): T {
  if (isRecord(source)) {
    for (const key of keys) {
      if (source[key] !== undefined && source[key] !== null) {
        return source[key] as T;
      }
    }
  }
  return fallback as T;
}

export function normalizeError(error: unknown, fallback = 'Request failed'): never {
  if (error instanceof ApiError) {
    throw new ApiError(resolveUserFacingErrorMessage(error, fallback), {
      code: error.code,
      errorCode: error.errorCode,
      messageKey: error.messageKey,
      messageParams: error.messageParams,
      details: error.details
    });
  }

  if (error instanceof Error) {
    throw new ApiError(resolveUserFacingErrorMessage(error, fallback));
  }

  if (isRecord(error)) {
    const raw = String(error.message ?? error.error ?? fallback);
    throw new ApiError(resolveUserFacingErrorMessage(raw, fallback), {
      errorCode: typeof error.error_code === 'string' ? error.error_code : undefined,
      code: typeof error.code === 'number' ? error.code : undefined,
      details: error.data ?? error.details ?? error
    });
  }

  throw new ApiError(resolveUserFacingErrorMessage(undefined, fallback));
}

export function normalizeResponse<T = unknown>(payload: unknown, options: NormalizedResponseOptions = {}): T {
  const fallbackMessage = options.fallbackMessage || 'Request failed';

  if (payload instanceof ApiError) {
    throw payload;
  }

  if (isRecord(payload)) {
    const code = payload.code;
    const hasNumericCode = typeof code === 'number' || (typeof code === 'string' && /^-?\d+$/.test(code));
    const numericCode = hasNumericCode ? Number(code) : null;
    // Backends may return business-code strings like "CONFIG_CATEGORY_LIST_SUCCESS".
    // Only treat code as failure when it is numeric and not a known success code.
    const numericCodeFailed = hasNumericCode && numericCode !== 0 && numericCode !== 200;
    if (payload.success === false || (payload.success !== true && numericCodeFailed)) {
      throw new ApiError(String(payload.message ?? payload.error ?? fallbackMessage), {
        errorCode: typeof payload.error_code === 'string' ? payload.error_code : undefined,
        code: typeof payload.code === 'number' ? payload.code : undefined,
        details: payload.data ?? payload
      });
    }

    const dataKeys = options.dataKeys && options.dataKeys.length ? options.dataKeys : ['data'];
    for (const key of dataKeys) {
      if (key in payload) {
        return payload[key] as T;
      }
    }
  }

  return payload as T;
}

export function paginationAdapter(
  payload: unknown,
  fallback: Partial<NormalizedPagination> = {}
): NormalizedPagination {
  const source = isRecord(payload) ? payload : {};
  return {
    page: Number(pickCompatField(source, ['page', 'current_page'], fallback.page ?? 1)),
    per_page: Number(pickCompatField(source, ['per_page', 'page_size', 'limit'], fallback.per_page ?? 20)),
    total: Number(pickCompatField(source, ['total', 'count'], fallback.total ?? 0)),
    pages: Number(pickCompatField(source, ['pages', 'total_pages'], fallback.pages ?? 0)),
    has_prev: pickCompatField(source, ['has_prev', 'hasPrevious'], fallback.has_prev),
    has_next: pickCompatField(source, ['has_next', 'hasNext'], fallback.has_next)
  };
}

export function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}
