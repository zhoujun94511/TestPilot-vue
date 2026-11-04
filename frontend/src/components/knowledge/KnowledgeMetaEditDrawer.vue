<template>
  <FormSideDrawer
    :open="visible"
    :title="t('knowledge.edit.title')"
    :subtitle="record?.file_name || ''"
    :aria-label="t('knowledge.edit.title')"
    @close="emit('close')"
  >
    <BaseState v-if="!record" variant="empty" :title="t('knowledge.edit.empty')" />
    <div v-else class="flex flex-col gap-4">
      <TpInput v-model="form.category" as="select" :label="t('knowledge.upload.category')" :options="categoryOptions" />
      <TpInput v-model="form.description" as="textarea" :label="t('knowledge.upload.description')" :rows="5" />
    </div>

    <template v-if="record" #footer>
      <form class="flex justify-end gap-2" novalidate @submit.prevent="handleSubmit">
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
import { reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import FormSideDrawer from '@/components/common/FormSideDrawer.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import { updateKnowledgeFile, type KnowledgeFileRecord } from '@/api/knowledge';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';

interface SelectOption {
  value: string;
  label: string;
}

const props = defineProps<{
  visible: boolean;
  record: KnowledgeFileRecord | null;
  categoryOptions: SelectOption[];
}>();

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'saved', record: KnowledgeFileRecord): void;
  (event: 'error', message: string): void;
}>();

const { t } = useI18n();
const saving = ref(false);
const form = reactive({ category: '', description: '' });

watch(
  () => [props.visible, props.record?.id] as const,
  ([open]) => {
    if (!open || !props.record) return;
    form.category = String(props.record.category || 'other');
    form.description = String(props.record.description || '');
  }
);

async function handleSubmit() {
  if (!props.record?.id) return;
  try {
    saving.value = true;
    const updated = await updateKnowledgeFile(props.record.id, {
      category: form.category,
      description: form.description.trim()
    });
    emit('saved', updated);
  } catch (error) {
    emit('error', getUserFacingErrorMessage(error, t('knowledge.edit.failed')));
  } finally {
    saving.value = false;
  }
}
</script>
