<template>
  <div v-if="count > 0" :class="toolbarBulkBarClass">
    <span :class="toolbarBulkBarMetaClass">{{ countLabel }}</span>
    <div class="flex flex-wrap items-center justify-end gap-2">
      <slot />
      <TpButton v-if="clearable" variant="ghost" size="sm" type="button" @click="emit('clear')">
        {{ clearText }}
      </TpButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import TpButton from '@/components/ui/base/TpButton.vue';
import { toolbarBulkBarClass, toolbarBulkBarMetaClass } from '@/lib/page-chrome-ui';

const props = withDefaults(
  defineProps<{
    count: number;
    countLabel?: string;
    clearable?: boolean;
    clearText?: string;
  }>(),
  {
    countLabel: '',
    clearable: true,
    clearText: ''
  }
);

const emit = defineEmits<{
  (event: 'clear'): void;
}>();

const { t } = useI18n();

const countLabel = computed(
  () => props.countLabel || t('common.toolbar.selectedCount', { count: props.count })
);

const clearText = computed(() => props.clearText || t('common.toolbar.clearSelection'));
</script>
