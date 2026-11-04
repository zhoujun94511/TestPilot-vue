import type { ComposerTranslation } from 'vue-i18n';
import i18n from '@/i18n';

/** 后端可能返回的模型状态原文（中英），展示文案走 i18n */
const MODEL_STATUS_MATCH_GROUPS: { messageKey: string; terms: string[] }[] = [
  {
    messageKey: 'chat.modelStatus.configError',
    terms: ['配置错误', 'config error', 'configuration error']
  },
  {
    messageKey: 'chat.modelStatus.serviceUnavailable',
    terms: ['服务不可用', 'service unavailable']
  },
  {
    messageKey: 'chat.modelStatus.connectionFailed',
    terms: ['连接失败', 'connection failed']
  },
  {
    messageKey: 'chat.modelStatus.unknownModel',
    terms: ['未知模型', 'unknown model']
  }
];

const TOOL_META_LABEL_KEYS = [
  'chat.toolMeta.status',
  'chat.toolMeta.tool',
  'chat.toolMeta.total',
  'chat.toolMeta.hits',
  'chat.toolMeta.searchStatus',
  'chat.toolMeta.generated',
  'chat.toolMeta.rag'
] as const;

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function collectLabelsForAllLocales(keys: readonly string[]): string[] {
  const labels = new Set<string>();
  for (const locale of ['zh-CN', 'en'] as const) {
    for (const key of keys) {
      const label = i18n.global.t(key, {}, { locale }).trim();
      if (label) labels.add(label);
    }
  }
  return [...labels];
}

let cachedToolMetaLinePattern: RegExp | null = null;

/** 过滤助手消息前几行中的工具元数据（后端可能用中或英标签） */
export function buildToolMetaLinePattern(): RegExp {
  if (cachedToolMetaLinePattern) return cachedToolMetaLinePattern;
  const labels = collectLabelsForAllLocales(TOOL_META_LABEL_KEYS);
  const alternation = labels.map(escapeRegExp).join('|');
  cachedToolMetaLinePattern = new RegExp(`^\\*\\*(${alternation})\\*\\*[:：]`, 'i');
  return cachedToolMetaLinePattern;
}

export function localizeModelStatusValue(raw: string | null | undefined, t: ComposerTranslation): string {
  const text = String(raw || '').trim();
  if (!text) return t('chat.sessions.defaultTitle');
  const lowered = text.toLowerCase();
  for (const group of MODEL_STATUS_MATCH_GROUPS) {
    if (group.terms.some((term) => term.toLowerCase() === lowered || term === text)) {
      return t(group.messageKey);
    }
  }
  return text;
}

const SESSION_TITLE_CANONICAL_GROUPS: { messageKey: string; terms: string[] }[] = [
  {
    messageKey: 'chat.sessions.defaultTitle',
    terms: [
      ...collectLabelsForAllLocales(['chat.sessions.defaultTitle', 'chat.page.title']),
      'AI Chat Assistant',
      'AI 对话助手'
    ]
  },
  {
    messageKey: 'chat.sessions.untitled',
    terms: [...collectLabelsForAllLocales(['chat.sessions.untitled']), 'Untitled Session']
  },
  {
    messageKey: 'chat.sessions.draftTitle',
    terms: [...collectLabelsForAllLocales(['chat.sessions.draftTitle']), '新会话', 'New chat', 'New Chat']
  }
];

/** 会话标题：后端/历史遗留英文或另一语言占位 → 当前 locale 文案 */
export function localizeSessionTitle(raw: string | null | undefined, t: ComposerTranslation): string {
  const text = String(raw || '').trim();
  if (!text) return t('chat.sessions.untitled');
  const lowered = text.toLowerCase();
  for (const group of SESSION_TITLE_CANONICAL_GROUPS) {
    if (group.terms.some((term) => term.toLowerCase() === lowered || term === text)) {
      return t(group.messageKey);
    }
  }
  return text;
}

export function stripLeadingToolMetaLines(content: string, maxScanLines = 9): string {
  const raw = String(content || '').trim();
  if (!raw) return raw;
  const pattern = buildToolMetaLinePattern();
  const lines = raw.split('\n');
  const filtered = lines.filter((line, index) => {
    if (index > maxScanLines) return true;
    const text = line.trim();
    if (!text) return true;
    return !pattern.test(text);
  });
  return filtered.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}
