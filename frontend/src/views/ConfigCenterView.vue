<template>
  <section :class="pageFluidShellMarkedClass(pageMarkerConfig)">
    <PageNoticeBanner
      :notice="pageBanner"
      @close="clearPageBanner"
    />

    <input
      ref="importInput"
      class="hidden"
      type="file"
      accept=".json,.yaml,.yml"
      @change="handleImportFileChange"
    />

    <div :class="grid12StretchClass">
      <aside :class="colSpan12Xl3">
        <PagePanel aside :class="cn(configSidebarStickyClass, 'h-full')" :padded="false">
          <SidebarMenu :title="t('config.category.title')" :aria-label="t('config.category.title')">
            <BaseState
              v-if="categoriesLoading"
              variant="loading"
              :title="t('config.state.loadingCategories')"
            />
            <BaseState
              v-else-if="categoriesError"
              variant="error"
              :title="t('common.status.error')"
              :message="categoriesError"
              :retry-text="t('common.actions.retry')"
              @retry="handleReloadCategories"
            />
            <template v-else>
              <button
                v-for="entry in configSidebarNavEntries"
                :key="resolveSidebarNavEntryId(entry)"
                type="button"
                :class="[
                  navItemClass({
                    active: resolveSidebarNavEntryId(entry) === selectedCategoryId,
                    framed: true
                  }),
                  configCategoryItemClass
                ]"
                @click="handleSelectCategory(resolveSidebarNavEntryId(entry))"
              >
                <div class="min-w-0 flex-1 text-left">
                  <div :class="dataTitleClass">{{ resolveSidebarNavEntryLabel(entry) }}</div>
                  <div :class="dataSubtitleClass">{{ resolveSidebarNavEntryDescription(entry) }}</div>
                </div>
              </button>
            </template>
          </SidebarMenu>
        </PagePanel>
      </aside>

      <section :class="colSpan12Xl9">
        <PagePanel class="h-full" :title="configPanelTitle">
          <template #actions>
            <div :class="pageToolbarStripClass">
              <TpButton
                variant="ghost"
                size="sm"
                :loading="configPanelRefreshLoading"
                @click="handleConfigPanelToolbarRefresh"
              >
                {{ t('common.actions.refresh') }}
              </TpButton>
              <template v-if="!isAuditCategorySelected">
                <TpButton
                  variant="ghost"
                  size="sm"
                  :loading="exporting"
                  :aria-label="exporting ? t('config.actions.exporting') : undefined"
                  @click="handleExport"
                >
                  {{ t('config.actions.export') }}
                </TpButton>
                <TpButton
                  variant="ghost"
                  size="sm"
                  :loading="importing"
                  :aria-label="importing ? t('config.actions.importing') : undefined"
                  @click="handleImportClick"
                >
                  {{ t('config.actions.import') }}
                </TpButton>
              </template>
            </div>
          </template>
          <template v-if="isAuditCategorySelected">
            <BaseState v-if="auditLogsLoading" variant="loading" :title="t('config.audit.loading')" />
            <BaseState
              v-else-if="auditLogsError"
              variant="error"
              :title="t('common.status.error')"
              :message="auditLogsError"
              :retry-text="t('common.actions.retry')"
              @retry="loadAuditLogs"
            />
            <BaseState v-else-if="!auditLogs.length" variant="empty" :title="t('config.audit.empty')" />
            <ul
              v-else
              :class="configAuditLogListClass(auditLogs.length > CONFIG_AUDIT_LOG_SCROLL_THRESHOLD)"
            >
              <li
                v-for="(log, index) in auditLogs"
                :key="`${log.id ?? log.key ?? 'log'}-${index}`"
                class="rounded-md border border-border bg-[var(--tp-bg-subtle)] px-3 py-2"
              >
                <div class="font-medium text-foreground">{{ log.key || '-' }} · {{ log.action || '-' }}</div>
                <div class="mt-1 text-xs text-muted-foreground">
                  {{ formatAuditLogTime(log.created_at) }}
                  <span v-if="log.operator"> · {{ log.operator }}</span>
                </div>
                <div v-if="log.old_value != null || log.new_value != null" class="mt-1 text-xs text-muted-foreground">
                  {{
                    t('config.audit.change', {
                      oldValue: String(log.old_value ?? '-'),
                      newValue: String(log.new_value ?? '-')
                    })
                  }}
                </div>
              </li>
            </ul>
          </template>

          <template v-else>
            <BaseState
              v-if="itemsLoading"
              variant="loading"
              :title="t('config.state.loadingItems')"
              :message="t('config.panel.loading')"
            />
            <BaseState
              v-else-if="itemsError"
              variant="error"
              :title="t('common.status.error')"
              :message="itemsError"
              :retry-text="t('common.actions.retry')"
              @retry="handleReloadCurrentCategory"
            />

            <template v-else>
              <BaseState
                v-if="!selectedCategoryId"
                variant="empty"
                :title="t('config.state.noCategorySelected')"
                :message="t('config.category.selectHint')"
              />

              <template v-else>
                <BaseState
                  v-if="!currentItems.length"
                  variant="empty"
                  :title="t('config.panel.empty')"
                />

                <template v-else>
                <div v-if="selectedCategoryId === 'ai_model'" :class="configOverviewClass">
                  <TableToolbar
                    class="mb-4"
                    :title="t('configCenter.providerUi.title')"
                    :subtitle="providerUiSubtitle || undefined"
                  >
                    <template v-if="dirtyCount > 0" #actions>
                      <div :class="[captionTextClass, configToolbarStatusClass, 'text-left lg:text-right']">
                        {{ configDirtySummary }}
                      </div>
                    </template>
                  </TableToolbar>

                  <PagePanel
                    :class="cn(configSectionPanelClass({ scope: 'provider', active: true }), 'mb-3')"
                    :title="t('configCenter.defaultSetting')"
                    :subtitle="providerUiSaveHint || undefined"
                  >
                    <template #actions>
                      <div :class="pageToolbarStripClass">
                        <TpButton
                          variant="ghost"
                          size="sm"
                          :disabled="itemsLoading || saving"
                          @click="resetQuickSection"
                        >
                          {{ t('config.actions.reload') }}
                        </TpButton>
                        <TpButton
                          variant="ghost"
                          size="sm"
                          :disabled="quickFieldDisabled || saving"
                          @click="clearQuickField"
                        >
                          {{ t('config.actions.clearValue') }}
                        </TpButton>
                        <TpTag :variant="quickProviderEnabled ? 'success' : 'neutral'">
                          {{ quickProviderEnabled ? t('configCenter.providerUi.active') : t('configCenter.providerUi.inactive') }}
                        </TpTag>
                      </div>
                    </template>

                    <div :class="grid12Class">
                      <div :class="colSpan12Lg4">
                        <TpInput
                          v-model="quickSelectedProvider"
                          as="select"
                          :label="t('configCenter.itemLabel.DEFAULT_COMPANY')"
                          :options="getProviderOptions()"
                        />
                      </div>

                      <div :class="colSpan12Lg8">
                        <TpInput
                          v-model="quickFieldValue"
                          :label="quickFieldLabel"
                          :type="quickFieldInputType"
                          :disabled="quickFieldDisabled"
                          :placeholder="quickFieldPlaceholder"
                          :helper="quickFieldHelper"
                        />
                      </div>
                    </div>

                    <div :class="cn(grid12Class, 'mt-4')">
                      <div
                        v-for="item in providerEnableItems"
                        :key="item.key"
                        :class="colSpan12Lg4"
                      >
                        <ConfigFormItem
                          :model-value="item.value"
                          kind="boolean"
                          :label="resolveItemLabel(item)"
                          :dirty="isItemDirty(item)"
                          :switch-key="`switch-${item.key}`"
                          :disabled="item.value === true"
                          @update:model-value="(value) => onProviderEnableChange(item, value)"
                        />
                      </div>
                    </div>
                  </PagePanel>

                  <PagePanel
                    v-if="
                      aiModelTokenBudget.chatItem ||
                      aiModelTokenBudget.hasGenerationMaxTokens ||
                      tokenSessionGuardItems.length
                    "
                    :class="cn(configSectionPanelClass({ scope: 'shared' }), 'mb-3')"
                    :title="t('config.section.tokenBudget')"
                  >
                    <div
                      v-if="aiModelTokenBudget.chatItem || aiModelTokenBudget.hasGenerationMaxTokens"
                      :class="configFormStackClass"
                    >
                      <ConfigFormItem
                        v-if="aiModelTokenBudget.chatItem"
                        :key="aiModelTokenBudget.chatItem.key"
                        v-model:modelValue="aiModelTokenBudget.chatItem.value"
                        :kind="aiModelTokenBudget.chatItem.inputKind"
                        :label="resolveItemLabel(aiModelTokenBudget.chatItem)"
                        :placeholder="resolveItemPlaceholder(aiModelTokenBudget.chatItem)"
                        :helper="resolveItemHelper(aiModelTokenBudget.chatItem)"
                        :error="aiModelTokenBudget.chatItem.error"
                        :dirty="isItemDirty(aiModelTokenBudget.chatItem)"
                        :required="isItemRequired(aiModelTokenBudget.chatItem)"
                        :options="resolveItemOptions(aiModelTokenBudget.chatItem)"
                        :switch-key="`switch-${aiModelTokenBudget.chatItem.key}`"
                        @blur="handleValidateItem(aiModelTokenBudget.chatItem)"
                      />
                      <ConfigFormItem
                        v-if="aiModelTokenBudget.hasGenerationMaxTokens"
                        v-model:modelValue="generationMaxTokensValue"
                        kind="number"
                        :label="t('configCenter.itemLabel.TR_MAX_TOKENS')"
                        :placeholder="t('config.form.numberPlaceholder')"
                        :helper="t('configCenter.itemDescription.TR_MAX_TOKENS')"
                        :error="generationMaxTokensError"
                        :dirty="generationMaxTokensDirty"
                        switch-key="switch-generation-max-tokens"
                        @blur="handleGenerationMaxTokensBlur"
                      />
                    </div>
                    <div
                      v-if="tokenSessionGuardItems.length"
                      :class="cn(pageSectionDivideClass, configFormStackClass)"
                    >
                      <p :class="[configOverviewEyebrowClass, 'mb-3']">{{ t('config.section.tokenSessionGuard') }}</p>
                      <ConfigFormItem
                        v-for="item in tokenSessionGuardItems"
                        :key="item.key"
                        v-model:modelValue="item.value"
                        :kind="item.inputKind"
                        :label="resolveItemLabel(item)"
                        :placeholder="resolveItemPlaceholder(item)"
                        :helper="resolveItemHelper(item)"
                        :error="item.error"
                        :dirty="isItemDirty(item)"
                        :required="isItemRequired(item)"
                        :options="resolveItemOptions(item)"
                        :switch-key="`switch-${item.key}`"
                        @blur="handleValidateItem(item)"
                      />
                    </div>
                  </PagePanel>
                </div>

                <div v-else :class="configOverviewClass">
                  <TableToolbar
                    class="mb-4"
                    :title="selectedCategoryLabel"
                    :subtitle="selectedCategoryDescription"
                  >
                    <template v-if="dirtyCount > 0" #actions>
                      <div :class="[captionTextClass, configToolbarStatusClass, 'text-left lg:text-right']">
                        {{ configDirtySummary }}
                      </div>
                    </template>
                  </TableToolbar>

                  <div :class="configOverviewHeadClass">
                    <div>
                      <div :class="configOverviewEyebrowClass">{{ t('config.section.providers') }}</div>
                      <div v-if="currentDefaultProviderLabel" :class="configMetaClass">
                        {{ t('config.section.providerHint', { provider: currentDefaultProviderLabel }) }}
                      </div>
                    </div>
                    <div :class="configOverviewMetricsClass">
                      <TpTag variant="neutral">
                        {{ t('config.section.shared') }}
                        <span :class="configOverviewCountClass">{{ groupedConfigSections.shared.items.length }}</span>
                      </TpTag>
                      <TpTag variant="ai">
                        {{ t('config.section.providers') }}
                        <span :class="configOverviewCountClass">{{ groupedConfigSections.providers.length }}</span>
                      </TpTag>
                    </div>
                  </div>

                  <PagePanel
                    v-if="groupedConfigSections.shared.items.length"
                    :class="cn(configSectionPanelClass({ scope: 'shared' }), 'mb-3')"
                    :title="t('config.section.shared')"
                  >
                    <div :class="configFormStackClass">
                      <ConfigFormItem
                        v-for="item in groupedConfigSections.shared.items"
                        :key="item.key"
                        v-model:modelValue="item.value"
                        :kind="item.inputKind"
                        :label="resolveItemLabel(item)"
                        :placeholder="resolveItemPlaceholder(item)"
                        :helper="resolveItemHelper(item)"
                        :error="item.error"
                        :dirty="isItemDirty(item)"
                        :required="isItemRequired(item)"
                        :options="resolveItemOptions(item)"
                        :switch-key="`switch-${item.key}`"
                        @blur="handleValidateItem(item)"
                      />
                    </div>
                  </PagePanel>

                  <div v-if="groupedConfigSections.providers.length" :class="configProviderGridClass">
                    <PagePanel
                      v-for="section in groupedConfigSections.providers"
                      :key="section.key"
                      :class="
                        cn(
                          configSectionPanelClass({
                            scope: 'provider',
                            active: section.active,
                            providerAccent: resolveConfigProviderAccent(section.key)
                          })
                        )
                      "
                      :title="section.title"
                    >
                      <template #actions>
                        <div :class="cn(pageToolbarStripClass, 'gap-2')">
                          <TpTag v-if="section.active" variant="primary">{{ t('config.section.active') }}</TpTag>
                          <TpTag variant="neutral">{{ section.items.length }}</TpTag>
                        </div>
                      </template>

                      <div :class="configFormStackClass">
                        <ConfigFormItem
                          v-for="item in section.items"
                          :key="item.key"
                          v-model:modelValue="item.value"
                          :kind="item.inputKind"
                          :label="resolveItemLabel(item)"
                          :placeholder="resolveItemPlaceholder(item)"
                          :helper="resolveItemHelper(item)"
                          :error="item.error"
                          :dirty="isItemDirty(item)"
                          :required="isItemRequired(item)"
                          :options="resolveItemOptions(item)"
                          :switch-key="`switch-${item.key}`"
                          @blur="handleValidateItem(item)"
                        />
                      </div>
                    </PagePanel>
                  </div>
                </div>
                </template>

                <div
                  v-if="currentItems.length"
                  :class="[configFooterClass, 'flex flex-wrap items-center justify-between gap-2']"
                >
                  <div :class="configMetaClass">
                    <span v-if="saving || exporting || validationPendingCount > 0">
                      {{ activityMessage }}
                    </span>
                    <span v-else>{{ configDirtySummary }}</span>
                  </div>

                  <div :class="pageToolbarStripClass">
                    <TpButton variant="ghost" size="sm" :disabled="saving" @click="handleReloadCurrentCategory">
                      {{ t('config.actions.reload') }}
                    </TpButton>
                    <TpButton
                      variant="primary"
                      size="sm"
                      :loading="saving"
                      :disabled="!currentItems.length"
                      :aria-label="saving ? t('config.actions.saving') : undefined"
                      @click="handleSave"
                    >
                      {{ t('config.actions.save') }}
                    </TpButton>
                  </div>
                </div>
              </template>
            </template>
          </template>
        </PagePanel>
      </section>
    </div>

    <ConfirmDialog
      v-model="unsavedDiscardVisible"
      :title="t('config.message.unsavedChangesTitle')"
      :message="t('config.message.unsavedChangesConfirm')"
      :confirm-text="t('common.actions.confirm')"
      :cancel-text="t('common.actions.cancel')"
      confirm-variant="warning"
      @confirm="onUnsavedDiscardConfirm"
      @cancel="onUnsavedDiscardCancel"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import PagePanel from '@/components/common/PagePanel.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import SidebarMenu from '@/components/layout/SidebarMenu.vue';
