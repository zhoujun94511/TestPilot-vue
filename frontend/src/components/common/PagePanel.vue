<template>
  <section :class="sectionShellClass">
    <header v-if="showHeader" :class="panelHeaderClass">
      <div class="min-w-0">
        <slot name="header">
          <div v-if="title" :class="titleClass">{{ title }}</div>
          <div v-if="subtitle" :class="subtitleClass">{{ subtitle }}</div>
        </slot>
      </div>
      <div v-if="$slots.actions" :class="panelActionsClass">
        <slot name="actions" />
      </div>
    </header>
    <div :class="panelBodyClass({ padded, hasHeader: showHeader })">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineOptions({ inheritAttrs: false });

import { computed, useAttrs, useSlots } from 'vue';
import { cn } from '@/lib/utils';
import {
  attrsIncludeConfigSection,
  configSectionPanelShellClass,
  panelActionsClass,
  panelBodyClass,
  panelConfigSubtitleClass,
  panelConfigTitleClass,
  panelHeaderClass,
  panelShellClass,
  panelSubtitleClass,
  panelTitleClass
} from '@/lib/panel-ui';

const props = withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string;
    padded?: boolean;
    flat?: boolean;
    /** 侧栏式面板（如配置分类） */
    aside?: boolean;
  }>(),
  {
    padded: true,
    flat: false,
    aside: false
  }
);

const attrs = useAttrs();
const slots = useSlots();

const isConfigSection = computed(() => attrsIncludeConfigSection(attrs.class));

const sectionShellClass = computed(() =>
  cn(
    isConfigSection.value
      ? configSectionPanelShellClass
      : panelShellClass({ flat: props.flat, aside: props.aside }),
    attrs.class
  )
);

const showHeader = computed(
  () =>
    Boolean(slots.header || slots.actions || props.title || props.subtitle)
);

const titleClass = computed(() =>
  isConfigSection.value ? panelConfigTitleClass : panelTitleClass
);

const subtitleClass = computed(() =>
  isConfigSection.value ? panelConfigSubtitleClass : panelSubtitleClass
);
</script>
