<template>
  <nav :aria-label="t('common.shell.breadcrumb')">
    <ol :class="breadcrumbListClass">
      <li
        v-for="(item, index) in items"
        :key="`${item.label}-${index}`"
        :class="breadcrumbItemClass"
      >
        <RouterLink
          v-if="item.to && index < items.length - 1"
          :to="item.to"
          :class="breadcrumbLinkClass"
        >
          {{ item.label }}
        </RouterLink>
        <span
          v-else
          :class="breadcrumbCurrentClass"
          :aria-current="index === items.length - 1 ? 'page' : undefined"
        >
          {{ item.label }}
        </span>
        <ChevronRight
          v-if="index < items.length - 1"
          :class="breadcrumbSepClass"
          :size="14"
          aria-hidden="true"
        />
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { ChevronRight } from '@lucide/vue';
import { useI18n } from 'vue-i18n';
import { useBreadcrumbs } from '@/composables/useBreadcrumbs';
import {
  breadcrumbCurrentClass,
  breadcrumbItemClass,
  breadcrumbLinkClass,
  breadcrumbListClass,
  breadcrumbSepClass
} from '@/lib/shell-ui';

const { t } = useI18n();
const items = useBreadcrumbs();
</script>
