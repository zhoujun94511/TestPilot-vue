/** 模型 ID / 配置 provider → 厂商展示名（configCenter.provider.*） */

export const AI_VENDOR_KEYS = ['openai', 'deepseek', 'ollama', 'gemini', 'qwen', 'anthropic'] as const;

export type AiVendorKey = (typeof AI_VENDOR_KEYS)[number] | 'unknown';

const VENDOR_I18N_KEY: Record<Exclude<AiVendorKey, 'unknown'>, string> = {
  openai: 'configCenter.provider.OPENAI',
  deepseek: 'configCenter.provider.DEEPSEEK',
  ollama: 'configCenter.provider.OLLAMA',
  gemini: 'configCenter.provider.GEMINI',
  qwen: 'configCenter.provider.QWEN',
  anthropic: 'configCenter.provider.ANTHROPIC'
};

export function inferAiVendorKey(modelOrProvider?: string | null): AiVendorKey {
  const raw = String(modelOrProvider || '').trim();
  if (!raw) return 'unknown';

  const normalized = raw.toLowerCase().replace(/_/g, '-');

  if (
    normalized === 'openai' ||
    normalized === 'deepseek' ||
    normalized === 'ollama' ||
    normalized === 'gemini' ||
    normalized === 'qwen' ||
    normalized === 'anthropic'
  ) {
    return normalized as AiVendorKey;
  }

  if (
    /\bgpt[-_]?\d|chatgpt|^o[1349](-|$)|^gpt-5|^gpt-4|^gpt-3/.test(normalized) ||
    normalized.includes('openai')
  ) {
    return 'openai';
  }
  if (normalized.includes('deepseek') || normalized.includes('deep-seek')) {
    return 'deepseek';
  }
  if (normalized.includes('gemini')) {
    return 'gemini';
  }
  if (normalized.includes('qwen') || normalized.includes('tongyi') || normalized.includes('通义')) {
    return 'qwen';
  }
  if (normalized.includes('anthropic') || normalized.includes('claude')) {
    return 'anthropic';
  }
  if (
    normalized.includes('ollama') ||
    normalized.includes('llama') ||
    normalized.includes('mistral') ||
    normalized.includes('phi-') ||
    normalized.includes('codellama')
  ) {
    return 'ollama';
  }

  return 'unknown';
}

export function resolveModelVendorLabel(
  modelOrProvider: string | null | undefined,
  t: (key: string) => string
): string {
  const vendor = inferAiVendorKey(modelOrProvider);
  if (vendor !== 'unknown') {
    return t(VENDOR_I18N_KEY[vendor]);
  }
  const raw = String(modelOrProvider || '').trim();
  return raw;
}