import BaseState from '@/components/common/BaseState.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import ConfigFormItem from '@/components/common/ConfigFormItem.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  CONFIG_AUDIT_CATEGORY_ID,
  CONFIG_AUDIT_LOG_SCROLL_THRESHOLD,
  configAuditLogListClass,
  configCategoryItemClass,
  isConfigAuditCategoryId,
  configFooterClass,
  configFormStackClass,
  configMetaClass,
  configOverviewClass,
  configOverviewCountClass,
  configOverviewEyebrowClass,
  configOverviewHeadClass,
  configOverviewMetricsClass,
  configProviderGridClass,
  configSectionPanelClass,
  configSidebarStickyClass,
  configToolbarStatusClass,
  resolveConfigProviderAccent
} from '@/lib/config-ui';
import {
  buildAiModelTokenBudgetSections,
  CONFIG_GENERATION_MAX_TOKENS_KEY,
  CONFIG_SESSION_TOKEN_GUARD_KEYS,
  filterItemsForCategoryGrouping,
  isConfigSessionTokenGuardKey,
  listLegacyProviderGenerationTokenItems,
  syncGenerationMaxTokensToLegacyKeys
} from '@/lib/config-token-ui';
import {
  colSpan12Lg4,
  colSpan12Lg8,
  colSpan12Xl3,
  colSpan12Xl9,
  grid12Class,
  grid12StretchClass,
  pageFluidShellMarkedClass,
  pageMarkerConfig,
  pageSectionDivideClass
} from '@/lib/page-layout-ui';
import { captionTextClass, dataSubtitleClass, dataTitleClass } from '@/lib/page-typography';
import { navItemClass } from '@/lib/shell-ui';
import { pageToolbarStripClass } from '@/lib/page-chrome-ui';
import { cn } from '@/lib/utils';
import { refreshAppFeatureFlags } from '@/composables/useFeatureFlags';
import { usePageNotifier } from '@/composables/usePageNotifier';
import { useAppStore } from '@/stores';
import {
  deleteConfigItem,
  exportConfig,
  getCategories,
  getCategoryConfig,
  importConfig,
  saveConfig,
  validateConfig,
  getConfigAuditLogs,
  type ConfigAuditLogRecord,
  type ConfigCategory,
  type ConfigItem,
  type ConfigOption
} from '@/api/config';
import { ApiError } from '@/api/http';
import { formatDateTime } from '@/lib/format';
import { triggerTextDownload } from '@/lib/download';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';

