import type { RecentActivityRecord } from '@/api/stats';
import type { ComposerTranslation } from 'vue-i18n';

const LEGACY_MESSAGE_PREFIXES: RegExp[] = [
  /^生成了测试用例[:：]\s*/,
  /^分析了需求文档[:：]\s*/,
  /^上传了知识库文件[:：]\s*/,
  /^AI助手会话[:：]\s*/
];

const SUBJECT_PREVIEW_MAX = 48;

function truncateSubject(value: string, max = SUBJECT_PREVIEW_MAX): string {
  const text = value.trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...`;
}

/** 从旧版 message 或新版 subject 提取活动主体文案 */
export function activitySubjectFromRecord(record: RecentActivityRecord): string {
  const direct = String(record.subject ?? '').trim();
  if (direct) return direct;

  let message = String(record.message ?? '').trim();
  for (const pattern of LEGACY_MESSAGE_PREFIXES) {
    message = message.replace(pattern, '');
  }
  return message.trim();
}

/** 按当前语言格式化最近活动说明（前缀 i18n + 动态主体） */
export function formatRecentActivityMessage(
  record: RecentActivityRecord,
  t: ComposerTranslation,
  te: (key: string) => boolean
): string {
  const subject = truncateSubject(activitySubjectFromRecord(record));
  if (!subject) {
    return String(record.message ?? '').trim();
  }
  const type = String(record.type || 'other');
  const key = `dashboard.activities.messages.${type}`;
  if (te(key)) {
    return t(key, { subject });
  }
  if (te('dashboard.activities.messages.other')) {
    return t('dashboard.activities.messages.other', { subject });
  }
  return subject;
}
