/** 后端 llm_usage_logs.source → i18n（enums.stats.llmUsageSource.*） */

export const LLM_USAGE_SOURCE_KEYS = [
  'chat',
  'case_generation',
  'document_analysis',
  'agent',
  'llm'
] as const;

export type LlmUsageSourceKey = (typeof LLM_USAGE_SOURCE_KEYS)[number];

export function normalizeLlmUsageSourceKey(source?: string | null): LlmUsageSourceKey {
  const raw = String(source || '').trim().toLowerCase();
  if (raw === 'case' || raw === 'cases') return 'case_generation';
  if (raw === 'document' || raw === 'documents') return 'document_analysis';
  if ((LLM_USAGE_SOURCE_KEYS as readonly string[]).includes(raw)) return raw as LlmUsageSourceKey;
  return 'llm';
}

export function llmUsageSourceI18nKey(source?: string | null): string {
  const key = normalizeLlmUsageSourceKey(source);
  return `enums.stats.llmUsageSource.${key}`;
}

export function resolveLlmUsageSourceLabel(
  source: string | undefined | null,
  t: (key: string) => string
): string {
  const i18nKey = llmUsageSourceI18nKey(source);
  const translated = t(i18nKey);
  if (translated !== i18nKey) return translated;
  return String(source || 'llm');
}