type NoticeType = 'success' | 'danger' | 'warning' | 'info';

const { t, locale } = useI18n();
const route = useRoute();
const appStore = useAppStore();
const {
  banner: pageBanner,
  clearBanner: clearPageBanner,
  showNotice: notifyPageNotice
} = usePageNotifier();

const categories = ref<ConfigCategory[]>([]);
const currentItems = ref<ConfigItem[]>([]);
const selectedCategoryId = ref('');
const baselineSnapshot = ref<Record<string, string>>({});
const categoriesLoading = ref(false);
const itemsLoading = ref(false);
const saving = ref(false);
const exporting = ref(false);
const importing = ref(false);
const categoriesError = ref('');
const itemsError = ref('');
const validationPending = reactive<Record<string, boolean>>({});
const importInput = ref<HTMLInputElement | null>(null);

type UnsavedDiscardPending =
  | { kind: 'selectCategory'; categoryId: string }
  | { kind: 'reloadCategories' }
  | { kind: 'reloadCurrentCategory' }
  | { kind: 'importClick' };

const unsavedDiscardVisible = ref(false);
const unsavedDiscardPending = ref<UnsavedDiscardPending | null>(null);

function openUnsavedDiscardDialog(pending: UnsavedDiscardPending) {
  unsavedDiscardPending.value = pending;
  unsavedDiscardVisible.value = true;
}

