<template>
  <section :class="pageRootMarkedClass(pageMarkerDashboard)">
    <BaseState
      v-if="hasPartialError"
      variant="error"
      :title="t('dashboard.message.partialFailure')"
      :message="partialErrorText"
      :retry-text="t('common.actions.retry')"
      @retry="handlePartialErrorRetry"
    />

    <PageNoticeBanner
      v-if="attentionNotice && !attentionDismissed"
      :notice="attentionNotice"
      @action="handleAttentionAction"
      @close="attentionDismissed = true"
    />

    <ActionBar>
      <template #lead>
        <div :class="dashboardMetaStripClass">
          <TpTag variant="ai">{{ aiModelLabel }}</TpTag>
          <TpTag :variant="reliabilityVariant">{{ reliabilityLabel }}</TpTag>
          <TpTag :variant="overallStatusVariant">{{ displayStatusLabel(overallStatusRaw) }}</TpTag>
          <span v-if="health?.timestamp" class="text-xs text-[var(--tp-color-text-500)]">
            {{ t('dashboard.system.updatedAt') }}: {{ formatDateTime(health?.timestamp, dashboardDateLocale, '') }}
          </span>
        </div>
      </template>
      <template #actions>
        <TpButton
          variant="ghost"
          size="sm"
          :loading="bundleExporting"
          :aria-label="bundleExporting ? t('dashboard.actions.bundleExporting') : undefined"
          @click="handleExportBundle"
        >
          {{ t('dashboard.actions.bundleExport') }}
        </TpButton>
        <TpButton
          variant="ghost"
          size="sm"
          :loading="exporting"
          :aria-label="exporting ? t('dashboard.actions.exporting') : undefined"
          @click="handleExportStats"
        >
          {{ t('dashboard.actions.export') }}
        </TpButton>
        <TpButton
          variant="secondary"
          size="sm"
          :loading="refreshing"
          :aria-label="refreshing ? t('dashboard.actions.refreshing') : undefined"
          @click="handleRefresh"
        >
          {{ t('dashboard.actions.refresh') }}
        </TpButton>
      </template>
    </ActionBar>

    <TpCard>
      <template #header>
        <div :class="flexBetweenStartGap2Class">
          <div>
            <div :class="sectionTitleClass">{{ t('dashboard.shortcuts.title') }}</div>
          </div>
        </div>
      </template>
      <div :class="dashboardShortcutGridClass">
        <DashboardShortcutTile
          v-for="item in shortcutTiles"
          :key="item.key"
          :to="item.to"
          :title="item.title"
          :icon="item.icon"
        />
      </div>
    </TpCard>

    <TpCard>
      <template #header>
        <div>
          <div :class="sectionTitleClass">{{ t('dashboard.kpi.title') }}</div>
        </div>
      </template>
      <BaseState
        v-if="overviewLoading && !overview"
        variant="loading"
        :title="t('dashboard.state.loadingOverview')"
      />
      <div v-else :class="grid12Class">
        <div v-for="card in kpiCards" :key="card.key" :class="colSpan12Md6Min1400_3">
          <DashboardStatTile
            :label="card.label"
            :value="card.value"
            :hint="card.hint"
            :to="card.to"
            :icon="card.icon"
          />
        </div>
      </div>
    </TpCard>

    <TpCard>
      <template #header>
        <div>
          <div :class="sectionTitleClass">{{ t('dashboard.system.title') }}</div>
        </div>
      </template>

      <BaseState
        v-if="systemLoading && !system && !health"
        variant="loading"
        :title="t('dashboard.state.loadingSystem')"
      />
      <BaseState
        v-else-if="systemError && !system && !health && !hasPartialError"
        variant="error"
        :title="t('common.status.error')"
        :message="systemError"
        :retry-text="t('common.actions.retry')"
        @retry="handleRefresh"
      />
      <div v-else :class="grid12Class">
        <div v-for="card in systemStatCards" :key="card.key" :class="colSpan12Md6Min1400_3">
          <DashboardStatTile
            :label="card.label"
            :value="card.value"
            :hint="card.hint"
            :to="card.to"
            :icon="card.icon"
          />
        </div>
      </div>
    </TpCard>

    <div :class="grid12StretchClass">
      <div :class="colSpan12Min1400_5">
        <TpCard class="h-full">
          <template #header>
            <div>
              <div :class="sectionTitleClass">{{ t('dashboard.advanced.title') }}</div>
            </div>
          </template>

          <BaseState
            v-if="advancedLoading && !advancedMetricsLoaded"
            variant="loading"
            :title="t('dashboard.state.loadingAdvanced')"
          />
          <BaseState
            v-else-if="advancedError && !advancedMetricsLoaded"
            variant="error"
            :title="t('common.status.error')"
            :message="advancedError"
            :retry-text="t('common.actions.retry')"
            @retry="() => loadAdvancedMetrics({ bustCache: true })"
          />
          <BaseState
            v-else-if="advancedMetricsLoaded && advancedIsEmpty"
            variant="empty"
            :title="t('dashboard.advanced.badgeNoData')"
          />
          <div v-else :class="dashboardAdvancedListSideClass">
            <DashboardStatTile
              v-for="card in advancedStatCards"
              :key="card.key"
              :label="card.label"
              :value="card.value"
              :hint="card.hint"
              :to="card.to"
              :icon="card.icon"
              value-placement="end"
            />
          </div>
        </TpCard>
      </div>

      <div :class="colSpan12Min1400_7">
        <TpCard class="flex h-full flex-col">
          <template #header>
            <div :class="flexBetweenStartGap2Class">
              <div>
                <div :class="sectionTitleClass">{{ t('dashboard.activities.title') }}</div>
              </div>
              <TpTag variant="primary">{{ activityTotal }}</TpTag>
            </div>
          </template>

          <BaseState
            v-if="activitiesLoading && !activities.length"
            variant="loading"
            :title="t('dashboard.state.loadingActivities')"
          />
          <BaseState
            v-else-if="activitiesError && !activities.length && !hasPartialError"
            variant="error"
            :title="t('common.status.error')"
            :message="activitiesError"
            :retry-text="t('common.actions.retry')"
            @retry="handleRefresh"
          />
          <BaseState
            v-else-if="!activities.length"
            variant="empty"
            :title="t('dashboard.activities.emptyTitle')"
          />
          <DashboardActivityGroups
            v-else
            :activities="activities"
            :counts="activityCounts"
            :period-days="activityPeriodDays"
          />
        </TpCard>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Activity, ScrollText, Sparkles } from '@lucide/vue';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import type { AppNavIcon } from '@/config/navigation';
