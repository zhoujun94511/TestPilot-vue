<template>
  <section :class="pageRootMarkedClass(pageMarkerDocumentsUpload)">
    <PagePanel
      :title="t('documents.upload.title')"
      :subtitle="t('documents.upload.autoAnalyzeHint')"
    >
      <TpInput
        v-model="analysisType"
        as="select"
        :class="uploadCategoryFieldClass"
        :label="t('documents.upload.analysisType')"
        :options="analysisTypeOptions"
      />

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
          <TpSwitch
            v-model="autoAnalyzeAfterUpload"
            switch-id="autoAnalyzeAfterUpload"
            :class="docUploadAutoToggleClass"
            :label="t('documents.upload.autoAnalyzeToggle')"
          />
        </template>
      </BaseUpload>
    </PagePanel>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import BaseUpload from '@/components/common/BaseUpload.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpSwitch from '@/components/ui/base/TpSwitch.vue';
import { pageMarkerDocumentsUpload, pageRootMarkedClass } from '@/lib/page-layout-ui';
import { docUploadAutoToggleClass, uploadCategoryFieldClass } from '@/lib/upload-ui';
import { cn } from '@/lib/utils';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { useToast } from '@/composables/useToast';
import { uploadDocument, type DocumentAnalysisType } from '@/api/documents';

interface SelectOption {
  value: DocumentAnalysisType;
  label: string;
}

const { t } = useI18n();
const router = useRouter();
const toast = useToast();

const selectedFile = ref<File | null>(null);
const uploadLoading = ref(false);
const analysisType = ref<DocumentAnalysisType>('requirements');
const autoAnalyzeAfterUpload = ref(true);

const analysisTypeOptions = computed<SelectOption[]>(() => [
  { value: 'requirements', label: t('enums.documents.analysisType.requirements') },
  { value: 'test_points', label: t('enums.documents.analysisType.test_points') },
  { value: 'business_rules', label: t('enums.documents.analysisType.business_rules') },
  { value: 'comprehensive', label: t('enums.documents.analysisType.comprehensive') }
]);

async function handleUpload(file: File | File[]) {
  const selected = Array.isArray(file) ? file[0] : file;
  if (!selected || uploadLoading.value) return;
  uploadLoading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', selected);
    formData.append('analysis_type', analysisType.value);
    const response = await uploadDocument(formData);
    toast.success(response.message || t('documents.message.uploadSuccess'));
    selectedFile.value = null;
    const target = response.file_info?.document_key || response.file_info?.filename || selected.name;
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
    toast.error(getUserFacingErrorMessage(error, t('documents.message.uploadFailed')));
  } finally {
    uploadLoading.value = false;
  }
}
</script>

