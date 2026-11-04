<template>
  <div :class="dashboardActivityPanelClass(needsScroll)">
    <section
      v-for="group in groups"
      :key="group.type"
      :class="dashboardActivityGroupClass"
    >
      <button
        type="button"
        :class="dashboardActivityGroupHeaderClass"
        :aria-expanded="isExpanded(group.type)"
        @click="toggleGroup(group.type)"
      >
        <div
          :class="
            group.navIcon
              ? navItemIconClass({ active: false })
              : dashboardActivityIconClass({ tone: 'primary' })
          "
        >
          <ShellAppNavIcon v-if="group.navIcon" :icon="group.navIcon" />
          <template v-else>{{ group.fallbackIcon }}</template>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-semibold text-[var(--tp-color-text-900)]">{{ group.label }}</span>
            <TpTag variant="primary">{{ group.items.length }}</TpTag>
          </div>
          <div class="mt-0.5 text-xs text-[var(--tp-color-text-500)]">
            {{ groupSummary(group) }}
          </div>
        </div>
        <span
          class="shrink-0 text-xs font-semibold text-[var(--tp-color-text-500)]"
          aria-hidden="true"
        >
          {{ isExpanded(group.type) ? '▾' : '▸' }}
        </span>
      </button>

      <ul v-if="isExpanded(group.type)" class="border-t border-[var(--tp-border-default)]">
        <li
          v-for="(item, index) in group.items"
          :key="`${group.type}-${item.time || item.message}-${index}`"
          :class="dashboardActivityGroupItemClass"
        >
          <div :class="dataTitleClass">{{ activityMessage(item) }}</div>
          <div v-if="item.time" :class="[dataSubtitleClass, 'mt-1']">
            {{ formatTime(item.time) }}
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { AppNavIcon } from '@/config/navigation';
import { navIconForModulePath } from '@/lib/nav-icon';
import ShellAppNavIcon from '@/components/shell/AppNavIcon.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import type { RecentActivityRecord } from '@/api/stats';
import {
  ACTIVITY_SCROLL_THRESHOLD,
  dashboardActivityGroupClass,
  dashboardActivityGroupHeaderClass,
  dashboardActivityGroupItemClass,
  dashboardActivityIconClass,
  dashboardActivityPanelClass
} from '@/lib/dashboard-ui';
import { navItemIconClass } from '@/lib/shell-ui';
import { dataSubtitleClass, dataTitleClass } from '@/lib/page-typography';
import { formatRecentActivityMessage } from '@/lib/recent-activity-i18n';

const props = defineProps<{
  activities: RecentActivityRecord[];
}>();

const { t, te, locale } = useI18n();
const expandedTypes = ref<Set<string>>(new Set());

interface ActivityGroupView {
  type: string;
  label: string;
  navIcon: AppNavIcon | null;
  fallbackIcon: string;
  items: RecentActivityRecord[];
}

const TYPE_ORDER = ['case', 'requirement', 'knowledge', 'chat', 'other'] as const;

const groups = computed((): ActivityGroupView[] => {
  const bucket = new Map<string, RecentActivityRecord[]>();
  for (const item of props.activities) {
    const type = String(item.type || 'other');
    const list = bucket.get(type) || [];
    list.push(item);
    bucket.set(type, list);
  }

  const orderedTypes = [
    ...TYPE_ORDER.filter((type) => bucket.has(type)),
    ...[...bucket.keys()].filter((type) => !TYPE_ORDER.includes(type as (typeof TYPE_ORDER)[number]))
  ];

  return orderedTypes.map((type) => {
    const items = bucket.get(type) || [];
    const sample = items[0];
    return {
      type,
      label: activityTypeLabel(type),
      navIcon: navIconForActivityType(type),
      fallbackIcon: String(sample?.icon || 'AI').slice(0, 2),
      items
    };
  });
});

const needsScroll = computed(() => {
  if (props.activities.length > ACTIVITY_SCROLL_THRESHOLD) return true;
  if (expandedTypes.value.size > 0 && props.activities.length > 3) return true;
  return false;
});

watch(
  () => props.activities,
  () => {
    expandedTypes.value = new Set();
  }
);

function navIconForActivityType(type: string): AppNavIcon | null {
  if (type === 'case') return navIconForModulePath('/cases');
  if (type === 'requirement') return navIconForModulePath('/documents');
  if (type === 'knowledge') return navIconForModulePath('/knowledge');
  if (type === 'chat') return navIconForModulePath('/chat');
  return null;
}

function activityMessage(item: RecentActivityRecord) {
  return formatRecentActivityMessage(item, t, te);
}

function activityTypeLabel(type: string) {
  if (type === 'case') return t('dashboard.activities.types.case');
  if (type === 'requirement') return t('dashboard.activities.types.requirement');
  if (type === 'knowledge') return t('dashboard.activities.types.knowledge');
  if (type === 'chat') return t('dashboard.activities.types.chat');
  return t('dashboard.activities.types.other');
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale.value === 'en' ? 'en-US' : 'zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function isExpanded(type: string) {
  return expandedTypes.value.has(type);
}

function toggleGroup(type: string) {
  const next = new Set(expandedTypes.value);
  if (next.has(type)) next.delete(type);
  else next.add(type);
  expandedTypes.value = next;
}

function groupSummary(group: ActivityGroupView) {
  if (isExpanded(group.type)) {
    return t('dashboard.activities.groupExpandedHint');
  }
  const latest = group.items.find((item) => item.time) || group.items[0];
  if (latest && (latest.subject || latest.message)) {
    return activityMessage(latest);
  }
  return t('dashboard.activities.groupCollapsedHint', { count: group.items.length });
}
</script>