import { navIconForModulePath } from '@/lib/nav-icon';
import {
  colSpan12Md6Min1400_3,
  colSpan12Min1400_5,
  colSpan12Min1400_7,
  grid12Class,
  grid12StretchClass,
  pageMarkerDashboard,
  pageRootMarkedClass
} from '@/lib/page-layout-ui';
import {
  flexBetweenStartGap2Class
} from '@/lib/page-chrome-ui';
import {
  dashboardAdvancedListSideClass,
  dashboardMetaStripClass,
  dashboardShortcutGridClass
} from '@/lib/dashboard-ui';
import { localizeBackendStatusLabel } from '@/lib/localize-backend-status';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { formatDateTime } from '@/lib/format';
import { resolveModelVendorLabel } from '@/lib/ai-model-vendor-ui';
import { resolveLlmUsageSourceLabel } from '@/lib/llm-usage-source-ui';
import { triggerBlobDownload } from '@/lib/download';
import { useToast } from '@/composables/useToast';
import type { PageBannerNotice } from '@/composables/usePageNotice';
import ActionBar from '@/components/common/ActionBar.vue';
import BaseState from '@/components/common/BaseState.vue';
import DashboardActivityGroups from '@/components/dashboard/DashboardActivityGroups.vue';
import DashboardShortcutTile from '@/components/dashboard/DashboardShortcutTile.vue';
import DashboardStatTile from '@/components/dashboard/DashboardStatTile.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpCard from '@/components/ui/base/TpCard.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { refreshAppFeatureFlags } from '@/composables/useFeatureFlags';
import { useAiResult } from '@/composables/useAiResult';
import { useAuthStore } from '@/stores/auth';
import {
  exportBatchZip,
  exportStats,
  getHealthStatus,
  getLogStats,
  getOverviewStats,
  getRecentActivities,
  getSystemStatus,
  getTokenStats,
  getUsageStats,
  type HealthStatus,
  type LogStatsResponse,
  type OverviewStats,
  type RecentActivityRecord,
  type SystemStatus,
  type TokenStatsResponse,
  type UsageStatsResponse
} from '@/api/stats';
import { listCases } from '@/api/cases';
import { getDocumentRequirements } from '@/api/documents';
import {
  kpiHintClass,
  kpiLabelClass,
  kpiValueClass,
  sectionTitleClass
} from '@/lib/page-typography';

