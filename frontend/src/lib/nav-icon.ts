import { appNavGroups, type AppNavIcon } from '@/config/navigation';
import { FlaskConical } from '@lucide/vue';

/** 与侧栏 `appNavGroups` 同源，按模块根路径取图标 */
export function navIconForModulePath(path: string): AppNavIcon {
  const normalized = path.split('?')[0] || path;
  for (const group of appNavGroups) {
    for (const item of group.items) {
      if (item.to === normalized) return item.icon;
      if (item.sectionPrefix && normalized.startsWith(item.sectionPrefix)) {
        return item.icon;
      }
    }
  }
  return FlaskConical;
}
