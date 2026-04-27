<template>
  <TpState :variant="normalizedVariant" :title="title" :message="message">
    <template v-if="variant === 'error'" #actions>
      <slot name="action" />
      <TpButton v-if="retryText" variant="danger" size="sm" @click="emit('retry')">
        {{ retryText }}
      </TpButton>
    </template>

    <slot v-if="variant !== 'error'" />
  </TpState>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import TpState from '@/components/ui/base/TpState.vue';
import TpButton from '@/components/ui/base/TpButton.vue';

type Variant = 'loading' | 'empty' | 'error' | 'success' | 'warning' | 'info' | 'processing' | 'analyzing' | 'generating';

const props = defineProps<{
  variant: Variant;
  title: string;
  message?: string;
  retryText?: string;
}>();

const emit = defineEmits<{
  (event: 'retry'): void;
}>();

const normalizedVariant = computed(() => props.variant);
</script>