type StatusVariant = 'primary' | 'ai' | 'success' | 'warning' | 'danger' | 'neutral' | 'info';

interface KpiCard {
  key: string;
  label: string;
  value: string | number;
  hint?: string;
  to?: string;
  icon: AppNavIcon;
}

interface ShortcutTile {
  key: string;
  to: string;
  title: string;
  icon: AppNavIcon;
}

const { t, locale } = useI18n();
const dashboardDateLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'));
const router = useRouter();
const authStore = useAuthStore();
const canOpenConfig = computed(() => authStore.canSeeConfigCenter());
const toast = useToast();

const overview = ref<OverviewStats | null>(null);
const health = ref<HealthStatus | null>(null);
const system = ref<SystemStatus | null>(null);
const activities = ref<RecentActivityRecord[]>([]);
const activityCounts = ref<Record<string, number> | undefined>();
const activityPeriodDays = ref(30);
const activityTotal = computed(() => {
  const counts = activityCounts.value;
  if (!counts) return activities.value.length;
  return Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0);
});
const usageStats = ref<UsageStatsResponse | null>(null);
const tokenStats = ref<TokenStatsResponse | null>(null);
const logStats = ref<LogStatsResponse | null>(null);

const LOG_STATS_HOURS = 24;
const OVERVIEW_DAYS = 30;

const overviewLoading = ref(false);
const systemLoading = ref(false);
const activitiesLoading = ref(false);
const refreshing = ref(false);
const advancedLoading = ref(false);
const advancedMetricsLoaded = ref(false);
const exporting = ref(false);
const bundleExporting = ref(false);

const overviewError = ref('');
const systemError = ref('');
const activitiesError = ref('');
const advancedError = ref('');
const logsError = ref('');
const errorVisible = ref(true);
const attentionDismissed = ref(false);

const showOfflineMetrics = computed(
  () =>
    !overviewLoading.value
    && !refreshing.value
    && !health.value
    && !system.value
    && !overview.value
    && Boolean(overviewError.value || systemError.value)
);

const overallStatusRaw = computed(() => {
  if (showOfflineMetrics.value) {
    return t('common.status.disconnected');
  }
  return String(
    health.value?.status
      || health.value?.health?.status
      || system.value?.system?.performance?.status
      || system.value?.system?.ai_service?.status
      || t('dashboard.system.unknown')
  );
});

const healthModelLabel = computed(() => {
  const raw = String(health.value?.health?.components?.ai_service?.model || system.value?.system?.ai_service?.model || '');
  return displayAiModelLabel(raw);
});

const aiModelLabel = computed(() => {
  if (showOfflineMetrics.value) {
    return t('common.status.disconnected');
  }
  return healthModelLabel.value || t('dashboard.system.unknown');
});

const reliabilityScore = computed(() => {
  if (showOfflineMetrics.value) {
    return 0;
  }
  const parts = [
    health.value?.status,
    system.value?.system?.ai_service?.status,
    system.value?.system?.knowledge?.status,
    system.value?.system?.performance?.status
  ].filter(Boolean).map((item) => String(item).toLowerCase());

  if (!parts.length) return 0;

  let score = 100;
  for (const part of parts) {
    if (/(warning|warn|unknown|pending)/.test(part)) score -= 12;
    if (/(offline|error|fail|failed|unhealthy|danger)/.test(part)) score -= 30;
  }

  const docs = Number(system.value?.system?.knowledge?.docs || 0);
  const vectors = Number(system.value?.system?.knowledge?.vectors || 0);
  if (docs === 0) score -= 15;
  if (vectors === 0) score -= 10;

  return Math.max(0, Math.min(100, score));
});

const overallStatusVariant = computed<StatusVariant>(() => statusToneVariant(overallStatusRaw.value));

const reliabilityAi = useAiResult(computed(() => ({ confidence: reliabilityScore.value })));
const reliabilityLabel = computed(() =>
  showOfflineMetrics.value
    ? `${t('ai.reliabilityScore')} ${t('common.status.noData')}`
    : `${t('ai.reliabilityScore')} ${reliabilityScore.value}%`
);
const reliabilityVariant = computed<StatusVariant>(() => {
  if (showOfflineMetrics.value) return 'neutral';
  if (reliabilityAi.value.riskLevel === 'danger') return 'danger';
  if (reliabilityAi.value.riskLevel === 'warning') return 'warning';
  return 'success';
});

