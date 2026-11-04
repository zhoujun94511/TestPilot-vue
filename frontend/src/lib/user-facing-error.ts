import i18n from '@/i18n';
import { redactLocalPaths } from '@/lib/public-file-label';

const AXIOS_STATUS_MESSAGE = /^Request failed with status code (\d{3})$/i;

const TRANSPORT_MESSAGE_EXACT = new Set(
  ['network error', 'request failed', 'timeout of', 'timeout exceeded'].map((s) => s.toLowerCase())
);

const GENERIC_BACKEND_MESSAGES = new Set(['unknown error', 'request failed', '']);

type ErrorLike = {
  name?: string;
  message?: string;
  code?: number;
  messageKey?: string;
  messageParams?: Record<string, unknown>;
};

function translate(key: string, params?: Record<string, unknown>) {
  return i18n.global.t(key, params ?? {});
}

function isGenericBackendMessage(message: string | undefined): boolean {
  return GENERIC_BACKEND_MESSAGES.has((message || '').trim().toLowerCase());
}

/** 后端仅返回 message_key 或 message 为 Unknown error 时，用 i18n 解析业务文案 */
export function messageFromApiEnvelope(
  payload:
    | {
        message?: string;
        error?: string;
        message_key?: string;
        message_params?: Record<string, unknown>;
      }
    | undefined,
  fallback?: string
): string {
  const fb = fallback ?? translate('common.errors.requestFailed');
  if (!payload) return fb;

  const raw = (payload.message || payload.error || '').trim();
  const key = payload.message_key?.trim();

  if (key) {
    const localized = translate(key, payload.message_params);
    if (localized && localized !== key) {
      if (isGenericBackendMessage(raw)) return localized;
    }
  }

  if (raw && !isGenericBackendMessage(raw)) return raw;
  if (key) {
    const localized = translate(key, payload.message_params);
    if (localized && localized !== key) return localized;
  }
  return fb;
}

export function messageLooksLikeTransportError(message: string): boolean {
  const trimmed = message.trim();
  if (!trimmed) return true;
  if (AXIOS_STATUS_MESSAGE.test(trimmed)) return true;
  const lower = trimmed.toLowerCase();
  if (TRANSPORT_MESSAGE_EXACT.has(lower)) return true;
  if (lower.startsWith('timeout')) return true;
  if (lower.includes('network error')) return true;
  return false;
}

export function resolveHttpStatusUserMessage(status?: number): string {
  if (status === 401) return translate('common.errors.http401');
  if (status === 403) return translate('common.errors.http403');
  if (status === 404) return translate('common.errors.http404');
  if (status === 408) return translate('common.errors.http408');
  if (status === 429) return translate('common.errors.http429');
  if (status && status >= 500) return translate('common.errors.http5xx', { status });
  if (status && status >= 400) return translate('common.errors.http4xx', { status });
  return translate('common.errors.requestFailed');
}

/** HTTP 拦截器：无业务 message 时将 Axios 英文转为 i18n */
export function resolveTransportErrorMessage(
  rawMessage: string | undefined,
  status?: number,
  fallback?: string
): string {
  const fb = fallback ?? translate('common.errors.requestFailed');
  const msg = (rawMessage || '').trim();
  const statusFromMsg = msg.match(AXIOS_STATUS_MESSAGE)?.[1];
  const resolvedStatus = status ?? (statusFromMsg ? Number(statusFromMsg) : undefined);

  if (!msg || messageLooksLikeTransportError(msg)) {
    if (resolvedStatus) return resolveHttpStatusUserMessage(resolvedStatus);
    if (!msg || msg.toLowerCase().includes('network')) {
      return translate('common.errors.network');
    }
    return fb;
  }
  return msg;
}

function isApiErrorLike(error: unknown): error is ErrorLike & { name: 'ApiError' } {
  return (
    typeof error === 'object' &&
    error !== null &&
    (error as ErrorLike).name === 'ApiError' &&
    typeof (error as ErrorLike).message === 'string'
  );
}

/**
 * 将 Axios/网络层英文报错转为可展示的本地化文案；保留后端返回的业务 message。
 */
export function resolveUserFacingErrorMessage(error: unknown, fallback?: string): string {
  const fb = fallback ?? translate('common.errors.requestFailed');

  if (isApiErrorLike(error)) {
    const msg = (error.message || '').trim();
    const statusFromMsg = msg.match(AXIOS_STATUS_MESSAGE)?.[1];
    const status = error.code ?? (statusFromMsg ? Number(statusFromMsg) : undefined);

    if (error.messageKey) {
      const localized = translate(error.messageKey, error.messageParams);
      if (localized && localized !== error.messageKey) {
        if (isGenericBackendMessage(msg) || messageLooksLikeTransportError(msg)) {
          return localized;
        }
      }
    }

    if (!msg || messageLooksLikeTransportError(msg) || isGenericBackendMessage(msg)) {
      if (error.messageKey) {
        const localized = translate(error.messageKey, error.messageParams);
        if (localized && localized !== error.messageKey) return localized;
      }
      return status ? resolveHttpStatusUserMessage(status) : fb;
    }
    return redactLocalPaths(msg);
  }

  if (error instanceof Error) {
    return redactLocalPaths(resolveTransportErrorMessage(error.message, undefined, fb));
  }

  if (typeof error === 'string' && error.trim()) {
    return messageLooksLikeTransportError(error) ? fb : redactLocalPaths(error.trim());
  }

  return fb;
}

/** 供 catch 块：`getUserFacingErrorMessage(error, t(fallbackKey))` */
export function getUserFacingErrorMessage(error: unknown, fallback: string): string {
  return resolveUserFacingErrorMessage(error, fallback);
}
