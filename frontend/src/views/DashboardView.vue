<template>
  <section class="tp-page tp-dashboard-page">
    <ActionBar :title="t('dashboard.page.title')" :subtitle="t('dashboard.page.subtitle')">
      <template #actions>
        <TpButton variant="ghost" :loading="bundleExporting" :disabled="bundleExporting" @click="handleExportBundle">
          {{ bundleExporting ? t('dashboard.actions.bundleExporting') : t('dashboard.actions.bundleExport') }}
        </TpButton>
        <TpButton variant="ghost" :loading="exporting" :disabled="exporting" @click="handleExportStats">
          {{ exporting ? t('dashboard.actions.exporting') : t('dashboard.actions.export') }}
        </TpButton>
        <TpButton variant="secondary" :loading="refreshing" @click="handleRefresh">
          {{ refreshing ? t('dashboard.actions.refreshing') : t('dashboard.actions.refresh') }}
        </TpButton>
      </template>
    </ActionBar>

    <div v-if="exportNotice" class="tp-risk-block tp-mb-3" :class="exportNoticeType === 'success' ? 'tp-risk-block--success' : 'tp-risk-block--danger'">
      <div class="tp-flex tp-align-start tp-justify-between tp-gap-3">
        <div class="tp-flex-grow-1">{{ exportNotice }}</div>
        <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="exportNotice = ''">
          {{ t('common.actions.close') }}
        </TpButton>
      </div>
    </div>

    <BaseState
      v-if="hasPartialError"
      variant="error"
      :title="t('dashboard.message.partialFailure')"
      :message="partialErrorText"
      :retry-text="t('common.actions.retry')"
      @retry="dismissErrorNotice"
    />

    <TpCard class="tp-dashboard-hero tp-mb-3">
      <template #header>
        <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-3">
          <div>
            <div class="tp-section-title">{{ t('dashboard.welcome.kicker') }}</div>
            <div class="tp-page-title__heading">{{ t('dashboard.welcome.title') }}</div>
            <div class="tp-page-title__subtitle tp-mb-0">{{ t('dashboard.welcome.description') }}</div>
          </div>
          <div class="tp-flex tp-flex-wrap tp-gap-2 tp-justify-end">
            <TpTag variant="ai">{{ aiModelLabel }}</TpTag>
            <TpTag :variant="reliabilityVariant">{{ reliabilityLabel }}</TpTag>
            <TpTag v-if="health?.timestamp" variant="neutral">
              {{ t('dashboard.system.updatedAt') }}: {{ formatDateTime(health?.timestamp) }}
            </TpTag>
          </div>
        </div>
      </template>

      <div class="tp-row tp-g-3">
        <div v-for="card in aiCapabilityCards" :key="card.key" class="tp-col-12 tp-col-md-4">
          <TpCard class="h-100">
            <div class="tp-ai-capability-card">
              <div>
                <div class="tp-kpi-label">{{ card.label }}</div>
                <div class="tp-kpi-value">{{ card.value }}</div>
                <div class="tp-kpi-hint">{{ card.hint }}</div>
              </div>
              <div v-if="card.score !== undefined" class="tp-mt-3">
                <TpProgress :value="card.score" :label="card.progressLabel" />
              </div>
              <div v-else class="tp-ai-capability-card__progress-placeholder"></div>
            </div>
          </TpCard>
        </div>
      </div>
    </TpCard>

    <div class="tp-mb-3">
      <BaseState
        v-if="overviewLoading && !overview"
        variant="loading"
        :title="t('dashboard.state.loadingOverview')"
        :message="t('dashboard.state.loadingHint')"
      />
      <div v-else class="tp-row tp-g-3">
        <div v-for="card in kpiCards" :key="card.key" class="tp-col-12 tp-col-md-6 tp-col-xxl-3">
          <KnowledgeStatsCard :label="card.label" :value="card.value" :hint="card.hint" :icon="card.icon" />
        </div>
      </div>
    </div>

    <div class="tp-row tp-g-3">
      <div class="tp-col-12 tp-col-xxl-5">
        <TpCard>
          <template #header>
            <div class="tp-flex tp-align-start tp-justify-between tp-gap-2">
              <div>
                <div class="tp-section-title">{{ t('dashboard.system.title') }}</div>
                <div class="tp-section-subtitle">{{ t('dashboard.system.subtitle') }}</div>
              </div>
              <TpTag :variant="overallStatusVariant">{{ displayStatusLabel(overallStatusRaw) }}</TpTag>
            </div>
          </template>

          <BaseState
            v-if="systemLoading && !system && !health"
            variant="loading"
            :title="t('dashboard.state.loadingSystem')"
            :message="t('dashboard.state.loadingHint')"
          />
          <BaseState
            v-else-if="systemError && !system && !health"
            variant="error"
            :title="t('common.status.error')"
            :message="systemError"
            :retry-text="t('common.actions.retry')"
            @retry="handleRefresh"
          />
          <div v-else class="tp-system-layout">
            <div class="tp-system-summary">
              <div class="tp-system-summary__main">
                <div class="tp-kpi-label">{{ t('dashboard.system.overall') }}</div>
                <div class="tp-system-summary__status">{{ displayStatusLabel(overallStatusRaw) }}</div>
                <div class="tp-system-summary__description">
                  {{ systemSummaryDescription }}
                </div>
              </div>

              <div class="tp-system-summary__grid">
                <div v-for="item in systemSummaryItems" :key="item.key" class="tp-system-summary-card">
                  <div class="tp-system-summary-card__header">
                    <div class="tp-data-title">{{ item.label }}</div>
                    <TpTag :variant="item.variant">{{ item.status }}</TpTag>
                  </div>
                  <div class="tp-system-summary-card__hint">{{ item.hint }}</div>
                </div>
              </div>
            </div>

          </div>
        </TpCard>
      </div>

      <div class="tp-col-12 tp-col-xxl-7">
        <TpCard>
          <template #header>
            <div class="tp-flex tp-align-start tp-justify-between tp-gap-2">
              <div>
                <div class="tp-section-title">{{ t('dashboard.activities.title') }}</div>
                <div class="tp-section-subtitle">{{ t('dashboard.activities.subtitle') }}</div>
              </div>
              <TpTag variant="neutral">{{ activities.length }}</TpTag>
            </div>
          </template>

          <BaseState
            v-if="activitiesLoading && !activities.length"
            variant="loading"
            :title="t('dashboard.state.loadingActivities')"
            :message="t('dashboard.state.loadingHint')"
          />
          <BaseState
            v-else-if="activitiesError && !activities.length"
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
            :message="t('dashboard.activities.emptyMessage')"
          />
          <div v-else class="tp-activity-list">
            <div v-for="item in activities" :key="`${item.type}-${item.time || item.message}`" class="tp-activity-item">
              <div class="tp-flex tp-align-start tp-gap-3">
                <div class="dashboard-activity-icon" :class="item.color || 'tp-activity-icon--muted'">
                  {{ item.icon || 'AI' }}
                </div>
                <div class="tp-flex-grow-1">
                  <div class="tp-data-title">{{ item.message }}</div>
                  <div class="tp-data-subtitle tp-text-start tp-flex tp-flex-wrap tp-gap-2">
                    <span>{{ activityTypeLabel(item.type) }}</span>
                    <span v-if="item.time">{{ formatDateTime(item.time) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TpCard>
      </div>
    </div>

    <div class="tp-row tp-g-3 tp-mt-0">
      <div class="tp-col-12">
        <TpCard>
          <template #header>
            <div class="tp-flex tp-align-start tp-justify-between tp-gap-2">
              <div>
                <div class="tp-section-title">{{ t('dashboard.advanced.title') }}</div>
                <div class="tp-section-subtitle">{{ t('dashboard.advanced.subtitle') }}</div>
              </div>
            </div>
          </template>
          <BaseState
            v-if="advancedLoading && !advancedCards.length"
            variant="loading"
            :title="t('dashboard.state.loadingOverview')"
            :message="t('dashboard.state.loadingHint')"
          />
          <div v-else class="tp-row tp-g-3">
            <div v-for="card in advancedCards" :key="card.key" class="tp-col-12 tp-col-md-6 tp-col-xxl-3">
              <KnowledgeStatsCard :label="card.label" :value="card.value" :hint="card.hint" :icon="card.icon" />
            </div>
          </div>
        </TpCard>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import ActionBar from '@/components/common/ActionBar.vue';
import BaseState from '@/components/common/BaseState.vue';
import KnowledgeStatsCard from '@/components/common/KnowledgeStatsCard.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpCard from '@/components/ui/base/TpCard.vue';
import TpProgress from '@/components/ui/base/TpProgress.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useAiResult } from '@/composables/useAiResult';
import {
  exportBatchZip,
  exportStats,
  getHealthStatus,
  getLogStats,
  getNetworkInfo,
  getOverviewStats,
  getPerformanceStats,
  getRecentActivities,
  getSystemStatus,
  getTokenStats,
  getUsageStats,
  type HealthStatus,
  type LogStatsResponse,
  type NetworkInfoResponse,
  type OverviewStats,
  type PerformanceStatsResponse,
  type RecentActivityRecord,
  type SystemStatus,
  type TokenStatsResponse,
  type UsageStatsResponse
} from '@/api/stats';
import { listCases } from '@/api/cases';
import { getDocumentRequirements } from '@/api/documents';
import { resolveCaseCategoryDisplayName } from '@/utils/caseCategoryI18n';

type StatusVariant = 'primary' | 'ai' | 'success' | 'warning' | 'danger' | 'neutral' | 'info';

interface KpiCard {
  key: string;
  label: string;
  value: string | number;
  hint?: string;
  icon: string;
}

interface AiCapabilityCard {
  key: string;
  label: string;
  value: string;
  hint: string;
  score?: number;
  progressLabel?: string;
}

interface SystemSummaryItem {
  key: string;
  label: string;
  status: string;
  variant: StatusVariant;
  hint: string;
}

const { t, locale } = useI18n();

const overview = ref<OverviewStats | null>(null);
const health = ref<HealthStatus | null>(null);
const system = ref<SystemStatus | null>(null);
const activities = ref<RecentActivityRecord[]>([]);
const performanceStats = ref<PerformanceStatsResponse | null>(null);
const usageStats = ref<UsageStatsResponse | null>(null);
const tokenStats = ref<TokenStatsResponse | null>(null);
const networkInfo = ref<NetworkInfoResponse | null>(null);
const logStats = ref<LogStatsResponse | null>(null);

const overviewLoading = ref(false);
const systemLoading = ref(false);
const activitiesLoading = ref(false);
const refreshing = ref(false);
const advancedLoading = ref(false);
const exporting = ref(false);
const bundleExporting = ref(false);

const overviewError = ref('');
const systemError = ref('');
const activitiesError = ref('');
const networkError = ref('');
const logsError = ref('');
const errorVisible = ref(true);
const exportNotice = ref('');

const overallStatusRaw = computed(() => {
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
  return localizeAiModelStatus(raw);
});

const aiModelLabel = computed(() => healthModelLabel.value || t('dashboard.system.unknown'));

const reliabilityScore = computed(() => {
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

const reliabilityAi = useAiResult(computed(() => ({ confidence: reliabilityScore.value })));
const reliabilityLabel = computed(() => `${t('ai.reliabilityScore')} ${reliabilityScore.value}%`);
const reliabilityVariant = computed<StatusVariant>(() => {
  if (reliabilityAi.value.riskLevel === 'danger') return 'danger';
  if (reliabilityAi.value.riskLevel === 'warning') return 'warning';
  return 'success';
});
const overallStatusVariant = computed<StatusVariant>(() => statusToneVariant(overallStatusRaw.value));

const systemSummaryDescription = computed(() => {
  return health.value?.message
    || t('dashboard.system.healthHint');
});

const systemSummaryItems = computed<SystemSummaryItem[]>(() => [
  {
    key: 'health',
    label: t('dashboard.system.healthTitle'),
    status: displayStatusLabel(health.value?.status),
    variant: statusToneVariant(health.value?.status || t('dashboard.system.unknown')),
    hint: systemSummaryDescription.value
  },
  {
    key: 'ai',
    label: t('dashboard.system.aiService'),
    status: displayStatusLabel(system.value?.system?.ai_service?.status),
    variant: statusToneVariant(system.value?.system?.ai_service?.status || t('dashboard.system.unknown')),
    hint: `${t('dashboard.system.model')} · ${String(system.value?.system?.ai_service?.model || healthModelLabel.value || t('dashboard.system.unknown'))}`
  },
  {
    key: 'knowledge',
    label: t('dashboard.system.knowledge'),
    status: displayStatusLabel(system.value?.system?.knowledge?.status),
    variant: statusToneVariant(system.value?.system?.knowledge?.status || t('dashboard.system.unknown')),
    hint: `${t('dashboard.system.documents')} ${formatMetricValue(system.value?.system?.knowledge?.docs, '')} · ${t('dashboard.system.vectors')} ${formatMetricValue(system.value?.system?.knowledge?.vectors, '')}`
  },
  {
    key: 'performance',
    label: t('dashboard.system.performance'),
    status: displayStatusLabel(system.value?.system?.performance?.status),
    variant: statusToneVariant(system.value?.system?.performance?.status || t('dashboard.system.unknown')),
    hint: `${t('dashboard.system.cpu')} ${formatMetricValue(system.value?.system?.performance?.cpu, '%')} · ${t('dashboard.system.memory')} ${formatMetricValue(system.value?.system?.performance?.memory, 'GB')}`
  }
]);

const aiCapabilityCards = computed<AiCapabilityCard[]>(() => {
  const docs = Number(system.value?.system?.knowledge?.docs || 0);
  const vectors = Number(system.value?.system?.knowledge?.vectors || 0);

  return [
    {
      key: 'model',
      label: t('dashboard.system.model'),
      value: aiModelLabel.value,
      hint: t('dashboard.system.aiService')
    },
    {
      key: 'coverage',
      label: t('ai.knowledgeCoverage'),
      value: `${docs} / ${vectors}`,
      hint: t('dashboard.system.knowledge'),
      score: docs > 0 ? Math.min(100, Math.round((vectors / Math.max(docs, 1)) * 100)) : 0,
      progressLabel: t('ai.knowledgeCoverage')
    },
    {
      key: 'reliability',
      label: t('ai.reliabilityScore'),
      value: `${reliabilityScore.value}%`,
      hint: t('ai.systemTrustIndicator'),
      score: reliabilityScore.value,
      progressLabel: t('ai.reliabilityScore')
    }
  ];
});

const partialErrorText = computed(() => {
  return [overviewError.value, systemError.value, activitiesError.value, networkError.value, logsError.value].filter(Boolean).join(' | ');
});

const hasPartialError = computed(() => errorVisible.value && Boolean(partialErrorText.value));
const exportNoticeType = ref<'success' | 'danger'>('success');

const kpiCards = computed<KpiCard[]>(() => {
  const totals = overview.value?.totals;
  const recent = overview.value?.recent_activity;

  return [
    {
      key: 'cases',
      label: t('dashboard.kpi.totalCases'),
      value: overview.value ? formatNumber(totals?.test_cases ?? 0) : '-',
      hint: t('dashboard.kpi.casesHint'),
      icon: 'TC'
    },
    {
      key: 'documents',
      label: t('dashboard.kpi.totalDocuments'),
      value: overview.value ? formatNumber(totals?.requirements ?? 0) : '-',
      hint: recent ? `${t('dashboard.kpi.recentDocuments')}: ${formatNumber(recent.requirements ?? 0)}` : t('dashboard.kpi.documentsHint'),
      icon: 'DO'
    },
    {
      key: 'knowledge',
      label: t('dashboard.kpi.totalKnowledge'),
      value: overview.value ? formatNumber(totals?.knowledge_files ?? 0) : '-',
      hint: t('dashboard.kpi.knowledgeHint'),
      icon: 'KB'
    },
    {
      key: 'chat',
      label: t('dashboard.kpi.totalChatSessions'),
      value: overview.value ? formatNumber(totals?.chat_sessions ?? 0) : '-',
      hint: recent ? `${t('dashboard.kpi.recentChats')}: ${formatNumber(recent.chat_messages ?? 0)}` : t('dashboard.kpi.chatHint'),
      icon: 'AI'
    }
  ];
});

const advancedCards = computed<KpiCard[]>(() => {
  const perfSummary = performanceStats.value?.summary || {};
  const perfCategories = Object.keys(perfSummary);
  const perfCount = perfCategories.length;
  const usageDist = usageStats.value?.category_distribution || {};
  const topCategory = Object.entries(usageDist).sort((a, b) => Number(b[1]) - Number(a[1]))[0];
  const tokenSummary = tokenStats.value?.summary;
  const topModel = (tokenStats.value?.by_model || []).slice().sort((a, b) => Number(b.total_tokens || 0) - Number(a.total_tokens || 0))[0];

  return [
    {
      key: 'perf-categories',
      label: t('dashboard.advanced.perfCategoryCount'),
      value: formatNumber(perfCount),
      hint: t('dashboard.advanced.perfCategoryHint'),
      icon: 'PF'
    },
    {
      key: 'usage-top-category',
      label: t('dashboard.advanced.topUsageCategory'),
      value: topCategory ? resolveCaseCategoryDisplayName(String(topCategory[0]), t) : t('dashboard.system.unknown'),
      hint: topCategory ? `${t('dashboard.advanced.count')}: ${formatNumber(Number(topCategory[1]))}` : t('dashboard.system.unknown'),
      icon: 'US'
    },
    {
      key: 'tokens-total',
      label: t('dashboard.advanced.totalTokens'),
      value: tokenSummary ? formatNumber(Number(tokenSummary.total_tokens || 0)) : '-',
      hint: tokenSummary ? `${t('dashboard.advanced.avgTokens')}: ${formatNumber(Number(tokenSummary.avg_tokens_per_message || 0))}` : t('dashboard.system.unknown'),
      icon: 'TK'
    },
    {
      key: 'tokens-top-model',
      label: t('dashboard.advanced.topTokenModel'),
      value: topModel?.model || t('dashboard.system.unknown'),
      hint: topModel ? `${t('dashboard.advanced.tokens')}: ${formatNumber(Number(topModel.total_tokens || 0))}` : t('dashboard.system.unknown'),
      icon: 'MD'
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
  const normalized = String(status || '').toLowerCase();
  const statusLabelMap: Record<string, string> = {
    online: t('common.status.healthy'),
    healthy: t('common.status.healthy'),
    active: t('common.status.healthy'),
    success: t('common.status.healthy'),
    ready: t('common.status.healthy'),
    done: t('common.status.healthy'),
    good: t('common.status.healthy'),
    normal: t('common.status.healthy'),
    '在线': t('common.status.healthy'),
    '健康': t('common.status.healthy'),
    '良好': t('common.status.healthy'),
    '正常': t('common.status.healthy'),
    warning: t('common.status.warning'),
    warn: t('common.status.warning'),
    pending: t('common.status.warning'),
    processing: t('common.status.warning'),
    unknown: t('dashboard.system.unknown'),
    empty: t('common.status.empty'),
    '警告': t('common.status.warning'),
    '处理中': t('common.status.warning'),
    '未知': t('dashboard.system.unknown'),
    '空': t('common.status.empty'),
    offline: t('common.status.unhealthy'),
    error: t('common.status.unhealthy'),
    fail: t('common.status.unhealthy'),
    failed: t('common.status.unhealthy'),
    unhealthy: t('common.status.unhealthy'),
    danger: t('common.status.unhealthy'),
    abnormal: t('common.status.unhealthy'),
    '离线': t('common.status.unhealthy'),
    '失败': t('common.status.unhealthy'),
    '危险': t('common.status.unhealthy'),
    '异常': t('common.status.unhealthy')
  };
  if (!normalized || normalized === 'unknown') {
    return t('dashboard.system.unknown');
  }
  return statusLabelMap[normalized] || status || t('dashboard.system.unknown');
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

function formatDateTime(value: string | null | undefined) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale.value === 'en' ? 'en-US' : 'zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function maskIp(value: string) {
  const parts = value.split('.');
  if (parts.length !== 4) return t('dashboard.system.networkHidden');
  return `${parts[0]}.${parts[1]}.*.*`;
}

function activityTypeLabel(type: string) {
  if (type === 'case') return t('dashboard.activities.types.case');
  if (type === 'requirement') return t('dashboard.activities.types.requirement');
  if (type === 'knowledge') return t('dashboard.activities.types.knowledge');
  if (type === 'chat') return t('dashboard.activities.types.chat');
  return t('dashboard.activities.types.other');
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
      color: 'tp-text-primary'
    });
  }
  if (recent.requirements > 0) {
    items.push({
      type: 'requirement',
      message: t('dashboard.activities.fallback.requirement', { count: formatNumber(recent.requirements) }),
      time: overview.value?.generated_at || undefined,
      icon: 'DO',
      color: 'tp-text-success'
    });
  }
  if (recent.knowledge_files > 0) {
    items.push({
      type: 'knowledge',
      message: t('dashboard.activities.fallback.knowledge', { count: formatNumber(recent.knowledge_files) }),
      time: overview.value?.generated_at || undefined,
      icon: 'KB',
      color: 'tp-text-info'
    });
  }
  if (recent.chat_messages > 0) {
    items.push({
      type: 'chat',
      message: t('dashboard.activities.fallback.chat', { count: formatNumber(recent.chat_messages) }),
      time: overview.value?.generated_at || undefined,
      icon: 'AI',
      color: 'tp-text-warning'
    });
  }

  return items;
}

function dismissErrorNotice() {
  errorVisible.value = false;
}

function triggerBlobDownload(blob: Blob, fileName: string) {
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(blobUrl);
}

async function handleExportStats() {
  if (exporting.value) return;
  exporting.value = true;
  exportNotice.value = '';
  try {
    const blob = await exportStats({ type: 'overview', format: 'csv', days: 7 });
    const stamp = new Date().toISOString().slice(0, 10);
    triggerBlobDownload(blob, `stats-overview-${stamp}.csv`);
    exportNoticeType.value = 'success';
    exportNotice.value = t('dashboard.message.exportSuccess');
  } catch (error) {
    exportNoticeType.value = 'danger';
    exportNotice.value = error instanceof Error ? error.message : t('dashboard.message.exportFailed');
  } finally {
    exporting.value = false;
  }
}

async function handleExportBundle() {
  if (bundleExporting.value) return;
  bundleExporting.value = true;
  exportNotice.value = '';
  try {
    const [casesResp, reqResp] = await Promise.all([
      listCases({ page: 1, per_page: 1000 }),
      getDocumentRequirements({ page: 1, per_page: 1000 })
    ]);
    const blob = await exportBatchZip({
      export_cases: true,
      cases: (casesResp.cases || []) as Array<Record<string, unknown>>,
      case_formats: ['excel', 'csv', 'json'],
      export_requirements: true,
      requirements: (reqResp.requirements || []) as Array<Record<string, unknown>>,
      export_chat: false
    });
    const stamp = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);
    triggerBlobDownload(blob, `batch_export_${stamp}.zip`);
    exportNoticeType.value = 'success';
    exportNotice.value = t('dashboard.message.bundleExportSuccess');
  } catch (error) {
    exportNoticeType.value = 'danger';
    exportNotice.value = error instanceof Error ? error.message : t('dashboard.message.bundleExportFailed');
  } finally {
    bundleExporting.value = false;
  }
}

async function loadDashboard() {
  overviewLoading.value = true;
  systemLoading.value = true;
  activitiesLoading.value = true;
  refreshing.value = true;
  advancedLoading.value = true;
  errorVisible.value = true;

  overviewError.value = '';
  systemError.value = '';
  activitiesError.value = '';
  networkError.value = '';
  logsError.value = '';

  try {
    const [overviewResult, healthResult, systemResult, activitiesResult, performanceResult, usageResult, tokensResult, networkResult, logsResult] = await Promise.allSettled([
      getOverviewStats(),
      getHealthStatus(),
      getSystemStatus(),
      getRecentActivities(),
      getPerformanceStats({ hours: 24 }),
      getUsageStats({ days: 30 }),
      getTokenStats({ days: 7 }),
      getNetworkInfo(),
      getLogStats({ hours: 24 })
    ]);

    if (overviewResult.status === 'fulfilled') {
      overview.value = overviewResult.value;
    } else {
      overview.value = null;
      overviewError.value = overviewResult.reason instanceof Error ? overviewResult.reason.message : t('dashboard.message.overviewFailed');
    }

    if (healthResult.status === 'fulfilled') {
      health.value = healthResult.value;
    } else {
      health.value = null;
      systemError.value = healthResult.reason instanceof Error ? healthResult.reason.message : t('dashboard.message.healthFailed');
    }

    if (systemResult.status === 'fulfilled') {
      system.value = systemResult.value;
    } else {
      system.value = null;
      if (!systemError.value) {
        systemError.value = systemResult.reason instanceof Error ? systemResult.reason.message : t('dashboard.message.systemFailed');
      }
    }

    if (activitiesResult.status === 'fulfilled') {
      activities.value = activitiesResult.value.activities;
    } else {
      activities.value = buildFallbackActivities();
      activitiesError.value = activitiesResult.reason instanceof Error ? activitiesResult.reason.message : t('dashboard.message.activitiesFailed');
    }

    if (!activities.value.length) {
      activities.value = buildFallbackActivities();
    }

    performanceStats.value = performanceResult.status === 'fulfilled' ? performanceResult.value : null;
    usageStats.value = usageResult.status === 'fulfilled' ? usageResult.value : null;
    tokenStats.value = tokensResult.status === 'fulfilled' ? tokensResult.value : null;
    if (networkResult.status === 'fulfilled') {
      networkInfo.value = networkResult.value;
    } else {
      networkInfo.value = null;
      networkError.value = networkResult.reason instanceof Error ? networkResult.reason.message : t('dashboard.message.networkFailed');
    }
    if (logsResult.status === 'fulfilled') {
      logStats.value = logsResult.value;
    } else {
      logStats.value = null;
      logsError.value = logsResult.reason instanceof Error ? logsResult.reason.message : t('dashboard.message.logsFailed');
    }
  } finally {
    overviewLoading.value = false;
    systemLoading.value = false;
    activitiesLoading.value = false;
    advancedLoading.value = false;
    refreshing.value = false;
  }
}

async function handleRefresh() {
  await loadDashboard();
}

onMounted(async () => {
  await loadDashboard();
});
</script>

<style scoped>
.tp-ai-capability-card {
  min-height: 156px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.tp-ai-capability-card__progress-placeholder {
  height: 28px;
}

.tp-system-layout {
  display: grid;
  gap: 16px;
}

.tp-system-summary {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.35fr);
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-lg);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--tp-color-primary-600) 6%, var(--tp-bg-surface)), var(--tp-bg-surface) 52%),
    var(--tp-bg-surface);
}

.tp-system-summary__main {
  display: grid;
  align-content: start;
  gap: 10px;
}

.tp-system-summary__status {
  font-size: 1.85rem;
  font-weight: 800;
  line-height: 1.05;
  color: var(--tp-color-text-900);
}

.tp-system-summary__description {
  color: var(--tp-color-text-500);
  line-height: 1.6;
  max-width: 32ch;
}

.tp-system-summary__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tp-system-summary-card {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md);
  background: color-mix(in srgb, var(--tp-bg-surface) 78%, white);
}

.tp-system-summary-card {
  padding: 14px;
}

.tp-system-summary-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.tp-system-summary-card__hint {
  margin-top: 10px;
  color: var(--tp-color-text-500);
  font-size: 0.875rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

@media (max-width: 1199px) {
  .tp-system-summary {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .tp-system-summary__grid {
    grid-template-columns: 1fr;
  }
}
</style>

