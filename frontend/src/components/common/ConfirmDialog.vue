<template>
  <Teleport to="body">
    <div v-if="modelValue" class="tp-confirm-backdrop">
      <div class="tp-confirm-dialog tp-card">
      <div class="tp-card__body">
          <div class="tp-flex tp-justify-between tp-align-start tp-gap-3 tp-mb-3">
            <div>
              <div class="tp-dialog__title">{{ title }}</div>
              <p v-if="message" class="tp-dialog__message tp-mb-0">{{ message }}</p>
            </div>
            <TpButton variant="ghost" size="sm" class="tp-dialog__close" :aria-label="t('common.actions.close')" @click="cancel">
              ×
            </TpButton>
          </div>

          <div class="tp-flex tp-justify-end tp-gap-2">
            <TpButton variant="secondary" @click="cancel">
              {{ cancelText }}
            </TpButton>
            <TpButton :variant="confirmVariant || 'primary'" @click="confirm">
              {{ confirmText }}
            </TpButton>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
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

function confirm() {
  emit('confirm');
  emit('update:modelValue', false);
}

function cancel() {
  emit('cancel');
  emit('update:modelValue', false);
}
</script>

<style scoped>
.tp-dialog__close {
  min-width: 30px;
  padding-inline: 8px;
  font-size: 18px;
  line-height: 1;
}
</style>
