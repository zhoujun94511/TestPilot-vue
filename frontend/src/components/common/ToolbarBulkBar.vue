<template>
  <div v-if="count > 0" :class="toolbarBulkBarClass">
    <span :class="toolbarBulkBarMetaClass">{{ countLabel }}</span>
    <div class="flex flex-wrap items-center justify-end gap-2">
      <TpButton
        v-if="selectAllCount > count"
        variant="secondary"
        size="sm"
        type="button"
        @click="emit('selectAll')"
      >
        {{ t('common.toolbar.selectAllMatching', { count: selectAllCount }) }}
      </TpButton>
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
    /** 大于 count 时显示「选择全部 N 条」，N 是当前筛选下的总条数 */
    selectAllCount?: number;
  }>(),
  {
    countLabel: '',
    clearable: true,
    clearText: '',
    selectAllCount: 0
  }
);

const emit = defineEmits<{
  (event: 'clear'): void;
  (event: 'selectAll'): void;
}>();

const { t } = useI18n();

const countLabel = computed(
  () => props.countLabel || t('common.toolbar.selectedCount', { count: props.count })
);

const clearText = computed(() => props.clearText || t('common.toolbar.clearSelection'));
</script>