function onUnsavedDiscardCancel() {
  unsavedDiscardPending.value = null;
}

async function runUnsavedDiscardPending() {
  const pending = unsavedDiscardPending.value;
  unsavedDiscardPending.value = null;
  if (!pending) return;
  switch (pending.kind) {
    case 'selectCategory':
      selectedCategoryId.value = pending.categoryId;
      await loadCategoryItems(pending.categoryId);
      break;
    case 'reloadCategories':
      await loadCategories({ preserveSelection: true });
      break;
    case 'reloadCurrentCategory':
      await loadCategoryItems(selectedCategoryId.value);
      break;
    case 'importClick':
      importInput.value?.click();
      break;
    default:
      break;
  }
}

function onUnsavedDiscardConfirm() {
  void runUnsavedDiscardPending();
}

const sortedCategories = computed(() =>
  [...categories.value].sort((left, right) => {
    const leftPriority = left.priority ?? 9999;
    const rightPriority = right.priority ?? 9999;
    if (leftPriority !== rightPriority) return leftPriority - rightPriority;
    return left.id.localeCompare(right.id);
  })
);

type ConfigSidebarNavEntry = { kind: 'category'; category: ConfigCategory } | { kind: 'audit' };

const configSidebarNavEntries = computed((): ConfigSidebarNavEntry[] => {
  const sorted = sortedCategories.value;
  const entries: ConfigSidebarNavEntry[] = sorted.map((category) => ({ kind: 'category', category }));
  const auditEntry: ConfigSidebarNavEntry = { kind: 'audit' };
  const fileProcessingIndex = sorted.findIndex((category) => category.id === 'file_processing');
  if (fileProcessingIndex >= 0) {
    entries.splice(fileProcessingIndex + 1, 0, auditEntry);
  } else {
    entries.push(auditEntry);
  }
  return entries;
});

const isAuditCategorySelected = computed(() => isConfigAuditCategoryId(selectedCategoryId.value));

const configPanelTitle = computed(() =>
  isAuditCategorySelected.value ? t('config.audit.title') : t('config.panel.title')
);

const configPanelRefreshLoading = computed(() =>
  isAuditCategorySelected.value ? auditLogsLoading.value : categoriesLoading.value
);

function handleConfigPanelToolbarRefresh() {
  if (isAuditCategorySelected.value) {
    void loadAuditLogs();
    return;
  }
  void handleReloadCategories();
}

function resolveSidebarNavEntryId(entry: ConfigSidebarNavEntry) {
  return entry.kind === 'audit' ? CONFIG_AUDIT_CATEGORY_ID : entry.category.id;
}

function resolveSidebarNavEntryLabel(entry: ConfigSidebarNavEntry) {
  return entry.kind === 'audit' ? t('config.audit.title') : resolveCategoryLabel(entry.category);
}

function resolveSidebarNavEntryDescription(entry: ConfigSidebarNavEntry) {
  return entry.kind === 'audit' ? t('config.audit.navDescription') : resolveCategoryDescription(entry.category);
}

const selectedCategory = computed(() => categories.value.find((item) => item.id === selectedCategoryId.value) || null);
const selectedCategoryLabel = computed(() => (selectedCategory.value ? resolveCategoryLabel(selectedCategory.value) : ''));
const selectedCategoryDescription = computed(() => (selectedCategory.value ? resolveCategoryDescription(selectedCategory.value) : ''));
const dirtyCount = computed(() => currentItems.value.filter((item) => isItemDirty(item)).length);
const configDirtySummary = computed(() =>
  dirtyCount.value > 0 ? t('config.state.pendingChanges', { count: dirtyCount.value }) : ''
);

function trimI18n(key: string) {
  return String(t(key) || '').trim();
}

const providerUiSubtitle = computed(() => trimI18n('configCenter.providerUi.subtitle'));
const providerUiSaveHint = computed(() => trimI18n('configCenter.providerUi.saveHint'));

const validationPendingCount = computed(() => Object.values(validationPending).filter(Boolean).length);
const providerKeys = ['OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN', 'ANTHROPIC'] as const;
type ProviderKey = (typeof providerKeys)[number];

interface ConfigSection {
  key: ProviderKey | 'shared';
  title: string;
  items: ConfigItem[];
  active: boolean;
}

const currentDefaultProviderLabel = computed(() => {
  const rawValue = currentItems.value.find((item) => item.key === 'DEFAULT_COMPANY')?.value;
  const next = String(rawValue ?? '').toUpperCase();
  if (!providerKeys.includes(next as ProviderKey)) return '';
  return translateKey(`configCenter.provider.${next}`, next);
});

const defaultProviderKey = computed<ProviderKey | ''>(() => {
  const rawValue = currentItems.value.find((item) => item.key === 'DEFAULT_COMPANY')?.value;
  const next = String(rawValue ?? '').toUpperCase();
  return providerKeys.includes(next as ProviderKey) ? (next as ProviderKey) : '';
});

