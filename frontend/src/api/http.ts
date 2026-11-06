import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import i18n from '@/i18n';
import { currentProjectScopeVersion, getTabProjectId, projectHeaders } from '@/lib/current-project';
import { messageFromApiEnvelope, resolveTransportErrorMessage } from '@/lib/user-facing-error';
import { pinia, useAppStore, useAuthStore } from '@/stores';
import type { Locale } from '@/i18n';

declare module 'axios' {
  interface AxiosRequestConfig {
    /** 项目列表自己就是确认当前项目的请求，不能再等自己 */
    skipProjectBootstrap?: boolean;
  }
}

export interface ApiLegacyEnvelope<T> {
  success?: boolean;
  message?: string;
  message_key?: string;
  message_params?: Record<string, unknown>;
  data?: T;
  error?: string;
  code?: number | string;
  error_code?: string;
}

export class ApiError extends Error {
  code?: number;
  errorCode?: string;
  messageKey?: string;
  messageParams?: Record<string, unknown>;
  details?: unknown;

  constructor(
    message: string,
    options: {
      code?: number;
      errorCode?: string;
      messageKey?: string;
      messageParams?: Record<string, unknown>;
      details?: unknown;
    } = {}
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = options.code;
    this.errorCode = options.errorCode;
    this.messageKey = options.messageKey;
    this.messageParams = options.messageParams;
    this.details = options.details;
  }
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

/** /auth/* 自己处理 401（如登录失败、原密码错误），不触发全局跳转 */
export function onUnauthorized(handler: UnauthorizedHandler) {
  unauthorizedHandler = handler;
}

export function notifyUnauthorized(status: number | undefined, url: string | undefined) {
  if (status !== 401 || !unauthorizedHandler) return;
  const path = String(url || '');
  if (/(^|\/)auth\//.test(path)) return;
  unauthorizedHandler();
}

export const PASSWORD_CHANGE_REQUIRED = 'PASSWORD_CHANGE_REQUIRED';
let passwordChangeRequiredHandler: UnauthorizedHandler | null = null;

export function onPasswordChangeRequired(handler: UnauthorizedHandler) {
  passwordChangeRequiredHandler = handler;
}

export function notifyPasswordChangeRequired(status: number | undefined, code: unknown) {
  if (status === 403 && code === PASSWORD_CHANGE_REQUIRED) passwordChangeRequiredHandler?.();
}

/** 后端 auth_gate 等把错误标识放在字符串 code 里 */
export function errorCodeFromPayload(payload: { code?: unknown; error_code?: string; error?: unknown } | undefined) {
  if (payload?.error_code) return payload.error_code;
  if (typeof payload?.code === 'string' && !/^-?\d+$/.test(payload.code)) return payload.code;
  return typeof payload?.error === 'string' ? payload.error : undefined;
}

/** 调模型、上传和重建索引等长任务，默认 30 秒会提前断开而后端仍在执行 */
export const LONG_TASK_TIMEOUT_MS = 10 * 60 * 1000;

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  withCredentials: true
});

function getLocale() {
  return localStorage.getItem('testpilot_locale') || 'zh-CN';
}

function applyBackendLocale(rawLocale: unknown) {
  const existingLocale = localStorage.getItem('testpilot_locale');
  // 仅用于启动默认值：本地已有语言设置时，不再被后端覆盖
  if (existingLocale === 'zh-CN' || existingLocale === 'en') return;

  const locale = String(rawLocale || '').toLowerCase().startsWith('zh') ? 'zh-CN' : 'en';
  const current = localStorage.getItem('testpilot_locale') as Locale | null;
  if (current === locale) return;
  localStorage.setItem('testpilot_locale', locale);
  i18n.global.locale.value = locale;
  try {
    const appStore = useAppStore(pinia);
    appStore.setLocale(locale);
  } catch {
    // ignore store initialization timing issues
  }
  document.documentElement.lang = locale;
}

let projectBootstrap: Promise<void> | null = null;
let projectBootstrapVersion = -1;

