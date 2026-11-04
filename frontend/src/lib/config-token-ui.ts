import type { ConfigItem } from '@/api/config';

/** 聊天单次最大词元数 */
export const CONFIG_CHAT_MAX_TOKENS_KEY = 'MAX_TOKENS';

/** 用例生成与需求分析（各厂商共用） */
export const CONFIG_GENERATION_MAX_TOKENS_KEY = 'TR_MAX_TOKENS';

/** 单会话累计 Token / 调用次数熔断（performance 分类） */
export const CONFIG_SESSION_TOKEN_GUARD_KEYS = [
  'TOKEN_MAX_PER_SESSION',
  'TOKEN_MAX_CALLS_PER_SESSION'
] as const;

export type ConfigSessionTokenGuardKey = (typeof CONFIG_SESSION_TOKEN_GUARD_KEYS)[number];

const PROVIDER_MAX_TOKEN_KEYS = {
  OPENAI: 'TR_OPENAI_MAX_TOKENS',
  DEEPSEEK: 'TR_DEEPSEEK_MAX_TOKENS',
  GEMINI: 'TR_GEMINI_MAX_TOKENS',
  QWEN: 'TR_QWEN_MAX_TOKENS'
} as const;

export type ConfigProviderMaxTokenProvider = keyof typeof PROVIDER_MAX_TOKEN_KEYS;

export function isConfigSessionTokenGuardKey(key: string): key is ConfigSessionTokenGuardKey {
  return (CONFIG_SESSION_TOKEN_GUARD_KEYS as readonly string[]).includes(key);
}

export function isConfigTokenBudgetKey(key: string): boolean {
  if (key === CONFIG_CHAT_MAX_TOKENS_KEY || key === CONFIG_GENERATION_MAX_TOKENS_KEY) return true;
  return Object.values(PROVIDER_MAX_TOKEN_KEYS).includes(key as (typeof PROVIDER_MAX_TOKEN_KEYS)[ConfigProviderMaxTokenProvider]);
}

export function listConfigProviderMaxTokenKeys(): string[] {
  return Object.values(PROVIDER_MAX_TOKEN_KEYS);
}

export interface AiModelTokenBudgetSections {
  chatItem: ConfigItem | null;
  /** 是否展示「用例与需求分析」统一词元项（有 TR_MAX_TOKENS 或任一 legacy TR_* 即可） */
  hasGenerationMaxTokens: boolean;
}

export function listLegacyProviderGenerationTokenItems(items: ConfigItem[]): ConfigItem[] {
  return listConfigProviderMaxTokenKeys()
    .map((key) => items.find((item) => item.key === key))
    .filter((item): item is ConfigItem => item != null);
}

export function buildAiModelTokenBudgetSections(items: ConfigItem[]): AiModelTokenBudgetSections {
  const byKey = new Map(items.map((item) => [item.key, item]));
  const chatItem = byKey.get(CONFIG_CHAT_MAX_TOKENS_KEY) ?? null;
  const hasGenerationMaxTokens =
    byKey.has(CONFIG_GENERATION_MAX_TOKENS_KEY) || listLegacyProviderGenerationTokenItems(items).length > 0;

  return { chatItem, hasGenerationMaxTokens };
}

/** 保存前：统一项与各厂商 legacy 键保持一致 */
export function syncGenerationMaxTokensToLegacyKeys(items: ConfigItem[], value: unknown) {
  const normalized: ConfigItem['value'] =
    typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' || value === null
      ? value
      : value === undefined
        ? ''
        : String(value);
  const unified = items.find((item) => item.key === CONFIG_GENERATION_MAX_TOKENS_KEY);
  if (unified) {
    unified.value = normalized;
  }
  listLegacyProviderGenerationTokenItems(items).forEach((item) => {
    item.value = normalized;
  });
}

/** 分组渲染时排除 Token 预算与会话熔断项，避免重复展示 */
export function filterItemsForCategoryGrouping(categoryId: string, items: ConfigItem[]): ConfigItem[] {
  return items.filter((item) => {
    if (categoryId === 'ai_model' && isConfigSessionTokenGuardKey(item.key)) return false;
    if (categoryId === 'ai_model' && isConfigTokenBudgetKey(item.key)) return false;
    if (categoryId === 'performance' && isConfigSessionTokenGuardKey(item.key)) return false;
    return true;
  });
}