const providerQuickFieldMap: Partial<Record<ProviderKey, {
  key: string;
  inputType: 'password' | 'text';
  labelKey: string;
  placeholderKey: string;
  helperKey: string;
}>> = {
  OPENAI: {
    key: 'OPENAI_API_KEY',
    inputType: 'password',
    labelKey: 'configCenter.providerUi.apiKey',
    placeholderKey: 'configCenter.providerUi.apiKeyPlaceholder',
    helperKey: 'configCenter.defaultSetting'
  },
  DEEPSEEK: {
    key: 'DEEPSEEK_API_KEY',
    inputType: 'password',
    labelKey: 'configCenter.providerUi.apiKey',
    placeholderKey: 'configCenter.providerUi.apiKeyPlaceholder',
    helperKey: 'configCenter.defaultSetting'
  },
  GEMINI: {
    key: 'GEMINI_API_KEY',
    inputType: 'password',
    labelKey: 'configCenter.providerUi.apiKey',
    placeholderKey: 'configCenter.providerUi.apiKeyPlaceholder',
    helperKey: 'configCenter.defaultSetting'
  },
  QWEN: {
    key: 'QWEN_API_KEY',
    inputType: 'password',
    labelKey: 'configCenter.providerUi.apiKey',
    placeholderKey: 'configCenter.providerUi.apiKeyPlaceholder',
    helperKey: 'configCenter.defaultSetting'
  },
  ANTHROPIC: {
    key: 'ANTHROPIC_API_KEY',
    inputType: 'password',
    labelKey: 'configCenter.providerUi.apiKey',
    placeholderKey: 'configCenter.providerUi.apiKeyPlaceholder',
    helperKey: 'configCenter.defaultSetting'
  },
  OLLAMA: {
    key: 'OLLAMA_BASE_URL',
    inputType: 'text',
    labelKey: 'configCenter.providerUi.baseUrl',
    placeholderKey: 'configCenter.providerUi.ollamaBaseUrlPlaceholder',
    helperKey: 'configCenter.providerUi.ollamaBaseUrlHint'
  }
};
const providerEnableKeyMap: Record<ProviderKey, string> = {
  OPENAI: 'ENABLE_OPENAI',
  DEEPSEEK: 'ENABLE_DEEPSEEK',
  OLLAMA: 'ENABLE_OLLAMA',
  GEMINI: 'ENABLE_GEMINI',
  QWEN: 'ENABLE_QWEN',
  ANTHROPIC: 'ENABLE_ANTHROPIC'
};

function activateProvider(provider: ProviderKey) {
  const target = currentItems.value.find((item) => item.key === 'DEFAULT_COMPANY');
  if (target) {
    target.value = provider;
    target.error = '';
  }
  providerKeys.forEach((name) => {
    const enableItem = currentItems.value.find((item) => item.key === providerEnableKeyMap[name]);
    if (!enableItem) return;
    enableItem.value = name === provider;
    enableItem.error = '';
  });
}

function onProviderEnableChange(item: ConfigItem, value: string | number | boolean | null) {
  const provider = providerKeys.find((name) => providerEnableKeyMap[name] === item.key);
  if (provider && value === true) activateProvider(provider);
}

function applySingleActiveProvider(items: ConfigItem[]) {
  const company = String(items.find((item) => item.key === 'DEFAULT_COMPANY')?.value || '').toUpperCase();
  if (!providerKeys.includes(company as ProviderKey)) return;
  providerKeys.forEach((provider) => {
    const enableItem = items.find((item) => item.key === providerEnableKeyMap[provider]);
    if (!enableItem) return;
    enableItem.value = provider === company;
  });
}

const quickSelectedProvider = computed<string>({
  get() {
    return defaultProviderKey.value || 'OPENAI';
  },
  set(value) {
    const target = currentItems.value.find((item) => item.key === 'DEFAULT_COMPANY');
    const next = String(value || 'OPENAI').toUpperCase() as ProviderKey;
    if (!providerKeys.includes(next)) {
      if (target) target.value = 'OPENAI';
      return;
    }
    activateProvider(next);
  }
});

const quickFieldConfig = computed(() => {
  const provider = quickSelectedProvider.value as ProviderKey;
  return providerQuickFieldMap[provider];
});

const quickFieldDisabled = computed(() => !quickFieldConfig.value?.key);

const quickProviderEnabled = computed(() => {
  const provider = quickSelectedProvider.value as ProviderKey;
  if (!providerKeys.includes(provider)) return false;
  const enableItem = currentItems.value.find((item) => item.key === providerEnableKeyMap[provider]);
  return enableItem?.value === true;
});

const providerEnableItems = computed(() =>
  providerKeys
    .map((provider) => currentItems.value.find((item) => item.key === providerEnableKeyMap[provider]))
    .filter((item): item is ConfigItem => Boolean(item))
);

const quickFieldLabel = computed(() => {
  const field = quickFieldConfig.value;
  if (!field) return t('configCenter.providerUi.apiKey');
  return t(field.labelKey);
});

const quickFieldInputType = computed(() => quickFieldConfig.value?.inputType || 'text');

const quickFieldPlaceholder = computed(() => {
  const field = quickFieldConfig.value;
  if (!field) return t('configCenter.providerUi.apiKeyPlaceholder');
  return t(field.placeholderKey);
});

const quickFieldHelper = computed(() => {
  const field = quickFieldConfig.value;
  if (!field) return t('configCenter.defaultSetting');
  if (field.key.endsWith('_API_KEY')) {
    return String(quickFieldValue.value || '') === '********'
      ? t('configCenter.providerUi.keySavedHint')
      : '';
  }
  return t(field.helperKey);
});

const quickFieldValue = computed<string>({
  get() {
    const field = quickFieldConfig.value;
    if (!field?.key) return '';
    const target = currentItems.value.find((item) => item.key === field.key);
    return String(target?.value || '');
  },
  set(value) {
    const field = quickFieldConfig.value;
    if (!field?.key) return;
    const target = currentItems.value.find((item) => item.key === field.key);
    if (target) {
      target.value = value;
      target.error = '';
    }
  }
});

async function clearQuickField() {
  if (quickFieldDisabled.value || !selectedCategoryId.value) return;
  const field = quickFieldConfig.value;
  const keyName = field?.key || '';
  if (!keyName) return;

  quickFieldValue.value = '';

  try {
    appStore.setLoading(true);
    await deleteConfigItem(keyName);
    const provider = quickSelectedProvider.value as ProviderKey;
    showNotice('success', t('common.feedback.success'), t('config.message.apiKeyCleared', { provider }));
    await loadCategoryItems(selectedCategoryId.value);
  } catch (error) {
    showApiError(error, t('config.message.apiKeyClearFailed'));
  } finally {
    appStore.setLoading(false);
  }
}

async function resetQuickSection() {
  if (!selectedCategoryId.value) return;
  await loadCategoryItems(selectedCategoryId.value);
}