const attentionNotice = computed<PageBannerNotice | null>(() => {
  if (showOfflineMetrics.value) {
    return {
      type: 'warning',
      title: t('dashboard.attention.offlineTitle'),
      message: t('dashboard.attention.offlineMessage')
    };
  }

  const aiVariant = statusToneVariant(system.value?.system?.ai_service?.status || '');
  if (aiVariant === 'danger') {
    return {
      type: 'danger',
      title: t('dashboard.attention.aiTitle'),
      message: t('dashboard.attention.aiMessage'),
      actionLabel: canOpenConfig.value ? t('dashboard.attention.aiAction') : undefined
    };
  }

  if (!showOfflineMetrics.value && reliabilityScore.value > 0 && reliabilityScore.value < 60) {
    return {
      type: 'warning',
      message: t('dashboard.attention.reliabilityTitle'),
      actionLabel: canOpenConfig.value ? t('dashboard.attention.aiAction') : undefined
    };
  }

  return null;
});

const shortcutTiles = computed<ShortcutTile[]>(() => allShortcutTiles.value.filter(
  (tile) => tile.key !== 'config' || canOpenConfig.value
));

const allShortcutTiles = computed<ShortcutTile[]>(() => [
  {
    key: 'generate',
    to: '/cases/generate',
    title: t('common.actions.generate'),
    icon: navIconForModulePath('/cases/generate')
  },
  {
    key: 'upload',
    to: '/documents/upload',
    title: t('common.actions.upload'),
    icon: navIconForModulePath('/documents/upload')
  },
  {
    key: 'chat',
    to: '/chat',
    title: t('common.nav.chat'),
    icon: navIconForModulePath('/chat')
  },
  {
    key: 'config',
    to: '/config',
    title: t('common.nav.configCenter'),
    icon: navIconForModulePath('/config')
  }
]);

function handleAttentionAction() {
  if (canOpenConfig.value) router.push('/config');
}

function aiServiceRowHint(): string {
  const serviceVariant = statusToneVariant(system.value?.system?.ai_service?.status || '');
  if (serviceVariant === 'danger' || serviceVariant === 'warning') {
    return t('dashboard.system.aiServiceRowHint');
  }
  const raw = String(system.value?.system?.ai_service?.model || '').trim();
  const label = displayAiModelLabel(raw);
  if (!label) return t('dashboard.system.unknown');
  return `${t('dashboard.system.model')} · ${label}`;
}

function countLogErrors(stats: LogStatsResponse | null): number {
  if (!stats) return 0;
  const dist = stats.level_distribution;
  if (dist && Object.keys(dist).length > 0) {
    return Object.entries(dist).reduce((sum, [level, count]) => {
      if (!/error|critical|fatal/i.test(level)) return sum;
      return sum + (Number(count) || 0);
    }, 0);
  }
  return stats.recent_errors?.length ?? 0;
}

function countLogTotal(stats: LogStatsResponse | null): number {
  const dist = stats?.level_distribution;
  if (!dist) return 0;
  return Object.values(dist).reduce((sum, count) => sum + (Number(count) || 0), 0);
}

function runtimeLogsValue(): string {
  if (!logStats.value && logsError.value) return t('common.status.noData');
  return formatNumber(countLogErrors(logStats.value));
}

function runtimeLogsHint(): string {
  const hours = logStats.value?.period_hours ?? LOG_STATS_HOURS;
  if (!logStats.value && logsError.value) return t('dashboard.system.runtimeLogsEmpty');
  const total = countLogTotal(logStats.value);
  const errors = countLogErrors(logStats.value);
  if (total === 0) return t('dashboard.system.runtimeLogsNoEntries', { hours });
  return t('dashboard.system.runtimeLogsHint', {
    hours,
    total: formatNumber(total),
    errors: formatNumber(errors)
  });
}

const systemStatCards = computed<KpiCard[]>(() => allSystemStatCards.value.filter(
  (card) => card.key !== 'runtime-logs' || canOpenConfig.value
));

