import i18n from '@/i18n';

export function isBlankField(value: string | number | boolean | null | undefined): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim().length === 0;
  return false;
}

export function requiredFieldMessage(): string {
  return i18n.global.t('validation.required');
}

/** 将空白字段写入 errors 对象，返回是否全部通过 */
export function applyRequiredFieldErrors<T extends Record<string, string>>(
  errors: T,
  fields: Record<keyof T, string | number | boolean | null | undefined>
): boolean {
  const message = requiredFieldMessage();
  let valid = true;
  for (const key of Object.keys(fields) as Array<keyof T>) {
    if (isBlankField(fields[key])) {
      errors[key] = message as T[keyof T];
      valid = false;
    } else {
      errors[key] = '' as T[keyof T];
    }
  }
  return valid;
}
