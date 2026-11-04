export type FormatBytesOptions = {
  /** 值为 0 或空时的展示，默认 `0 B`；表格列常用 `-` */
  zero?: string;
};

export function formatBytes(bytes?: number | null, options?: FormatBytesOptions): string {
  const zero = options?.zero ?? '0 B';
  const value = Number(bytes ?? 0);
  if (!value) return zero;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

/** locale 不传时使用运行时默认区域；页面可传入 `useI18n().locale` */
export function formatDateTime(value?: string | null, locale?: string, empty = '-'): string {
  if (!value) return empty;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

/** 会话列表等紧凑场景：月日 + 时分，不含年份 */
export function formatDateTimeCompact(value?: string | null, locale?: string, empty = ''): string {
  if (!value) return empty;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}
