import type { ComposerTranslation } from 'vue-i18n';

/** Maps DB / API category strings (ZH/EN variants) to enums.cases.category.* keys */
const CASE_CATEGORY_ALIASES: Record<string, string> = {
  功能测试: 'functional',
  functional: 'functional',
  'functional testing': 'functional',
  性能测试: 'performance',
  performance: 'performance',
  'performance testing': 'performance',
  安全测试: 'security',
  安全性测试: 'security',
  security: 'security',
  'security testing': 'security',
  兼容性测试: 'compatibility',
  compatibility: 'compatibility',
  'compatibility testing': 'compatibility',
  可用性测试: 'usability',
  易用性测试: 'usability',
  usability: 'usability',
  'usability testing': 'usability',
  集成测试: 'integration',
  接口测试: 'integration',
  integration: 'integration',
  api: 'integration',
  'api testing': 'integration',
  'integration testing': 'integration',
  回归测试: 'regression',
  自动化测试: 'regression',
  自动化回归测试: 'regression',
  弱网测试: 'performance',
  regression: 'regression',
  automation: 'regression',
  'automation testing': 'regression',
  'regression testing': 'regression'
};

/**
 * Display name for a test case category, using i18n when the value matches known aliases.
 */
export function canonicalCaseCategory(raw: string): string {
  const value = String(raw || '').trim();
  if (!value) return '';
  return CASE_CATEGORY_ALIASES[value] || CASE_CATEGORY_ALIASES[value.toLowerCase()] || value;
}

export function resolveCaseCategoryDisplayName(raw: string, t: ComposerTranslation): string {
  const value = String(raw).trim();
  if (!value) return '';
  const alias = CASE_CATEGORY_ALIASES[value] || CASE_CATEGORY_ALIASES[value.toLowerCase()];
  if (!alias) return value;
  return t(`enums.cases.category.${alias}`);
}