function shouldResolveProject(url: string | undefined, skip: boolean | undefined) {
  if (skip || getTabProjectId() != null) return false;
  const path = String(url || '');
  if (/(^|\/)auth\//.test(path)) return false;
  const auth = useAuthStore(pinia);
  return auth.authRequired && auth.isAuthenticated;
}

/** 本标签页还没有项目时，先等一次项目列表，再让业务请求带上 X-Project-Id */
function ensureCurrentProject(): Promise<void> {
  if (getTabProjectId() != null) return Promise.resolve();
  const version = currentProjectScopeVersion();
  if (projectBootstrapVersion === version) return Promise.resolve();
  if (!projectBootstrap) {
    projectBootstrap = import('@/api/projects')
      .then(({ listProjects }) => listProjects())
      .then(() => undefined)
      .catch(() => undefined)
      .finally(() => {
        projectBootstrapVersion = version;
        projectBootstrap = null;
      });
  }
  return projectBootstrap;
}

export async function resolveProjectHeaders(): Promise<Record<string, string>> {
  if (shouldResolveProject(undefined, false)) await ensureCurrentProject();
  return projectHeaders();
}

http.interceptors.request.use(async (config) => {
  config.headers = config.headers || {};
  config.headers['X-Requested-With'] = 'XMLHttpRequest';
  config.headers['Accept-Language'] = getLocale();
  if (shouldResolveProject(config.url, config.skipProjectBootstrap)) {
    await ensureCurrentProject();
  }
  Object.assign(config.headers, projectHeaders());

  if (config.data instanceof FormData) {
    delete (config.headers as Record<string, string>)['Content-Type'];
  } else if (!config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json';
  }

  return config;
});

function isBlob(value: unknown): value is Blob {
  return typeof Blob !== 'undefined' && value instanceof Blob;
}

async function readBlobError(response: AxiosResponse<Blob>) {
  const contentType = String(response.headers['content-type'] || '');
  if (contentType.includes('application/json')) {
    const text = await response.data.text();
    try {
      const parsed = JSON.parse(text) as ApiLegacyEnvelope<unknown>;
      return parsed.message || parsed.error || resolveTransportErrorMessage(undefined, response.status);
    } catch {
      return text || resolveTransportErrorMessage(undefined, response.status);
    }
  }
  return resolveTransportErrorMessage(response.statusText, response.status);
}

function extractMessage(payload: ApiLegacyEnvelope<unknown> | undefined, fallback = 'Request failed') {
  return messageFromApiEnvelope(payload, fallback);
}

function throwApiError(payload: ApiLegacyEnvelope<unknown> | undefined, fallback = 'Request failed'): never {
  const message = extractMessage(payload, fallback);
  const normalizedCode = typeof payload?.code === 'number'
    ? payload.code
    : (typeof payload?.code === 'string' && /^-?\d+$/.test(payload.code) ? Number(payload.code) : undefined);
    throw new ApiError(message, {
      code: normalizedCode,
      errorCode: errorCodeFromPayload(payload),
      messageKey: payload?.message_key,
      messageParams: payload?.message_params,
      details: payload?.data ?? payload
    });
}

http.interceptors.response.use(
  async (response) => {
    applyBackendLocale(response.headers?.['x-testpilot-locale']);
    if (response.config.responseType === 'blob') {
      return response;
    }

    const payload = response.data as ApiLegacyEnvelope<unknown>;
    const successByFlag = payload?.success !== false;
    const hasNumericCode = typeof payload?.code === 'number' || (typeof payload?.code === 'string' && /^-?\d+$/.test(payload.code));
    const numericCode = hasNumericCode ? Number(payload?.code) : null;
    const successByCode = payload?.code === undefined || !hasNumericCode || numericCode === 0 || numericCode === 200;

    if (successByFlag && successByCode) {
      return response;
    }

    throwApiError(payload);
  },
  async (error: AxiosError) => {
    const response = error.response as AxiosResponse<Blob | ApiLegacyEnvelope<unknown>> | undefined;
    notifyUnauthorized(response?.status, response?.config?.url);

    if (response?.config?.responseType === 'blob' && isBlob(response.data)) {
      const message = await readBlobError(response as AxiosResponse<Blob>);
      return Promise.reject(new ApiError(message, { code: response.status }));
    }

    const payload = response?.data as ApiLegacyEnvelope<unknown> | undefined;
    notifyPasswordChangeRequired(response?.status, payload?.code);
    const payloadMessage = extractMessage(payload, '').trim();
    const message = payloadMessage
      || resolveTransportErrorMessage(error.message, response?.status);
    return Promise.reject(
      new ApiError(message, {
        code: typeof payload?.code === 'number' ? payload.code : response?.status,
        errorCode: errorCodeFromPayload(payload),
        messageKey: payload?.message_key,
        messageParams: payload?.message_params,
        details: payload?.data ?? payload
      })
    );
  }
);

export async function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
  const response = await http.request<T>(config);
  return response.data as T;
}

export function get<T = unknown>(url: string, params?: object, config?: AxiosRequestConfig) {
  return request<T>({ url, method: 'GET', params, ...config });
}

export function post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
  return request<T>({ url, method: 'POST', data, ...config });
}

export function put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
  return request<T>({ url, method: 'PUT', data, ...config });
}

export function patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
  return request<T>({ url, method: 'PATCH', data, ...config });
}

export function del<T = unknown>(url: string, config?: AxiosRequestConfig) {
  return request<T>({ url, method: 'DELETE', ...config });
}

export function download(url: string, config?: AxiosRequestConfig) {
  return request<Blob>({ url, method: 'GET', responseType: 'blob', timeout: LONG_TASK_TIMEOUT_MS, ...config });
}

export default http;