const tokenSessionGuardItems = computed(() =>
  currentItems.value
    .filter((item) => isConfigSessionTokenGuardKey(item.key))
    .sort(
      (left, right) =>
        CONFIG_SESSION_TOKEN_GUARD_KEYS.indexOf(left.key as (typeof CONFIG_SESSION_TOKEN_GUARD_KEYS)[number]) -
        CONFIG_SESSION_TOKEN_GUARD_KEYS.indexOf(right.key as (typeof CONFIG_SESSION_TOKEN_GUARD_KEYS)[number])
    )
);

const aiModelTokenBudget = computed(() => buildAiModelTokenBudgetSections(currentItems.value));

function generationMaxTokensRelatedItems() {
  const items = listLegacyProviderGenerationTokenItems(currentItems.value);
  const unified = currentItems.value.find((item) => item.key === CONFIG_GENERATION_MAX_TOKENS_KEY);
  return unified ? [unified, ...items.filter((item) => item.key !== unified.key)] : items;
}

const generationMaxTokensValue = computed({
  get() {
    const related = generationMaxTokensRelatedItems();
    if (!related.length) return null;
    const unified = related.find((item) => item.key === CONFIG_GENERATION_MAX_TOKENS_KEY);
    if (unified) return unified.value;
    return related[0].value;
  },
  set(value) {
    syncGenerationMaxTokensToLegacyKeys(currentItems.value, value);
  }
});

const generationMaxTokensError = computed(
  () => generationMaxTokensRelatedItems().map((item) => item.error).find(Boolean) ?? ''
);

const generationMaxTokensDirty = computed(() =>
  generationMaxTokensRelatedItems().some((item) => isItemDirty(item))
);

async function handleGenerationMaxTokensBlur() {
  syncGenerationMaxTokensToLegacyKeys(currentItems.value, generationMaxTokensValue.value);
  await Promise.all(generationMaxTokensRelatedItems().map((item) => handleValidateItem(item)));
}

const groupedConfigSections = computed(() => {
  const sharedItems: ConfigItem[] = [];
  const groupedItems = new Map<ProviderKey, ConfigItem[]>(providerKeys.map((key) => [key, [] as ConfigItem[]]));

  const itemsForGrouping = filterItemsForCategoryGrouping(
    selectedCategoryId.value,
    currentItems.value
  );

  itemsForGrouping.forEach((item) => {
    const providerKey = resolveProviderKey(item);
    if (providerKey === 'shared') {
      sharedItems.push(item);
      return;
    }

    groupedItems.get(providerKey)?.push(item);
  });

  const providers = providerKeys
    .map((key): ConfigSection => ({
      key,
      title: translateKey(`configCenter.provider.${key}`, key),
      items: groupedItems.get(key) || [],
      active: defaultProviderKey.value === key
    }))
    .filter((section) => section.items.length > 0);

  return {
    shared: {
      key: 'shared' as const,
      title: t('config.section.shared'),
      items: sharedItems,
      active: false
    },
    providers
  };
});

const activityMessage = computed(() => {
  if (saving.value) return t('config.actions.saving');
  if (exporting.value) return t('config.actions.exporting');
  if (validationPendingCount.value > 0) return t('config.state.validationRunning');
  return t('common.actions.loading');
});

watch(
  () => appStore.locale,
  (nextLocale) => {
    if (nextLocale && nextLocale !== locale.value) {
      locale.value = nextLocale;
    }
  },
  { immediate: true }
);

function showNotice(type: NoticeType, title: string, message: string) {
  notifyPageNotice(type, message, { title });
}

function showApiError(error: unknown, fallback: string, altFallback?: string) {
  const message = getUserFacingErrorMessage(error, altFallback ?? fallback);
  showNotice('danger', t('common.status.error'), message || altFallback || fallback);
}

function resetImportInput() {
  if (importInput.value) {
    importInput.value.value = '';
  }
}

function humanizeKey(key: string) {
  return key
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (part) => part.toUpperCase());
}

function translateKey(path: string, fallback: string) {
  const translated = t(path) as string;
  return translated === path ? fallback : translated;
}

function normalizeConfigDisplayText(text: string) {
  if (!text) return text;
  const trimmed = text.trim();
  // 仅当整段就是 settings 引用占位时才替换，避免把「…与 settings.py 一致」类说明整块变成「默认设置」
  if (/^settings\.py$/i.test(trimmed)) {
    return t('configCenter.defaultSetting') as string;
  }
  return text;
}

function resolveCategoryLabel(category: ConfigCategory) {
  return translateKey(category.name_key || `configCenter.category.${category.id}`, category.name || humanizeKey(category.id));
}

function resolveCategoryDescription(category: ConfigCategory) {
  return translateKey(
    category.description_key || `configCenter.categoryDescription.${category.id}`,
    category.description || ''
  );
}

function resolveItemLabel(item: ConfigItem) {
  const resolved = translateKey(item.label_key || `configCenter.itemLabel.${item.key}`, item.description || humanizeKey(item.key));
  return normalizeConfigDisplayText(resolved);
}

function resolveItemValueTypeLabel(item: ConfigItem) {
  if (item.key === 'CONTENT_DEDUP_WEIGHTS' || item.inputKind === 'dedup_weights') {
    return t('config.form.dedupWeights.valueType');
  }
  if (item.value_type) {
    return translateKey(`enums.config.valueType.${item.value_type}`, item.value_type);
  }
  return translateKey(`enums.config.fieldKind.${item.inputKind}`, item.inputKind);
}

function resolveItemHelper(item: ConfigItem) {
  const pieces: string[] = [];
  const description = normalizeConfigDisplayText(
    translateKey(item.description_key || `configCenter.itemDescription.${item.key}`, item.description || '')
  );
  if (description) {
    pieces.push(`${t('config.form.description')}: ${description}`);
  }
  pieces.push(`${t('config.form.valueType')}: ${resolveItemValueTypeLabel(item)}`);
  if (item.updated_at) {
    pieces.push(`${t('config.form.updatedAt')}: ${formatDateTime(item.updated_at)}`);
  }
  return pieces.join(' · ');
}

function resolveItemPlaceholder(item: ConfigItem) {
  switch (item.inputKind) {
    case 'password':
      return t('config.form.passwordPlaceholder');
    case 'number':
      return t('config.form.numberPlaceholder');
    case 'textarea':
      return t('config.form.textareaPlaceholder');
    case 'select':
      return t('config.form.selectPlaceholder');
    default:
      return t('config.form.textPlaceholder');
  }
}

