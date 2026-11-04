<template>
  <Dialog :open="dialogOpen" @update:open="onDialogOpenChange">
    <DialogContent class="max-w-[560px]" :labelled-by="titleId">
      <div class="flex items-start justify-between gap-3">
        <DialogHeader class="flex-1 pr-2">
          <DialogTitle :id="titleId">{{ resolvedTitle }}</DialogTitle>
          <DialogDescription v-if="resolvedMessage" class="mt-2">
            {{ resolvedMessage }}
          </DialogDescription>
        </DialogHeader>
        <TpButton
          variant="ghost"
          size="sm"
          class="min-w-[30px] shrink-0 px-2 text-lg leading-none"
          :aria-label="t('common.actions.close')"
          @click="cancel"
        >
          ×
        </TpButton>
      </div>

      <DialogFooter>
        <TpButton variant="secondary" @click="cancel">
          {{ resolvedCancelText }}
        </TpButton>
        <TpButton :variant="confirmVariant || 'primary'" @click="confirm">
          {{ resolvedConfirmText }}
        </TpButton>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, unref, useId, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import TpButton from '@/components/ui/base/TpButton.vue';

const { t } = useI18n();

const props = defineProps<{
  modelValue: boolean;
  title: string;
  message?: string;
  confirmText: string;
  cancelText: string;
  confirmVariant?: 'primary' | 'danger' | 'warning';
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void;
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const titleId = useId();
/** 区分「确认关闭」与遮罩/Esc/父级 v-model 关闭，避免误触发 cancel */
const closingViaConfirm = ref(false);

function unwrapText(value: unknown) {
  return String(unref(value as never) ?? '').trim();
}

const resolvedTitle = computed(() => unwrapText(props.title));
const resolvedMessage = computed(() => unwrapText(props.message));
const resolvedConfirmText = computed(() => unwrapText(props.confirmText));
const resolvedCancelText = computed(() => unwrapText(props.cancelText));
const resolvedOpen = computed(() => Boolean(unref(props.modelValue as never)));

const hasContent = computed(
  () => resolvedTitle.value.length > 0 && resolvedConfirmText.value.length > 0
);

const dialogOpen = computed(() => resolvedOpen.value && hasContent.value);

watch(
  () => props.modelValue,
  (open) => {
    if (open && !hasContent.value) {
      emit('update:modelValue', false);
      emit('cancel');
    }
  },
  { immediate: true }
);

function onDialogOpenChange(open: boolean) {
  if (open) {
    if (!hasContent.value) {
      emit('update:modelValue', false);
      return;
    }
    closingViaConfirm.value = false;
    return;
  }

  emit('update:modelValue', false);
  if (!closingViaConfirm.value) {
    emit('cancel');
  }
  closingViaConfirm.value = false;
}

function confirm() {
  closingViaConfirm.value = true;
  emit('confirm');
  emit('update:modelValue', false);
}

function cancel() {
  emit('cancel');
  emit('update:modelValue', false);
}
</script>
