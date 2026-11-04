import type { Component } from 'vue';
import {
  BookOpen,
  FileText,
  FlaskConical,
  LayoutDashboard,
  MessageSquare,
  Settings,
  Sparkles,
  Users
} from '@lucide/vue';

/** Lucide 组件，或 `'brand-mark'`（与 `BrandMark.vue` / 圆角 brand-mark*.png 同源） */
export type AppNavIcon = Component | 'brand-mark';

export type AppNavRole = 'super_admin' | 'admin' | 'user';

export interface AppNavItem {
  to: string;
  labelKey: string;
  icon: AppNavIcon;
  /** 开启 AUTH_REQUIRE_AUTH 时可见角色；未设置则所有已登录/匿名用户可见 */
  roles?: AppNavRole[];
  /** 用于面包屑的模块根路径前缀 */
  sectionPrefix?: string;
  sectionLabelKey?: string;
}

export interface AppNavGroup {
  titleKey: string;
  items: AppNavItem[];
}

export const appNavGroups: AppNavGroup[] = [
  {
    titleKey: 'common.shell.groups.overview',
    items: [
      {
        to: '/',
        labelKey: 'common.nav.dashboard',
        icon: LayoutDashboard
      }
    ]
  },
  {
    titleKey: 'common.shell.groups.analysis',
    items: [
      {
        to: '/documents',
        labelKey: 'common.nav.documents',
        icon: FileText,
        sectionPrefix: '/documents',
        sectionLabelKey: 'common.nav.documents'
      },
      {
        to: '/knowledge',
        labelKey: 'common.nav.knowledgeBase',
        icon: BookOpen,
        sectionPrefix: '/knowledge',
        sectionLabelKey: 'common.nav.knowledgeBase'
      }
    ]
  },
  {
    titleKey: 'common.shell.groups.generation',
    items: [
      {
        to: '/cases',
        labelKey: 'common.nav.cases',
        icon: FlaskConical,
        sectionPrefix: '/cases',
        sectionLabelKey: 'common.nav.cases'
      }
    ]
  },
  {
    titleKey: 'common.shell.groups.assistant',
    items: [
      {
        to: '/chat',
        labelKey: 'common.nav.chat',
        icon: MessageSquare
      },
      {
        to: '/experimental-tools',
        labelKey: 'common.nav.experimentalTools',
        icon: Sparkles
      }
    ]
  },
  {
    titleKey: 'common.shell.groups.system',
    items: [
      {
        to: '/config',
        labelKey: 'common.nav.configCenter',
        icon: Settings,
        roles: ['super_admin'],
        sectionPrefix: '/config',
        sectionLabelKey: 'common.nav.configCenter'
      },
      {
        to: '/admin/users',
        labelKey: 'admin.nav.users',
        icon: Users,
        roles: ['super_admin', 'admin'],
        sectionPrefix: '/admin/users',
        sectionLabelKey: 'admin.nav.users'
      }
    ]
  }
];