function resolveProviderKey(item: ConfigItem): ProviderKey | 'shared' {
  const text = `${item.key} ${item.description || ''}`.toUpperCase();

  if (text.includes('OPENAI') || /GPT[\-_ ]?5/.test(text)) return 'OPENAI';
  if (text.includes('DEEPSEEK')) return 'DEEPSEEK';
  if (text.includes('OLLAMA')) return 'OLLAMA';
  if (text.includes('GEMINI')) return 'GEMINI';
  if (text.includes('QWEN')) return 'QWEN';
  if (text.includes('ANTHROPIC') || text.includes('CLAUDE')) return 'ANTHROPIC';

  return 'shared';
}

function getProviderOptions(): ConfigOption[] {
  const values = ['OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN', 'ANTHROPIC'];
  return values.map((value) => ({
    value,
    label: translateKey(`configCenter.provider.${value}`, value)
  }));
}

function resolveItemOptions(item: ConfigItem): ConfigOption[] | undefined {
  if (item.options && item.options.length > 0) {
    return item.options.map((option) => {
      const optionValue = String(option.value).toUpperCase();
      return {
        ...option,
        label: translateKey(`configCenter.provider.${optionValue}`, option.label)
      };
    });
  }

  if (item.key === 'DEFAULT_COMPANY' || item.value_type === 'provider') {
    return getProviderOptions();
  }

  if (item.inputKind === 'select') {
    return [];
  }

  return undefined;
}

function isItemRequired(item: ConfigItem) {
  return Boolean(item.raw && (item.raw.is_required === true || item.raw.required === true));
}

function serializeValueForComparison(item: ConfigItem) {
  if (item.value === null || item.value === undefined) {
    return '';
  }
  if (item.inputKind === 'boolean') {
    return item.value ? 'true' : 'false';
  }
  return String(item.value);
}

function isItemDirty(item: ConfigItem) {
  const snapshot = baselineSnapshot.value[item.key];
  return snapshot !== serializeValueForComparison(item);
}

function ensureAiProviderDrafts(items: ConfigItem[]) {
  const company = String(items.find((item) => item.key === 'DEFAULT_COMPANY')?.value || '').toUpperCase();
  providerKeys.forEach((provider) => {
    const secretKey = providerQuickFieldMap[provider]?.key;
    if (secretKey?.endsWith('_API_KEY') && !items.some((item) => item.key === secretKey)) {
      items.push({
        key: secretKey,
        value: '',
        value_type: 'string',
        category: 'ai_model',
        is_sensitive: true,
        configured: false,
        inputKind: 'password',
        dirty: false,
        touched: false,
        raw: { key: secretKey, value_type: 'string', category: 'ai_model', is_sensitive: true }
      });
    }
    const enableKey = providerEnableKeyMap[provider];
    if (!items.some((item) => item.key === enableKey)) {
      items.push({
        key: enableKey,
        value: provider === company,
        value_type: 'bool',
        category: 'ai_model',
        is_sensitive: false,
        inputKind: 'boolean',
        dirty: false,
        touched: false,
        raw: { key: enableKey, value_type: 'bool', category: 'ai_model' }
      });
    }
  });
}

function resetDirtySnapshot(items: ConfigItem[]) {
  baselineSnapshot.value = items.reduce<Record<string, string>>((acc, item) => {
    acc[item.key] = serializeValueForComparison(item);
    return acc;
  }, {});
}

function normalizeSubmitValue(item: ConfigItem) {
  if (item.inputKind === 'boolean') {
    return Boolean(item.value);
  }

  if (item.inputKind === 'number') {
    if (item.value === null || item.value === undefined || item.value === '') return null;
    if (typeof item.value === 'number') return item.value;
    const next = Number(item.value);
    return Number.isNaN(next) ? item.value : next;
  }

  return item.value;
}

async function loadCategories({ preserveSelection = false } = {}) {
  categoriesLoading.value = true;
  categoriesError.value = '';
  appStore.setLoading(true);

  try {
    const list = await getCategories();
    categories.value = list;

    if (!categories.value.length) {
      selectedCategoryId.value = '';
      currentItems.value = [];
      baselineSnapshot.value = {};
      return;
    }

    const selectionValid =
      isConfigAuditCategoryId(selectedCategoryId.value) ||
      categories.value.some((item) => item.id === selectedCategoryId.value);

    if (!selectedCategoryId.value || !selectionValid || !preserveSelection) {
      selectedCategoryId.value = categories.value[0]?.id ?? CONFIG_AUDIT_CATEGORY_ID;
    }

    await loadCategoryItems(selectedCategoryId.value);
  } catch (error) {
    categories.value = [];
    selectedCategoryId.value = '';
    currentItems.value = [];
    baselineSnapshot.value = {};
    categoriesError.value = getUserFacingErrorMessage(error, t('config.message.loadFailed'));
    showApiError(error, t('config.message.loadFailed'), t('validation.loadFailed'));
  } finally {
    categoriesLoading.value = false;
    appStore.setLoading(false);
  }
}

let loadCategoryRequestSeq = 0;
let categoryLoadInFlight = false;

async function loadCategoryItems(categoryId: string) {
  // 先点 A 再点 B 时，A 的慢响应不能覆盖 B 的配置项，否则保存会把 A 的值提交到 B
  const requestSeq = ++loadCategoryRequestSeq;
  const isStale = () => requestSeq !== loadCategoryRequestSeq || categoryId !== selectedCategoryId.value;
  // 切到审计日志等不走请求的分类时，前一个还没返回的请求不再负责清 loading
  categoryLoadInFlight = false;
  if (!categoryId) {
    currentItems.value = [];
    baselineSnapshot.value = {};
    return;
  }

  if (isConfigAuditCategoryId(categoryId)) {
    currentItems.value = [];
    baselineSnapshot.value = {};
    itemsError.value = '';
    await loadAuditLogs();
    return;
  }

  itemsLoading.value = true;
  itemsError.value = '';
  appStore.setLoading(true);
  categoryLoadInFlight = true;

  try {
    const response = await getCategoryConfig(categoryId);
    if (isStale()) return;
    currentItems.value = response;
    if (categoryId === 'ai_model') {
      ensureAiProviderDrafts(currentItems.value);
      applySingleActiveProvider(currentItems.value);
    }
    resetDirtySnapshot(currentItems.value);
    currentItems.value.forEach((item) => {
      item.error = '';
    });
    if (categoryId === 'ai_model') {
      syncGenerationMaxTokensToLegacyKeys(currentItems.value, generationMaxTokensValue.value);
    }
  } catch (error) {
    if (isStale()) return;
    currentItems.value = [];
    baselineSnapshot.value = {};
    itemsError.value = getUserFacingErrorMessage(error, t('config.message.loadFailed'));
    showApiError(error, t('config.message.loadFailed'), t('validation.loadFailed'));
  } finally {
    if (requestSeq === loadCategoryRequestSeq || !categoryLoadInFlight) {
      itemsLoading.value = false;
      appStore.setLoading(false);
    }
    if (requestSeq === loadCategoryRequestSeq) categoryLoadInFlight = false;
  }
}