const allSystemStatCards = computed<KpiCard[]>(() => [
  {
    key: 'ai',
    label: t('dashboard.system.aiService'),
    value: displayStatusLabel(system.value?.system?.ai_service?.status),
    hint: aiServiceRowHint(),
    to: canOpenConfig.value ? '/config' : undefined,
    icon: navIconForModulePath('/config')
  },
  {
    key: 'knowledge',
    label: t('dashboard.system.knowledge'),
    value: displayStatusLabel(system.value?.system?.knowledge?.status),
    hint: `${t('dashboard.system.documents')} ${formatMetricValue(system.value?.system?.knowledge?.docs, '')} · ${t('dashboard.system.vectors')} ${formatMetricValue(system.value?.system?.knowledge?.vectors, '')}`,
    to: '/knowledge',
    icon: navIconForModulePath('/knowledge')
  },
  {
    key: 'performance',
    label: t('dashboard.system.performance'),
    value: displayStatusLabel(system.value?.system?.performance?.status),
    hint: system.value?.system?.performance?.limited_visibility
      ? t('dashboard.system.limitedHint')
      : `${t('dashboard.system.cpu')} ${formatMetricValue(system.value?.system?.performance?.cpu, '%')} · ${t('dashboard.system.memory')} ${formatMetricValue(system.value?.system?.performance?.memory, 'GB')} · ${t('dashboard.system.disk')} ${formatMetricValue(system.value?.system?.performance?.disk, '%')}`,
    icon: Activity
  },
  {
    key: 'runtime-logs',
    label: t('dashboard.system.runtimeLogs', { hours: logStats.value?.period_hours ?? LOG_STATS_HOURS }),
    value: runtimeLogsValue(),
    hint: runtimeLogsHint(),
    icon: ScrollText
  }
]);

const partialErrorText = computed(() => {
  const parts = [
    overviewError.value,
    systemError.value,
    activitiesError.value,
    logsError.value,
    advancedError.value
  ].filter(Boolean) as string[];
  return [...new Set(parts)].join(' · ');
});

const hasPartialError = computed(() => errorVisible.value && Boolean(partialErrorText.value));

function formatOverviewKpiValue(raw: number | undefined): string {
  if (overview.value) {
    return formatNumber(raw ?? 0);
  }
  if (overviewError.value) {
    return t('common.status.noData');
  }
  return '—';
}

const kpiCards = computed<KpiCard[]>(() => {
  const totals = overview.value?.totals;
  const recent = overview.value?.recent_activity;
  const days = recent?.period_days ?? OVERVIEW_DAYS;

  return [
    {
      key: 'cases',
      label: t('dashboard.kpi.totalCases'),
      value: formatOverviewKpiValue(totals?.test_cases),
      hint: recent ? t('dashboard.kpi.recentNew', { days, count: formatNumber(recent.test_cases ?? 0) }) : undefined,
      to: '/cases',
      icon: navIconForModulePath('/cases')
    },
    {
      key: 'documents',
      label: t('dashboard.kpi.totalRequirements'),
      value: formatOverviewKpiValue(totals?.requirements),
      hint: recent ? t('dashboard.kpi.recentNew', { days, count: formatNumber(recent.requirements ?? 0) }) : undefined,
      to: '/documents',
      icon: navIconForModulePath('/documents')
    },
    {
      key: 'knowledge',
      label: t('dashboard.kpi.totalKnowledge'),
      value: formatOverviewKpiValue(totals?.knowledge_files),
      to: '/knowledge',
      icon: navIconForModulePath('/knowledge')
    },
    {
      key: 'chat',
      label: t('dashboard.kpi.totalChatSessions'),
      value: formatOverviewKpiValue(totals?.chat_sessions),
      hint: recent ? t('dashboard.kpi.recentMessages', { days, count: formatNumber(recent.chat_messages ?? 0) }) : undefined,
      to: '/chat',
      icon: navIconForModulePath('/chat')
    }
  ];
});

function sumDailyTrend(items?: Array<{ count?: number }>) {
  return (items || []).reduce((sum, item) => sum + Number(item.count || 0), 0);
}

const advancedIsEmpty = computed(() => {
  if (!advancedMetricsLoaded.value) return false;
  const recentCases = sumDailyTrend(usageStats.value?.daily_trends?.test_cases);
  const recentRequirements = sumDailyTrend(usageStats.value?.daily_trends?.requirements);
  const recentChats = sumDailyTrend(usageStats.value?.daily_trends?.chat_messages);
  const totalTokens = Number(tokenStats.value?.summary?.total_tokens || 0);
  return recentCases === 0 && recentRequirements === 0 && recentChats === 0 && totalTokens === 0;
});

