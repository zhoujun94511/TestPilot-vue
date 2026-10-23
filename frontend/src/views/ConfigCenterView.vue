<template>
  <section class="tp-container-fluid tp-py-3 tp-page tp-page-shell tp-config-page">
    <div
      v-if="banner && banner.message"
      class="tp-risk-block tp-mb-3"
      :class="bannerClass"
    >
      <div class="tp-flex-grow-1">
        <div class="tp-risk-block__title">{{ banner.title }}</div>
        <div class="tp-risk-block__text">{{ banner.message }}</div>
      </div>
      <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="clearBanner">
        {{ t('common.actions.close') }}
      </TpButton>
    </div>

    <ActionBar :title="t('config.page.title')" :subtitle="t('config.page.subtitle')">
      <template #actions>
        <TpButton variant="secondary" :loading="categoriesLoading" @click="handleReloadCategories">
          {{ t('common.actions.refresh') }}
        </TpButton>
        <TpButton variant="ghost" :loading="exporting" @click="handleExport">
          {{ exporting ? t('config.actions.exporting') : t('config.actions.export') }}
        </TpButton>
        <TpButton variant="ghost" :loading="importing" @click="handleImportClick">
          {{ importing ? t('config.actions.importing') : t('config.actions.import') }}
        </TpButton>
        <TpButton :loading="saving" :disabled="saving || !selectedCategoryId || currentItems.length === 0" @click="handleSave">
          {{ saving ? t('config.actions.saving') : t('config.actions.save') }}
        </TpButton>
      </template>
    </ActionBar>

    <input
      ref="importInput"
      class="tp-d-none"
      type="file"
      accept=".json,.yaml,.yml"
      @change="handleImportFileChange"
    />

    <div class="tp-row tp-g-3 tp-align-stretch">
      <aside class="tp-col-12 tp-col-xl-3">
        <div class="tp-surface tp-config-sidebar tp-p-3 tp-h-100">
          <div class="tp-flex tp-justify-between tp-align-center tp-mb-3">
            <div class="tp-card__title">{{ t('config.category.title') }}</div>
            <TpTag v-if="selectedCategoryLabel" variant="neutral">
              {{ t('config.category.current') }}
            </TpTag>
          </div>

          <BaseState
            v-if="categoriesLoading"
            variant="loading"
            :title="t('config.category.loading')"
          />
          <BaseState
            v-else-if="categoriesError"
            variant="error"
            :title="t('common.status.error')"
            :message="categoriesError"
            :retry-text="t('common.actions.retry')"
            @retry="handleReloadCategories"
          />
          <BaseState
            v-else-if="!sortedCategories.length"
            variant="empty"
            :title="t('config.category.empty')"
          />
          <div v-else class="tp-config-list">
            <button
              v-for="category in sortedCategories"
              :key="category.id"
              type="button"
              class="tp-nav-item tp-config-category-item"
              :class="{ 'tp-config-category-item--active': category.id === selectedCategoryId }"
              @click="handleSelectCategory(category.id)"
            >
              <div class="tp-text-start">
                <div class="tp-data-title">{{ resolveCategoryLabel(category) }}</div>
                <div class="tp-data-subtitle">{{ resolveCategoryDescription(category) }}</div>
              </div>
              <TpTag v-if="category.id === selectedCategoryId" variant="neutral">
                {{ t('config.category.current') }}
              </TpTag>
            </button>
          </div>
        </div>
      </aside>

      <section class="tp-col-12 tp-col-xl-9">
        <div class="tp-surface tp-p-3 tp-p-lg-4 tp-h-100">
          <BaseState
            v-if="itemsLoading"
            variant="loading"
            :title="t('config.panel.loading')"
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
                <div v-if="selectedCategoryId === 'ai_model'" class="tp-config-overview">
                  <div class="tp-config-toolbar tp-mb-3">
                    <div class="tp-flex tp-flex-column tp-flex-lg-row tp-justify-between tp-align-start tp-gap-2">
                      <div>
                        <div class="tp-card__title">{{ t('configCenter.providerUi.title') }}</div>
                        <div class="tp-config-meta">{{ t('configCenter.providerUi.subtitle') }}</div>
                      </div>

                      <div class="tp-config-toolbar__meta tp-text-lg-end">
                        <div class="tp-small tp-config-toolbar__hint">{{ t('config.panel.hint') }}</div>
                        <div class="tp-small tp-mt-1 tp-config-toolbar__status">
                          <span v-if="dirtyCount > 0">{{ t('config.state.pendingChanges', { count: dirtyCount }) }}</span>
                          <span v-else>{{ t('config.state.noChanges') }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="tp-config-section tp-config-section--provider tp-config-section--active">
                    <div class="tp-config-section__header">
                      <div>
                        <div class="tp-config-section__title">{{ t('configCenter.defaultSetting') }}</div>
                        <div class="tp-config-section__subtitle">{{ t('configCenter.providerUi.saveHint') }}</div>
                      </div>
                      <div class="tp-flex tp-align-center tp-gap-2">
                        <TpButton
                          variant="secondary"
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
                        <TpTag variant="primary">{{ t('config.section.active') }}</TpTag>
                      </div>
                    </div>

                    <div class="tp-row tp-g-3">
                      <div class="tp-col-12 tp-col-lg-4">
                        <label class="tp-form-label">{{ t('configCenter.itemLabel.DEFAULT_COMPANY') }}</label>
                        <select v-model="quickSelectedProvider" class="tp-select">
                          <option v-for="option in getProviderOptions()" :key="option.value" :value="option.value">
                            {{ option.label }}
                          </option>
                        </select>
                      </div>

                      <div class="tp-col-12 tp-col-lg-8">
                        <label class="tp-form-label">{{ quickFieldLabel }}</label>
                        <input
                          v-model="quickFieldValue"
                          class="tp-input"
                          :type="quickFieldInputType"
                          :disabled="quickFieldDisabled"
                          :placeholder="quickFieldPlaceholder"
                        />
                        <small class="tp-help-text tp-d-block tp-mt-2">
                          {{ quickFieldHelper }}
                        </small>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="tp-config-overview">
                  <div class="tp-config-toolbar tp-mb-3">
                    <div class="tp-flex tp-flex-column tp-flex-lg-row tp-justify-between tp-align-start tp-gap-2">
                      <div>
                        <div class="tp-card__title">{{ selectedCategoryLabel }}</div>
                        <div class="tp-config-meta">{{ selectedCategoryDescription }}</div>
                      </div>

                      <div class="tp-config-toolbar__meta tp-text-lg-end">
                        <div class="tp-small tp-config-toolbar__hint">{{ t('config.panel.hint') }}</div>
                        <div class="tp-small tp-mt-1 tp-config-toolbar__status">
                          <span v-if="dirtyCount > 0">{{ t('config.state.pendingChanges', { count: dirtyCount }) }}</span>
                          <span v-else>{{ t('config.state.noChanges') }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="tp-config-overview__head">
                    <div>
                      <div class="tp-config-overview__eyebrow">{{ t('config.section.providers') }}</div>
                      <div class="tp-config-meta">
                        {{
                          currentDefaultProviderLabel
                            ? t('config.section.providerHint', { provider: currentDefaultProviderLabel })
                            : t('config.section.sharedScopeHint')
                        }}
                      </div>
                    </div>
                    <div class="tp-config-overview__metrics">
                      <TpTag variant="neutral">
                        {{ t('config.section.shared') }}
                        <span class="tp-config-overview__count">{{ groupedConfigSections.shared.items.length }}</span>
                      </TpTag>
                      <TpTag variant="ai">
                        {{ t('config.section.providers') }}
                        <span class="tp-config-overview__count">{{ groupedConfigSections.providers.length }}</span>
                      </TpTag>
                    </div>
                  </div>

                  <div
                    v-if="groupedConfigSections.shared.items.length"
                    class="tp-config-section tp-config-section--shared"
                  >
                    <div class="tp-config-section__header">
                      <div>
                        <div class="tp-config-section__title">{{ t('config.section.shared') }}</div>
                        <div class="tp-config-section__subtitle">{{ t('config.section.sharedHint') }}</div>
                      </div>
                    </div>
                    <div class="tp-config-form-stack">
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
                  </div>

                  <div v-if="groupedConfigSections.providers.length" class="tp-config-provider-grid">
                    <section
                      v-for="section in groupedConfigSections.providers"
                      :key="section.key"
                      class="tp-config-section tp-config-section--provider"
                      :class="[`tp-config-section--${section.key.toLowerCase()}`, { 'tp-config-section--active': section.active }]"
                    >
                      <div class="tp-config-section__header">
                        <div>
                          <div class="tp-config-section__title">{{ section.title }}</div>
                          <div class="tp-config-section__subtitle">{{ section.subtitle }}</div>
                        </div>
                        <div class="tp-config-section__meta">
                          <TpTag v-if="section.active" variant="primary">{{ t('config.section.active') }}</TpTag>
                          <TpTag variant="neutral">{{ section.items.length }}</TpTag>
                        </div>
                      </div>

                      <div class="tp-config-form-stack">
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
                    </section>
                  </div>
                </div>
              </template>

              <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-center tp-gap-2 tp-mt-4 tp-pt-3">
                <div class="tp-config-meta">
                  <span v-if="saving || exporting || validationPendingCount > 0">
                    {{ activityMessage }}
                  </span>
                  <span v-else>{{ dirtyCount > 0 ? t('config.state.pendingChanges', { count: dirtyCount }) : t('config.state.noChanges') }}</span>
                </div>

                <div class="tp-flex tp-flex-wrap tp-gap-2">
                  <TpButton variant="secondary" :disabled="saving" @click="handleReloadCurrentCategory">
                    {{ t('config.actions.reload') }}
                  </TpButton>
                  <TpButton :loading="saving" :disabled="saving || !currentItems.length" @click="handleSave">
                    {{ saving ? t('config.actions.saving') : t('config.actions.save') }}
                  </TpButton>
                </div>
              </div>
            </template>
          </template>
        </div>
      </section>
    </div>

    <section class="tp-surface tp-p-3 tp-mt-3">
      <div class="tp-flex tp-justify-between tp-align-center tp-gap-2 tp-mb-2">
        <div class="tp-card__title">{{ t('config.audit.title') }}</div>
        <TpButton variant="ghost" size="sm" :loading="auditLoading" @click="loadAuditLogs">
          {{ t('common.actions.refresh') }}
        </TpButton>
      </div>
      <div v-if="auditLoading" class="tp-small">{{ t('config.audit.loading') }}</div>
      <div v-else-if="!auditLogs.length" class="tp-small">{{ t('config.audit.empty') }}</div>
      <div v-else class="tp-grid tp-gap-2">
        <div v-for="log in auditLogs" :key="String(log.id || log.key) + String(log.created_at || '')" class="tp-small">
          <strong>{{ log.key || '-' }}</strong>
          · {{ log.action || '-' }}
          · {{ log.operator || '-' }}
          · {{ formatDateTime(String(log.created_at || '')) }}
        </div>
      </div>
    </section>

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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import ActionBar from '@/components/common/ActionBar.vue';
import BaseState from '@/components/common/BaseState.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import ConfigFormItem from '@/components/common/ConfigFormItem.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useAppStore } from '@/stores';
import {
  deleteConfigItem,
  exportConfig,
  getCategories,
  getCategoryConfig,
  getConfigAuditLogs,
  importConfig,
  saveConfig,
  validateConfig,
  type ConfigAuditLogRecord,
  type ConfigCategory,
  type ConfigItem,
  type ConfigOption
} from '@/api/config';
import { ApiError } from '@/api/http';

type NoticeType = 'success' | 'danger' | 'warning' | 'info';

interface NoticeState {
  type: NoticeType;
  title: string;
  message: string;
}

const { t, locale } = useI18n();
const route = useRoute();
const appStore = useAppStore();

const categories = ref<ConfigCategory[]>([]);
const auditLogs = ref<ConfigAuditLogRecord[]>([]);
const auditLoading = ref(false);
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
const banner = ref<NoticeState | null>(null);
const bannerTimer = ref<number | null>(null);
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

const selectedCategory = computed(() => categories.value.find((item) => item.id === selectedCategoryId.value) || null);
const selectedCategoryLabel = computed(() => (selectedCategory.value ? resolveCategoryLabel(selectedCategory.value) : ''));
const selectedCategoryDescription = computed(() => (selectedCategory.value ? resolveCategoryDescription(selectedCategory.value) : ''));
const dirtyCount = computed(() => currentItems.value.filter((item) => isItemDirty(item)).length);
const validationPendingCount = computed(() => Object.values(validationPending).filter(Boolean).length);
const providerKeys = ['OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN'] as const;
type ProviderKey = (typeof providerKeys)[number];

interface ConfigSection {
  key: ProviderKey | 'shared';
  title: string;
  subtitle: string;
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
  QWEN: 'ENABLE_QWEN'
};

const quickSelectedProvider = computed<string>({
  get() {
    return defaultProviderKey.value || 'OPENAI';
  },
  set(value) {
    const target = currentItems.value.find((item) => item.key === 'DEFAULT_COMPANY');
    if (target) {
      target.value = String(value || 'OPENAI').toUpperCase();
      target.error = '';
    }
    syncAiModelProviderFlags();
  }
});

const quickFieldConfig = computed(() => {
  const provider = quickSelectedProvider.value as ProviderKey;
  return providerQuickFieldMap[provider];
});

const quickFieldDisabled = computed(() => {
  const field = quickFieldConfig.value;
  if (!field?.key) return true;
  return !currentItems.value.some((item) => item.key === field.key);
});

const quickFieldLabel = computed(() => {
  const field = quickFieldConfig.value;
  if (!field) return t('configCenter.providerUi.apiKey');
  return t(field.labelKey);
});

const quickFieldInputType = computed(() => quickFieldConfig.value?.inputType || 'text');

const quickFieldPlaceholder = computed(() => {
  if (quickFieldDisabled.value) return t('configCenter.providerUi.noApiKeyNeeded');
  const field = quickFieldConfig.value;
  if (!field) return t('configCenter.providerUi.apiKeyPlaceholder');
  return t(field.placeholderKey);
});

const quickFieldHelper = computed(() => {
  if (quickFieldDisabled.value) return t('configCenter.providerUi.noApiKeyNeeded');
  const field = quickFieldConfig.value;
  if (!field) return t('configCenter.defaultSetting');
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

const groupedConfigSections = computed(() => {
  const sharedItems: ConfigItem[] = [];
  const groupedItems = new Map<ProviderKey, ConfigItem[]>(providerKeys.map((key) => [key, [] as ConfigItem[]]));

  currentItems.value.forEach((item) => {
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
      subtitle: t('config.section.providerHint', { provider: translateKey(`configCenter.provider.${key}`, key) }),
      items: groupedItems.get(key) || [],
      active: defaultProviderKey.value === key
    }))
    .filter((section) => section.items.length > 0);

  return {
    shared: {
      key: 'shared' as const,
      title: t('config.section.shared'),
      subtitle: t('config.section.sharedHint'),
      items: sharedItems,
      active: false
    },
    providers
  };
});

const bannerClass = computed(() => {
  const type = banner.value?.type || 'info';
  return {
    'tp-risk-block--info': type === 'info',
    'tp-risk-block--danger': type === 'danger',
    'tp-risk-block--warning': type === 'warning',
    'tp-risk-block--success': type === 'success'
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

function clearBanner() {
  banner.value = null;
  if (bannerTimer.value) {
    window.clearTimeout(bannerTimer.value);
    bannerTimer.value = null;
  }
}

function showNotice(type: NoticeType, title: string, message: string) {
  banner.value = { type, title, message };
  if (bannerTimer.value) {
    window.clearTimeout(bannerTimer.value);
  }
  bannerTimer.value = window.setTimeout(() => {
    banner.value = null;
    bannerTimer.value = null;
  }, 3000);
}

function showApiError(error: unknown, fallback: string) {
  const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : fallback;
  showNotice('danger', t('common.status.error'), message || fallback);
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
    pieces.push(description);
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

  return 'shared';
}

function getProviderOptions(): ConfigOption[] {
  const values = ['OPENAI', 'DEEPSEEK', 'OLLAMA', 'GEMINI', 'QWEN'];
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

function syncAiModelProviderFlags() {
  if (selectedCategoryId.value !== 'ai_model') return;
  const selected = String(quickSelectedProvider.value || '').toUpperCase() as ProviderKey;
  if (!providerKeys.includes(selected)) return;

  providerKeys.forEach((provider) => {
    const enableKey = providerEnableKeyMap[provider];
    const target = currentItems.value.find((item) => item.key === enableKey);
    if (!target) return;
    target.value = provider === selected;
    target.error = '';
  });
}

function buildAiModelSubmitItems(items: ConfigItem[]) {
  if (selectedCategoryId.value !== 'ai_model') return items;
  const selected = String(quickSelectedProvider.value || '').toUpperCase() as ProviderKey;
  if (!providerKeys.includes(selected)) return items;

  const nextItems = [...items];
  providerKeys.forEach((provider) => {
    const enableKey = providerEnableKeyMap[provider];
    const expectedValue = provider === selected;
    const existing = currentItems.value.find((item) => item.key === enableKey);
    if (existing) {
      existing.value = expectedValue;
      if (isItemDirty(existing) && !nextItems.some((item) => item.key === enableKey)) {
        nextItems.push(existing);
      }
      return;
    }

    nextItems.push({
      key: enableKey,
      value: expectedValue,
      value_type: 'bool',
      category: 'ai_model',
      description: `Enable ${provider} provider`,
      is_sensitive: false,
      inputKind: 'boolean',
      dirty: true,
      touched: true,
      raw: { key: enableKey, value_type: 'bool', category: 'ai_model' }
    });
  });

  return nextItems;
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

    if (!selectedCategoryId.value || !categories.value.some((item) => item.id === selectedCategoryId.value) || !preserveSelection) {
      selectedCategoryId.value = categories.value[0].id;
    }

    await loadCategoryItems(selectedCategoryId.value);
  } catch (error) {
    categoriesError.value = error instanceof Error ? error.message : t('config.message.loadFailed');
    showApiError(error, t('config.message.loadFailed'));
  } finally {
    categoriesLoading.value = false;
    appStore.setLoading(false);
  }
}

async function loadCategoryItems(categoryId: string) {
  if (!categoryId) {
    currentItems.value = [];
    baselineSnapshot.value = {};
    return;
  }

  itemsLoading.value = true;
  itemsError.value = '';
  appStore.setLoading(true);

  try {
    const response = await getCategoryConfig(categoryId);
    currentItems.value = response;
    resetDirtySnapshot(currentItems.value);
    currentItems.value.forEach((item) => {
      item.error = '';
    });
  } catch (error) {
    currentItems.value = [];
    baselineSnapshot.value = {};
    itemsError.value = error instanceof Error ? error.message : t('config.message.loadFailed');
    showApiError(error, t('config.message.loadFailed'));
  } finally {
    itemsLoading.value = false;
    appStore.setLoading(false);
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
    item.error = error instanceof Error ? error.message : t('validation.validationFailed');
  } finally {
    validationPending[item.key] = false;
  }
}

async function handleSave() {
  if (!selectedCategoryId.value) return;

  if (!currentItems.value.length) {
    showNotice('info', t('common.feedback.info'), t('config.message.noChangesToSave'));
    return;
  }

  saving.value = true;
  appStore.setLoading(true);

  try {
    syncAiModelProviderFlags();
    const dirtyItems = currentItems.value.filter((item) => isItemDirty(item));
    const submitItems = buildAiModelSubmitItems(dirtyItems);
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
      showNotice('warning', t('common.feedback.warning'), t('config.message.savedWithWarnings'));
    } else {
      showNotice('success', t('common.feedback.success'), t('config.message.saved'));
    }

    await loadCategoryItems(selectedCategoryId.value);
    await loadAuditLogs();
  } catch (error) {
    showApiError(error, t('config.message.saveFailed'));
  } finally {
    saving.value = false;
    appStore.setLoading(false);
  }
}

async function handleExport() {
  exporting.value = true;

  try {
    const result = await exportConfig('json');
    const blob = new Blob([result.content], {
      type: 'application/json;charset=utf-8'
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.filename || 'config_export.json';
    link.click();
    URL.revokeObjectURL(url);

    showNotice('success', t('common.feedback.success'), t('config.message.exportReady'));
  } catch (error) {
    showApiError(error, t('config.message.exportFailed'));
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

async function loadAuditLogs() {
  auditLoading.value = true;
  try {
    auditLogs.value = await getConfigAuditLogs({ limit: 8 });
  } catch {
    auditLogs.value = [];
  } finally {
    auditLoading.value = false;
  }
}

function formatDateTime(value: string) {
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(locale.value, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  } catch {
    return value;
  }
}

onMounted(async () => {
  const routeCategory = typeof route.query.category === 'string' ? route.query.category : '';
  if (routeCategory) {
    selectedCategoryId.value = routeCategory;
  }
  await loadCategories({ preserveSelection: Boolean(routeCategory) });
  await loadAuditLogs();
});

onBeforeUnmount(() => {
  if (bannerTimer.value) {
    window.clearTimeout(bannerTimer.value);
    bannerTimer.value = null;
  }
});
</script>
