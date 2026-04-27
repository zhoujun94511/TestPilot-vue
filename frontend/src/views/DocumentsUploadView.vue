<template>
  <section class="tp-documents-upload-page">
    <div v-if="notice" class="tp-risk-block tp-mb-3" :class="noticeClass">
      <div class="tp-flex tp-align-start tp-justify-between tp-gap-3">
        <div class="tp-flex-grow-1">{{ notice.message }}</div>
        <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="notice = null">
          {{ t('common.actions.close') }}
        </TpButton>
      </div>
    </div>

    <div class="tp-surface tp-p-3">
      <div class="tp-flex tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
        <div class="tp-doc-upload-head-main">
          <div class="tp-card__title">{{ t('documents.upload.title') }}</div>
          <div class="tp-card__subtitle">{{ t('documents.upload.autoAnalyzeHint') }}</div>
          <div class="tp-doc-upload-analysis-type tp-mt-2">
            <label class="tp-form-label tp-mb-1">{{ t('documents.upload.analysisType') }}</label>
            <select v-model="analysisType" class="tp-select">
              <option v-for="option in analysisTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <BaseUpload
        v-model="selectedFile"
        :label="t('documents.upload.file')"
        :choose-text="t('common.actions.chooseFile')"
        :submit-text="t('documents.actions.upload')"
        :loading-text="t('documents.actions.uploading')"
        :hint="t('documents.upload.fileHint')"
        :empty-text="t('documents.upload.empty')"
        :clear-text="t('common.actions.cancel')"
        accept=".txt,.csv,.docx,.pdf,.json,.md,.xlsx,.yml,.yaml"
        :loading="uploadLoading"
        @submit="handleUpload"
      >
        <template #after-filename>
          <label
            class="tp-doc-switch tp-mt-2 tp-doc-upload-auto-toggle"
            :class="{ 'tp-doc-switch--on': autoAnalyzeAfterUpload }"
            for="autoAnalyzeAfterUpload"
          >
            <input id="autoAnalyzeAfterUpload" v-model="autoAnalyzeAfterUpload" class="tp-doc-switch__input" type="checkbox" />
            <span class="tp-doc-switch__track" aria-hidden="true">
              <span class="tp-doc-switch__thumb"></span>
            </span>
            <span class="tp-doc-switch__state" :class="{ 'tp-doc-switch__state--on': autoAnalyzeAfterUpload }">
              {{ switchStateLabel(autoAnalyzeAfterUpload) }}
            </span>
            <span>{{ t('documents.upload.autoAnalyzeToggle') }}</span>
          </label>
        </template>
      </BaseUpload>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import BaseUpload from '@/components/common/BaseUpload.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import { uploadDocument, type DocumentAnalysisType } from '@/api/documents';

interface NoticeState {
  type: 'success' | 'danger' | 'warning' | 'info';
  message: string;
}

interface SelectOption {
  value: DocumentAnalysisType;
  label: string;
}

const { t, locale } = useI18n();
const router = useRouter();

const selectedFile = ref<File | null>(null);
const uploadLoading = ref(false);
const notice = ref<NoticeState | null>(null);
const analysisType = ref<DocumentAnalysisType>('requirements');
const autoAnalyzeAfterUpload = ref(true);

const analysisTypeOptions = computed<SelectOption[]>(() => [
  { value: 'requirements', label: t('enums.documents.analysisType.requirements') },
  { value: 'test_points', label: t('enums.documents.analysisType.test_points') },
  { value: 'business_rules', label: t('enums.documents.analysisType.business_rules') },
  { value: 'comprehensive', label: t('enums.documents.analysisType.comprehensive') }
]);

const noticeClass = computed(() => {
  const type = notice.value?.type || 'info';
  return {
    'tp-risk-block--info': type === 'info',
    'tp-risk-block--danger': type === 'danger',
    'tp-risk-block--warning': type === 'warning',
    'tp-risk-block--success': type === 'success'
  };
});

function showNotice(type: NoticeState['type'], message: string) {
  notice.value = { type, message };
}

function switchStateLabel(enabled: boolean) {
  const isZh = String(locale.value || '').toLowerCase().startsWith('zh');
  if (isZh) return enabled ? '开' : '关';
  return enabled ? 'ON' : 'OFF';
}

async function handleUpload(file: File) {
  if (uploadLoading.value) return;
  uploadLoading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('analysis_type', analysisType.value);
    const response = await uploadDocument(formData);
    showNotice('success', response.message || t('documents.message.uploadSuccess'));
    selectedFile.value = null;
    const target = response.file_info?.document_key || response.file_info?.filename || file.name;
    await router.push({
      name: 'documents',
      query: {
        fromUpload: '1',
        autoAnalyze: autoAnalyzeAfterUpload.value ? '1' : '0',
        target,
        analysisType: analysisType.value
      }
    });
  } catch (error) {
    showNotice('danger', error instanceof Error ? error.message : t('documents.message.uploadFailed'));
  } finally {
    uploadLoading.value = false;
  }
}
</script>

<style scoped>
.tp-doc-upload-analysis-type {
  width: min(360px, 100%);
  min-width: 220px;
}

.tp-doc-upload-head-main {
  min-width: 0;
  flex: 1;
}

.tp-doc-upload-auto-toggle {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.tp-doc-switch {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tp-bg-surface) 90%, var(--tp-color-text-100) 10%);
  cursor: pointer;
}

.tp-doc-switch__input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
  pointer-events: none;
}

.tp-doc-switch__track {
  width: 44px;
  height: 26px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tp-color-text-300) 86%, transparent);
  border: 1px solid var(--tp-border-default);
  position: relative;
  flex: 0 0 auto;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.tp-doc-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--tp-bg-surface);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.18);
  transition: transform 0.2s ease;
}

.tp-doc-switch__state {
  min-width: 34px;
  text-align: center;
  color: var(--tp-color-text-500);
  font-size: 11px;
  line-height: 1;
  font-weight: 700;
  padding: 4px 6px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--tp-color-text-300) 70%, transparent);
  background: color-mix(in srgb, var(--tp-color-text-200) 60%, transparent);
}

.tp-doc-switch--on {
  background: color-mix(in srgb, var(--tp-color-primary-500) 10%, var(--tp-bg-surface) 90%);
}

.tp-doc-switch--on .tp-doc-switch__track {
  background: var(--tp-color-primary-500);
  border-color: var(--tp-color-primary-600);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--tp-color-primary-500) 24%, transparent);
}

.tp-doc-switch--on .tp-doc-switch__thumb {
  transform: translateX(18px);
}

.tp-doc-switch__state--on {
  color: var(--tp-color-primary-700);
  border-color: color-mix(in srgb, var(--tp-color-primary-500) 60%, transparent);
  background: color-mix(in srgb, var(--tp-color-primary-500) 20%, transparent);
}

@media (max-width: 767.98px) {
  .tp-doc-upload-analysis-type {
    width: 100%;
    min-width: 0;
  }
}
</style>
