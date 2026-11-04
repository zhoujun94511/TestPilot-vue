<template>
  <nav :class="sidebarMenuClass" :aria-label="ariaLabel">
    <header
      v-if="title || $slots.header || $slots['header-extra']"
      :class="sidebarMenuHeaderClass"
    >
      <div class="min-w-0">
        <slot name="header">
          <div v-if="title" :class="sidebarMenuTitleClass">{{ title }}</div>
          <div v-if="subtitle" :class="sidebarMenuSubtitleClass">{{ subtitle }}</div>
        </slot>
      </div>
      <div v-if="$slots['header-extra']" class="shrink-0 self-center">
        <slot name="header-extra" />
      </div>
    </header>
    <div :class="sidebarMenuBodyClass">
      <slot />
    </div>
  </nav>
</template>

<script setup lang="ts">
import {
  sidebarMenuBodyClass,
  sidebarMenuClass,
  sidebarMenuHeaderClass,
  sidebarMenuSubtitleClass,
  sidebarMenuTitleClass
} from '@/lib/panel-ui';

withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string;
    ariaLabel?: string;
  }>(),
  {
    ariaLabel: ''
  }
);
</script>