const advancedStatCards = computed<KpiCard[]>(() => {
  const usageDays = usageStats.value?.period_days ?? 30;
  const tokenDays = tokenStats.value?.period_days ?? 7;
  const recentCases = sumDailyTrend(usageStats.value?.daily_trends?.test_cases);
  const recentRequirements = sumDailyTrend(usageStats.value?.daily_trends?.requirements);
  const recentChats = sumDailyTrend(usageStats.value?.daily_trends?.chat_messages);
  const tokenSummary = tokenStats.value?.summary;
  const totalTokens = Number(tokenSummary?.total_tokens || 0);
  const totalCalls = Number(tokenSummary?.total_calls ?? tokenSummary?.total_messages ?? 0);
  const avgPerCall = Number(
    tokenSummary?.avg_tokens_per_call ?? tokenSummary?.avg_tokens_per_message ?? 0
  );
  const topModel = (tokenStats.value?.by_model || [])
    .slice()
    .sort((a, b) => Number(b.total_tokens || 0) - Number(a.total_tokens || 0))[0];

  const noData = t('dashboard.advanced.badgeNoData');

  let tokenHint = t('dashboard.advanced.tokensEmptyHint');
  if (tokenSummary && totalTokens > 0) {
    const parts = [
      t('dashboard.advanced.tokensHintCalls', { n: formatNumber(totalCalls) }),
      t('dashboard.advanced.tokensHintAvg', { n: formatNumber(avgPerCall) })
    ];
    if (topModel?.model) parts.push(resolveModelVendorLabel(String(topModel.model), t));

    const sourceItems = (tokenStats.value?.by_source || [])
      .filter((item) => Number(item.total_tokens || 0) > 0)
      .sort((a, b) => Number(b.total_tokens || 0) - Number(a.total_tokens || 0));
    if (sourceItems.length > 1) {
      const bySource = sourceItems
        .map((item) => {
          const label = resolveLlmUsageSourceLabel(String(item.source || 'llm'), t);
          return `${label} ${formatNumber(Number(item.total_tokens || 0))}`;
        })
        .join(' · ');
      parts.push(bySource);
    } else if (sourceItems.length === 1) {
      parts.push(resolveLlmUsageSourceLabel(String(sourceItems[0].source || 'llm'), t));
    }

    tokenHint = parts.join(' · ');
  }

  return [
    {
      key: 'recent-cases',
      label: t('dashboard.advanced.recentCases', { days: usageDays }),
      value: recentCases > 0 ? formatNumber(recentCases) : noData,
      to: '/cases',
      icon: navIconForModulePath('/cases')
    },
    {
      key: 'recent-requirements',
      label: t('dashboard.advanced.recentRequirements', { days: usageDays }),
      value: recentRequirements > 0 ? formatNumber(recentRequirements) : noData,
      to: '/documents',
      icon: navIconForModulePath('/documents')
    },
    {
      key: 'recent-chats',
      label: t('dashboard.advanced.recentChats', { days: usageDays }),
      value: recentChats > 0 ? formatNumber(recentChats) : noData,
      to: '/chat',
      icon: navIconForModulePath('/chat')
    },
    {
      key: 'tokens-total',
      label: t('dashboard.advanced.totalTokensPeriod', { days: tokenDays }),
      value: totalTokens > 0 ? formatNumber(totalTokens) : noData,
      hint: tokenHint,
      icon: Sparkles
    }
  ];
});

function statusToneVariant(status: string): StatusVariant {
  const normalized = String(status || '').toLowerCase();
  if (/(^good$|^normal$|^online$|^healthy$|^active$|^success$|^ready$|^done$|^正常$|^良好$|^在线$|^健康$)/.test(normalized)) {
    return 'success';
  }
  if (/(^processing$|^pending$|^warning$|^warn$|^unknown$|^empty$|^处理中$|^警告$|^未知$|^空$)/.test(normalized)) {
    return 'warning';
  }
  if (/(^abnormal$|^offline$|^error$|^fail$|^failed$|^unhealthy$|^danger$|^异常$|^离线$|^失败$|^危险$)/.test(normalized)) {
    return 'danger';
  }
  return 'neutral';
}

function displayStatusLabel(status: string | null | undefined) {
  return localizeBackendStatusLabel(t, status);
}

function localizeAiModelStatus(model: string | null | undefined) {
  const raw = String(model || '').trim();
  const normalized = raw.toLowerCase();
  const modelStatusMap: Record<string, string> = {
    '配置错误': t('dashboard.system.modelStatus.configError'),
    '服务不可用': t('dashboard.system.modelStatus.serviceUnavailable'),
    '连接失败': t('dashboard.system.modelStatus.connectionFailed'),
    '未知模型': t('dashboard.system.modelStatus.unknownModel'),
    'config error': t('dashboard.system.modelStatus.configError'),
    'configuration error': t('dashboard.system.modelStatus.configError'),
    'service unavailable': t('dashboard.system.modelStatus.serviceUnavailable'),
    'connection failed': t('dashboard.system.modelStatus.connectionFailed'),
    'unknown model': t('dashboard.system.modelStatus.unknownModel')
  };
  if (!raw) return '';
  return modelStatusMap[raw] || modelStatusMap[normalized] || raw;
}

