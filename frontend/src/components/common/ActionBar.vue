<template>
  <div
    v-if="showBar"
    :class="actionsOnly ? pageToolbarActionsOnlyClass : cn(pageToolbarClass, toolbarRowAlignClass)"
  >
    <div v-if="!actionsOnly" :class="pageToolbarLeadClass">
      <slot name="lead" />
      <p v-if="subtitle && showSubtitle" :class="pageToolbarSubtitleClass">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" :class="actionsOnly ? 'flex justify-end' : toolbarActionsClass">
      <div :class="pageToolbarStripClass">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue';
import {
  pageToolbarActionsOnlyClass,
  pageToolbarClass,
  pageToolbarLeadClass,
  pageToolbarStripClass,
  pageToolbarSubtitleClass,
  toolbarActionsClass
} from '@/lib/page-chrome-ui';
import { cn } from '@/lib/utils';

const props = withDefaults(
  defineProps<{
    /** @deprecated 标题已移至顶栏，保留 prop 仅为兼容旧调用 */
    title?: string;
    subtitle?: string;
    /** 是否在工具栏重复展示副标题（默认否，副标题在顶栏展示） */
    showSubtitle?: boolean;
  }>(),
  {
    showSubtitle: false
  }
);

const slots = useSlots();

const showBar = computed(
  () => Boolean(slots.actions || slots.lead || (props.subtitle && props.showSubtitle))
);

const actionsOnly = computed(
  () =>
    Boolean(slots.actions) &&
    !slots.lead &&
    !(props.subtitle && props.showSubtitle)
);

/** 有 lead 时与右侧操作条垂直居中对齐 */
const toolbarRowAlignClass = computed(() =>
  slots.lead ? 'items-center' : 'items-start'
);
</script>
