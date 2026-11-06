import { ApiError } from '@/api/http';
import { ErrorCodes } from '@/constants/errorCodes';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';

type TranslateFn = (key: string, params?: Record<string, unknown>) => string;

/**
 * 后端 error_code / error slug → vue-i18n key（与 zh-CN/en  locale 路径一致）。
 * 优先使用响应里的 message_key；此处为兜底映射。
 */
const API_ERROR_I18N_KEY: Record<string, string> = {
  [ErrorCodes.ACTION_MODE_NOT_SUPPORTED]: 'chat.message.actionModeNotSupported',
  action_mode_not_supported: 'chat.message.actionModeNotSupported',
  [ErrorCodes.EXPLICIT_TOOL_REQUIRED]: 'chat.experimentalTools.errors.explicitRequired',
  explicit_tool_required: 'chat.experimentalTools.errors.explicitRequired',
  [ErrorCodes.UNKNOWN_EXPERIMENTAL_TOOL]: 'chat.experimentalTools.errors.unknownTool',
  unknown_tool: 'chat.experimentalTools.errors.unknownTool',
  feature_disabled: 'chat.experimentalTools.errors.featureDisabled',
  rate_limit_exceeded: 'chat.experimentalTools.errors.rateLimited',
  [ErrorCodes.MODEL_AUTH_FAILED]: 'chat.message.apiKeyInvalid',
  [ErrorCodes.MODEL_RATE_LIMITED]: 'chat.message.providerRateLimited',
  [ErrorCodes.MODEL_TIMEOUT]: 'chat.message.providerTimeout',
  [ErrorCodes.MODEL_NETWORK_ERROR]: 'chat.message.providerNetworkError',
  [ErrorCodes.TOKEN_SESSION_TOKEN_LIMIT]: 'common.tokenSession.exceededTokens',
  [ErrorCodes.TOKEN_SESSION_CALL_LIMIT]: 'common.tokenSession.exceededCalls'
};

function lookupApiErrorI18nKey(error: ApiError): string | undefined {
  if (error.messageKey?.trim()) {
    return error.messageKey.trim();
  }
  const token = String(error.errorCode || '').trim();
  if (!token) return undefined;
  return (
    API_ERROR_I18N_KEY[token]
    || API_ERROR_I18N_KEY[token.toUpperCase()]
    || API_ERROR_I18N_KEY[token.toLowerCase()]
  );
}

/** 将 ApiError 解析为当前 locale 下的展示文案（与 chat 发送、实验工具共用）。 */
export function resolveApiErrorMessage(error: unknown, t: TranslateFn, fallbackKey: string): string {
  if (error instanceof ApiError) {
    const i18nKey = lookupApiErrorI18nKey(error);
    if (i18nKey) {
      const params =
        error.messageParams && typeof error.messageParams === 'object'
          ? (error.messageParams as Record<string, unknown>)
          : undefined;
      const localized = t(i18nKey, params);
      if (localized && localized !== i18nKey) {
        return localized;
      }
    }
    return getUserFacingErrorMessage(error, t(fallbackKey));
  }
  if (error instanceof Error) {
    return getUserFacingErrorMessage(error, t(fallbackKey));
  }
  return t(fallbackKey);
}