/** 健康/异常文案保留；否则映射为厂商名（DeepSeek、OpenAI 等） */
function displayAiModelLabel(model: string | null | undefined) {
  const raw = String(model || '').trim();
  if (!raw) return '';
  const statusLabel = localizeAiModelStatus(raw);
  if (statusLabel !== raw) return statusLabel;
  return resolveModelVendorLabel(raw, t);
}

function formatNumber(value: number | string) {
  const numeric = typeof value === 'string' ? Number(value) : value;
  return Number.isFinite(numeric) ? new Intl.NumberFormat(locale.value === 'en' ? 'en-US' : 'zh-CN').format(numeric) : String(value);
}

function formatMetricValue(value: unknown, unit: string) {
  if (value === undefined || value === null || value === '') return t('dashboard.system.unknown');
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isFinite(numeric)) {
    if (unit === 'ms') return `${numeric.toFixed(0)}${unit}`;
    return unit ? `${numeric}${unit}` : `${numeric}`;
  }
  return String(value);
}


function buildFallbackActivities() {
  const recent = overview.value?.recent_activity;
  if (!recent) return [];

  const items: RecentActivityRecord[] = [];
  if (recent.test_cases > 0) {
    items.push({
      type: 'case',
      message: t('dashboard.activities.fallback.case', { count: formatNumber(recent.test_cases) }),
      time: overview.value?.generated_at || undefined,
      icon: 'TC',
      color: 'primary'
    });
  }
  if (recent.requirements > 0) {
    items.push({
      type: 'requirement',
      message: t('dashboard.activities.fallback.requirement', { count: formatNumber(recent.requirements) }),
      time: overview.value?.generated_at || undefined,
      icon: 'DO',
      color: 'success'
    });
  }
  if (recent.knowledge_files > 0) {
    items.push({
      type: 'knowledge',
      message: t('dashboard.activities.fallback.knowledge', { count: formatNumber(recent.knowledge_files) }),
      time: overview.value?.generated_at || undefined,
      icon: 'KB',
      color: 'info'
    });
  }
  if (recent.chat_messages > 0) {
    items.push({
      type: 'chat',
      message: t('dashboard.activities.fallback.chat', { count: formatNumber(recent.chat_messages) }),
      time: overview.value?.generated_at || undefined,
      icon: 'CH',
      color: 'warning'
    });
  }

  return items;
}

function handlePartialErrorRetry() {
  errorVisible.value = true;
  void handleRefresh();
}

async function handleExportStats() {
  if (exporting.value) return;
  exporting.value = true;
  try {
    const blob = await exportStats({ type: 'overview', format: 'csv', days: OVERVIEW_DAYS });
    const stamp = new Date().toISOString().slice(0, 10);
    triggerBlobDownload(blob, `stats-overview-${stamp}.csv`);
    toast.success(t('dashboard.message.exportSuccess'));
  } catch (error) {
    toast.error(getUserFacingErrorMessage(error, t('dashboard.message.exportFailed')));
  } finally {
    exporting.value = false;
  }
}

async function handleExportBundle() {
  if (bundleExporting.value) return;
  bundleExporting.value = true;
  try {
    const [casesResp, reqResp] = await Promise.all([
      listCases({ page: 1, per_page: 1000 }),
      getDocumentRequirements({ page: 1, per_page: 1000 })
    ]);
    const blob = await exportBatchZip({
      export_cases: true,
      cases: casesResp.cases || [],
      case_formats: ['excel', 'csv', 'json'],
      export_requirements: true,
      requirements: reqResp.requirements || [],
      export_chat: false
    });
    const stamp = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);
    triggerBlobDownload(blob, `batch_export_${stamp}.zip`);
    toast.success(t('dashboard.message.bundleExportSuccess'));
  } catch (error) {
    toast.error(getUserFacingErrorMessage(error, t('dashboard.message.bundleExportFailed')));
  } finally {
    bundleExporting.value = false;
  }
}

let loadDashboardSeq = 0;

