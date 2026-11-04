import type { ComposerTranslation } from 'vue-i18n';

/** 将后端/监控接口返回的英文（或少量中文）状态码转为当前 locale 文案，避免界面中英混排。 */
export function localizeBackendStatusLabel(
  t: ComposerTranslation,
  status: string | null | undefined
): string {
  const raw = String(status ?? '').trim();
  if (!raw) {
    return t('dashboard.system.unknown');
  }

  const normalized = raw.toLowerCase().replace(/\s+/g, '_');
  const compact = normalized.replace(/_/g, '');

  const map: Record<string, string> = {
    online: t('common.status.healthy'),
    healthy: t('common.status.healthy'),
    active: t('common.status.healthy'),
    success: t('common.status.healthy'),
    ready: t('common.status.healthy'),
    done: t('common.status.healthy'),
    good: t('common.status.healthy'),
    normal: t('common.status.healthy'),
    connected: t('common.status.connected'),
    warning: t('common.status.warning'),
    warn: t('common.status.warning'),
    pending: t('common.status.warning'),
    processing: t('common.status.warning'),
    unknown: t('dashboard.system.unknown'),
    empty: t('common.status.empty'),
    no_data: t('common.status.noData'),
    'no data': t('common.status.noData'),
    nodata: t('common.status.noData'),
    offline: t('common.status.unhealthy'),
    error: t('common.status.unhealthy'),
    fail: t('common.status.unhealthy'),
    failed: t('common.status.unhealthy'),
    unhealthy: t('common.status.unhealthy'),
    danger: t('common.status.unhealthy'),
    abnormal: t('common.status.unhealthy'),
    disconnected: t('common.status.disconnected'),
    limited: t('dashboard.system.limited'),
    在线: t('common.status.healthy'),
    健康: t('common.status.healthy'),
    良好: t('common.status.healthy'),
    正常: t('common.status.healthy'),
    已连接: t('common.status.connected'),
    警告: t('common.status.warning'),
    处理中: t('common.status.warning'),
    未知: t('dashboard.system.unknown'),
    空: t('common.status.empty'),
    暂无数据: t('common.status.noData'),
    离线: t('common.status.unhealthy'),
    失败: t('common.status.unhealthy'),
    危险: t('common.status.unhealthy'),
    异常: t('common.status.unhealthy'),
    未连接: t('common.status.disconnected')
  };

  return (
    map[normalized] ||
    map[compact] ||
    map[raw] ||
    t('dashboard.system.unknown')
  );
}