async function handleSelectCategory(categoryId: string) {
  if (categoryId === selectedCategoryId.value) return;

  if (dirtyCount.value > 0) {
    openUnsavedDiscardDialog({ kind: 'selectCategory', categoryId });
    return;
  }

  selectedCategoryId.value = categoryId;
  await loadCategoryItems(categoryId);
}

async function handleReloadCategories() {
  if (dirtyCount.value > 0) {
    openUnsavedDiscardDialog({ kind: 'reloadCategories' });
    return;
  }
  await loadCategories({ preserveSelection: true });
}

async function handleReloadCurrentCategory() {
  if (!selectedCategoryId.value) return;
  if (isConfigAuditCategoryId(selectedCategoryId.value)) {
    await loadAuditLogs();
    return;
  }
  if (dirtyCount.value > 0) {
    openUnsavedDiscardDialog({ kind: 'reloadCurrentCategory' });
    return;
  }
  await loadCategoryItems(selectedCategoryId.value);
}

async function handleValidateItem(item: ConfigItem) {
  validationPending[item.key] = true;
  item.touched = true;

  try {
    // Sensitive values (e.g. API keys) use local checks first to reduce unnecessary network exposure.
    if (item.is_sensitive) {
      const value = String(item.value ?? '').trim();
      if (isItemRequired(item) && !value) {
        item.error = t('validation.required');
      } else {
        item.error = '';
      }
      return;
    }

    // Boolean switches are deterministic and do not need backend validation calls.
    if (item.inputKind === 'boolean') {
      item.error = '';
      return;
    }

    const result = await validateConfig(item.key, normalizeSubmitValue(item));
    if (result.valid) {
      item.error = '';
    } else {
      item.error = result.message || t('validation.invalidValue');
    }
  } catch (error) {
    item.error = getUserFacingErrorMessage(error, t('validation.validationFailed'));
  } finally {
    validationPending[item.key] = false;
  }
}

async function handleSave() {
  if (!selectedCategoryId.value || isConfigAuditCategoryId(selectedCategoryId.value)) return;

  if (!currentItems.value.length) {
    showNotice('info', t('common.feedback.info'), t('config.message.noChangesToSave'));
    return;
  }

  saving.value = true;
  appStore.setLoading(true);

  try {
    if (selectedCategoryId.value === 'ai_model') {
      syncGenerationMaxTokensToLegacyKeys(currentItems.value, generationMaxTokensValue.value);
    }
    const submitItems = currentItems.value.filter((item) => isItemDirty(item));
    if (!submitItems.length) {
      showNotice('info', t('common.feedback.info'), t('config.message.noChangesToSave'));
      return;
    }

    await Promise.allSettled(submitItems.map((item) => handleValidateItem(item)));

    const payload = submitItems.map((item) => ({
      ...item,
      value: normalizeSubmitValue(item)
    }));

    const result = await saveConfig(selectedCategoryId.value, payload);
    const failedConfigs = result.failed_configs || [];

    if (failedConfigs.length > 0) {
      failedConfigs.forEach((failed) => {
        const matched = currentItems.value.find((item) => item.key === failed.key);
        if (matched) {
          matched.error = failed.error;
        }
      });
      showNotice(
        'warning',
        t('common.feedback.warning'),
        `${t('config.message.savedWithWarnings')} · ${t('config.message.validationFailed')}`
      );
    } else {
      showNotice(
        'success',
        t('common.feedback.success'),
        `${t('config.message.saved')} · ${t('config.message.validationPassed')}`
      );
    }

    await loadCategoryItems(selectedCategoryId.value);
    await refreshAppFeatureFlags();
  } catch (error) {
    showNotice(
      'danger',
      t('config.message.saveFailed'),
      getUserFacingErrorMessage(error, t('validation.saveFailed'))
    );
  } finally {
    saving.value = false;
    appStore.setLoading(false);
  }
}

async function handleExport() {
  exporting.value = true;

  try {
    const result = await exportConfig('json');
    triggerTextDownload(result.content, result.filename || 'config_export.json');

    showNotice('success', t('common.feedback.success'), t('config.message.exportReady'));
  } catch (error) {
    showApiError(error, t('config.message.exportFailed'), t('validation.exportFailed'));
  } finally {
    exporting.value = false;
  }
}

function handleImportClick() {
  if (dirtyCount.value > 0) {
    openUnsavedDiscardDialog({ kind: 'importClick' });
    return;
  }
  importInput.value?.click();
}

async function handleImportFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  resetImportInput();

  if (!file) return;

  importing.value = true;
  appStore.setLoading(true);

  try {
    const result = await importConfig(file);
    showNotice('success', t('common.feedback.success'), t('config.message.importReady', { count: result.imported_count ?? 0 }));
    await loadCategories({ preserveSelection: true });
  } catch (error) {
    showApiError(error, t('config.message.importFailed'));
  } finally {
    importing.value = false;
    appStore.setLoading(false);
  }
}

const auditLogs = ref<ConfigAuditLogRecord[]>([]);
const auditLogsLoading = ref(false);
const auditLogsError = ref('');

function formatAuditLogTime(value: unknown) {
  return formatDateTime(value ? String(value) : null, locale.value);
}

async function loadAuditLogs() {
  auditLogsLoading.value = true;
  auditLogsError.value = '';
  try {
    auditLogs.value = await getConfigAuditLogs({ limit: 50, offset: 0 });
  } catch (error) {
    auditLogs.value = [];
    auditLogsError.value = getUserFacingErrorMessage(error, t('config.audit.loading'));
  } finally {
    auditLogsLoading.value = false;
  }
}

onMounted(async () => {
  const routeCategory = typeof route.query.category === 'string' ? route.query.category : '';
  if (routeCategory) {
    selectedCategoryId.value = routeCategory;
  }
  await loadCategories({ preserveSelection: Boolean(routeCategory) });
});

</script>