async function loadAdvancedMetrics(options: { bustCache?: boolean; requestSeq?: number } = {}) {
  const cacheQuery = options.bustCache ? { _: Date.now() } : {};
  advancedLoading.value = true;
  advancedError.value = '';

  try {
    const [usageResult, tokensResult] = await Promise.allSettled([
      getUsageStats({ days: OVERVIEW_DAYS, ...cacheQuery }),
      getTokenStats({ days: 7, ...cacheQuery })
    ]);

    if (options.requestSeq !== undefined && options.requestSeq !== loadDashboardSeq) return;

    usageStats.value = usageResult.status === 'fulfilled' ? usageResult.value : null;
    tokenStats.value = tokensResult.status === 'fulfilled' ? tokensResult.value : null;

    const failures = [usageResult, tokensResult].filter((item) => item.status === 'rejected');
    if (failures.length === 2) {
      advancedError.value = getUserFacingErrorMessage(
        (failures[0] as PromiseRejectedResult).reason,
        t('dashboard.message.advancedFailed')
      );
      advancedMetricsLoaded.value = false;
      return;
    }

    advancedMetricsLoaded.value = true;
  } finally {
    if (options.requestSeq === undefined || options.requestSeq === loadDashboardSeq) {
      advancedLoading.value = false;
    }
  }
}

async function loadDashboard(options: { bustCache?: boolean } = {}) {
  const requestSeq = ++loadDashboardSeq;
  const cacheQuery = options.bustCache ? { _: Date.now() } : {};

  overviewLoading.value = true;
  systemLoading.value = true;
  activitiesLoading.value = true;
  refreshing.value = true;
  errorVisible.value = true;
  attentionDismissed.value = false;

  overviewError.value = '';
  systemError.value = '';
  activitiesError.value = '';
  advancedError.value = '';
  logsError.value = '';

  const advancedPromise = loadAdvancedMetrics({ bustCache: options.bustCache, requestSeq });

  try {
    const [overviewResult, healthResult, systemResult, activitiesResult, logsResult] = await Promise.allSettled([
      getOverviewStats({ days: OVERVIEW_DAYS, ...cacheQuery }),
      getHealthStatus(cacheQuery),
      getSystemStatus(cacheQuery),
      getRecentActivities({ days: OVERVIEW_DAYS, ...cacheQuery }),
      canOpenConfig.value ? getLogStats({ hours: LOG_STATS_HOURS, ...cacheQuery }) : Promise.resolve(null)
    ]);

    if (requestSeq !== loadDashboardSeq) return;

    if (overviewResult.status === 'fulfilled') {
      overview.value = overviewResult.value;
    } else {
      overview.value = null;
      overviewError.value = getUserFacingErrorMessage(overviewResult.reason, t('dashboard.message.overviewFailed'));
    }

    if (healthResult.status === 'fulfilled') {
      health.value = healthResult.value;
    } else {
      health.value = null;
      systemError.value = getUserFacingErrorMessage(healthResult.reason, t('dashboard.message.healthFailed'));
    }

    if (systemResult.status === 'fulfilled') {
      system.value = systemResult.value;
    } else {
      system.value = null;
      if (!systemError.value) {
        systemError.value = getUserFacingErrorMessage(systemResult.reason, t('dashboard.message.systemFailed'));
      }
    }

    if (activitiesResult.status === 'fulfilled') {
      activities.value = activitiesResult.value.activities;
      activityCounts.value = activitiesResult.value.counts;
      activityPeriodDays.value = activitiesResult.value.periodDays || 30;
    } else {
      activities.value = buildFallbackActivities();
      activityCounts.value = undefined;
      activitiesError.value = getUserFacingErrorMessage(activitiesResult.reason, t('dashboard.message.activitiesFailed'));
    }

    if (!activities.value.length) {
      activities.value = buildFallbackActivities();
      activityCounts.value = undefined;
    }

    if (logsResult.status === 'fulfilled') {
      logStats.value = logsResult.value;
    } else {
      logStats.value = null;
      logsError.value = getUserFacingErrorMessage(logsResult.reason, t('dashboard.message.logsFailed'));
    }

    await advancedPromise;
  } finally {
    if (requestSeq !== loadDashboardSeq) return;
    overviewLoading.value = false;
    systemLoading.value = false;
    activitiesLoading.value = false;
    refreshing.value = false;
  }
}

async function handleRefresh() {
  if (refreshing.value) return;
  await refreshAppFeatureFlags();
  await loadDashboard({ bustCache: true });
}

onMounted(async () => {
  await loadDashboard();
});
</script>

