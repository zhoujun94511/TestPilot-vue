/** 需求 status 字段 → i18n（enums.documents.requirementStatus.*） */

const REQUIREMENT_STATUS_VALUES = ['draft', 'active', 'deprecated'] as const;

export function normalizeRequirementStatusKey(status?: string | null): string {
  const key = String(status || 'active').trim().toLowerCase();
  if (key === 'deleted') return 'deprecated';
  if ((REQUIREMENT_STATUS_VALUES as readonly string[]).includes(key)) return key;
  return key || 'active';
}

export function resolveRequirementStatusLabel(
  status: string | undefined | null,
  t: (key: string) => string
): string {
  const key = normalizeRequirementStatusKey(status);
  const i18nKey = `enums.documents.requirementStatus.${key}`;
  const translated = t(i18nKey);
  if (translated !== i18nKey) return translated;
  const casesKey = `enums.cases.status.${key}`;
  const casesLabel = t(casesKey);
  if (casesLabel !== casesKey) return casesLabel;
  return String(status || '').trim() || t('enums.documents.requirementStatus.active');
}

export function buildRequirementStatusSelectOptions(t: (key: string) => string) {
  return REQUIREMENT_STATUS_VALUES.map((value) => ({
    value,
    label: resolveRequirementStatusLabel(value, t)
  }));
}
