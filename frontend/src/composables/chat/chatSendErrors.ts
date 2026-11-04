import { ApiError } from '@/api/http';
import { ErrorCodes } from '@/constants/errorCodes';
import { resolveApiErrorMessage } from '@/lib/api-error-i18n';

export function isModelInitError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  const message = String(error.message || '').toLowerCase();
  const errorCode = String(error.errorCode || '').toUpperCase();
  return error.code === 503
    || errorCode === ErrorCodes.MODEL_NOT_INITIALIZED
    || errorCode === ErrorCodes.MODEL_SERVICE_UNAVAILABLE
    || message.includes('llm_not_initialized')
    || message.includes('chat model is not initialized')
    || message.includes('聊天模型尚未初始化')
    || message.includes('api key');
}

type TranslateFn = (key: string, params?: Record<string, unknown>) => string;

export function resolveSendErrorMessage(error: unknown, t: TranslateFn): string {
  if (isModelInitError(error)) {
    return t('chat.message.llmNotInitialized');
  }

  if (error instanceof ApiError) {
    const message = String(error.message || '').toLowerCase();
    if (message.includes('api key') || message.includes('apikey') || message.includes('配置异常')) {
      return t('chat.message.apiKeyInvalid');
    }
    return resolveApiErrorMessage(error, t, 'chat.message.sendFailed');
  }

  if (error instanceof Error) {
    return resolveApiErrorMessage(error, t, 'chat.message.sendFailed');
  }

  return t('chat.message.sendFailed');
}

export function resolveExperimentalToolErrorMessage(error: unknown, t: TranslateFn): string {
  return resolveApiErrorMessage(error, t, 'chat.experimentalTools.runFailed');
}
