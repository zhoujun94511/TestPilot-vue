<template>
  <DropdownMenu :modal="false">
    <DropdownMenuTrigger as-child>
      <TpButton
        variant="ghost"
        size="sm"
        type="button"
        class="px-2"
        :aria-label="displayLabel"
      >
        <MoreHorizontal class="h-4 w-4" aria-hidden="true" />
      </TpButton>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" :side-offset="6">
      <slot />
    </DropdownMenuContent>
  </DropdownMenu>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { MoreHorizontal } from '@lucide/vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';

const props = withDefaults(
  defineProps<{
    label?: string;
    iconOnly?: boolean;
  }>(),
  {
    label: '',
    iconOnly: true
  }
);

const { t } = useI18n();
const displayLabel = computed(() => props.label || t('common.actions.more'));
</script>
