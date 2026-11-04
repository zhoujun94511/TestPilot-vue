<template>
  <FormSideDrawer
    :open="visible"
    :title="t('documents.requirement.editTitle')"
    :subtitle="activeRecord?.req_id || ''"
    :aria-label="t('documents.requirement.editTitle')"
    @close="emit('close')"
  >
    <BaseState v-if="loading" variant="loading" :title="t('documents.requirement.editLoading')" />
    <BaseState v-else-if="loadError" variant="error" :title="t('common.status.error')" :message="loadError" />
    <BaseState v-else-if="!activeRecord" variant="empty" :title="t('documents.requirement.editEmpty')" />
    <div v-else class="flex flex-col gap-4">
      <TpInput
        v-model="form.title"
        :label="t('documents.requirement.title')"
        required
        :error="fieldErrors.title"
      />
      <TpInput
        v-model="form.content"
        as="textarea"
        :label="t('documents.requirement.content')"
        :rows="10"
        required
        :error="fieldErrors.content"
      />
      <div class="grid gap-4 md:grid-cols-2">
        <TpInput v-model="form.type" as="select" :label="t('documents.requirement.type')" :options="typeOptions" />
        <TpInput v-model="form.priority" as="select" :label="t('documents.requirement.priority')" :options="priorityOptions" />
      </div>
      <TpInput
        v-model="form.status"
        as="select"
        :label="t('documents.requirement.statusLabel')"
        :options="statusOptions"
      />
    </div>

    <template v-if="activeRecord && !loading && !loadError" #footer>
      <form class="flex flex-wrap justify-end gap-2" novalidate @submit.prevent="handleSubmit">
        <TpButton variant="ghost" type="button" :disabled="saving" @click="emit('close')">
          {{ t('common.actions.cancel') }}
        </TpButton>
        <TpButton type="submit" :loading="saving" :disabled="saving">
          {{ t('common.actions.save') }}
        </TpButton>
      </form>
    </template>
  </FormSideDrawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import FormSideDrawer from '@/components/common/FormSideDrawer.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import {
  getRequirement,
  updateRequirement,
  type DocumentRequirementRecord,
  type RequirementUpdatePayload
} from '@/api/documents';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { applyRequiredFieldErrors } from '@/lib/required-field';
import { buildRequirementStatusSelectOptions, normalizeRequirementStatusKey } from '@/lib/requirement-status-ui';

interface SelectOption {
  value: string;
  label: string;
}

const props = defineProps<{
  visible: boolean;
  record: DocumentRequirementRecord | null;
  typeOptions: SelectOption[];
  priorityOptions: SelectOption[];
}>();

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'saved', record: DocumentRequirementRecord): void;
  (event: 'error', message: string): void;
}>();

const { t } = useI18n();
const statusOptions = computed(() => buildRequirementStatusSelectOptions(t));
const saving = ref(false);
const loading = ref(false);
const loadError = ref('');
const loadedRecord = ref<DocumentRequirementRecord | null>(null);

const activeRecord = computed(() => loadedRecord.value || props.record);

const form = reactive({
  title: '',
  content: '',
  type: 'functional',
  priority: 'P2',
  status: 'active'
});

const fieldErrors = reactive({ title: '', content: '' });

function resetForm(record: DocumentRequirementRecord | null) {
  if (!record) {
    form.title = '';
    form.content = '';
    form.type = 'functional';
    form.priority = 'P2';
    form.status = 'active';
    return;
  }
  form.title = record.title || '';
  form.content = record.content || '';
  form.type = String(record.type || 'functional');
  form.priority = String(record.priority || 'P2');
  form.status = normalizeRequirementStatusKey(record.status);
}

async function loadDetail(reqId: string) {
  loading.value = true;
  loadError.value = '';
  loadedRecord.value = null;
  try {
    loadedRecord.value = await getRequirement(reqId);
    resetForm(loadedRecord.value);
  } catch (error) {
    loadError.value = getUserFacingErrorMessage(error, t('documents.message.loadAnalysisFailed'));
    if (props.record) resetForm(props.record);
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.visible, props.record?.req_id] as const,
  ([open, reqId]) => {
    if (!open || !reqId) {
      loadedRecord.value = null;
      loadError.value = '';
      return;
    }
    void loadDetail(String(reqId));
  }
);

async function handleSubmit() {
  const reqId = activeRecord.value?.req_id;
  if (!reqId) return;
  if (!applyRequiredFieldErrors(fieldErrors, { title: form.title, content: form.content })) {
    return;
  }
  const title = form.title.trim();
  const content = form.content.trim();

  const payload: RequirementUpdatePayload = {
    title,
    content,
    type: form.type,
    priority: form.priority,
    status: form.status
  };

  try {
    saving.value = true;
    const updated = await updateRequirement(reqId, payload);
    emit('saved', updated);
  } catch (error) {
    emit('error', getUserFacingErrorMessage(error, t('documents.requirement.updateFailed')));
  } finally {
    saving.value = false;
  }
}
</script>
