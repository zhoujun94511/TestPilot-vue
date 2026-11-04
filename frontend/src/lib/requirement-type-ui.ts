/** 后端 Requirement.type / 分析落库类型 → i18n（enums.documents.requirementType.*） */

export const REQUIREMENT_TYPE_ENUM_KEYS = [
  'functional',
  'non_functional',
  'non-functional',
  'business',
  'technical',
  'test_point',
  'business_rule',
  'requirements'
] as const;

export function normalizeRequirementTypeKey(type?: string | null): string {
  const raw = String(type || '').trim().toLowerCase();
  if (!raw) return 'functional';
  if (raw === 'nonfunctional' || raw === 'non_functional') return 'non_functional';
  if (raw === 'testpoint') return 'test_point';
  if (raw === 'businessrule') return 'business_rule';
  return raw.replace(/-/g, '_');
}

export function requirementTypeI18nKey(type?: string | null): string {
  const key = normalizeRequirementTypeKey(type);
  if (key === 'non_functional') return 'enums.documents.requirementType.non_functional';
  return `enums.documents.requirementType.${key}`;
}

export function resolveRequirementTypeLabel(
  type: string | undefined | null,
  t: (key: string) => string
): string {
  const key = normalizeRequirementTypeKey(type);
  const i18nKey = requirementTypeI18nKey(type);
  const translated = t(i18nKey);
  if (translated !== i18nKey) return translated;
  if (key === 'functional' || key === 'test_point') {
    const fallback = t('enums.documents.analysisType.test_points');
    if (fallback !== 'enums.documents.analysisType.test_points') return fallback;
  }
  if (key === 'business' || key === 'business_rule') {
    const fallback = t('enums.documents.analysisType.business_rules');
    if (fallback !== 'enums.documents.analysisType.business_rules') return fallback;
  }
  const raw = String(type || '').trim();
  return raw || t('enums.documents.requirementType.unknown');
}

export function buildRequirementTypeSelectOptions(t: (key: string) => string) {
  const values = [
    'functional',
    'non_functional',
    'business',
    'technical',
    'test_point',
    'business_rule'
  ] as const;
  return values.map((value) => ({
    value,
    label: resolveRequirementTypeLabel(value, t)
  }));
}
