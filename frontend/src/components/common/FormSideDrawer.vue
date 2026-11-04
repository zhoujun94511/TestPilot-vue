<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="pointer-events-none fixed inset-0 z-[1100]"
      role="presentation"
    >
      <div
        v-if="dismissible"
        :class="formSideDrawerBackdropClass"
        aria-hidden="true"
        @click="emit('close')"
      />
      <aside
        role="dialog"
        aria-modal="true"
        :aria-label="ariaLabel || title"
        :class="panelClass"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 py-3">
          <div class="min-w-0">
            <div class="text-base font-semibold text-foreground">{{ title }}</div>
            <div v-if="subtitle" class="mt-1 truncate text-sm text-muted-foreground" :title="subtitle">
              {{ subtitle }}
            </div>
            <div v-if="$slots['header-meta']" class="mt-1 text-xs text-muted-foreground">
              <slot name="header-meta" />
            </div>
          </div>
          <slot name="header-actions">
            <TpButton variant="ghost" size="sm" @click="emit('close')">
              {{ closeLabel }}
            </TpButton>
          </slot>
        </header>

        <div :class="bodyClass">
          <slot />
        </div>

        <footer v-if="$slots.footer" class="shrink-0 border-t border-border bg-background px-4 py-3">
          <slot name="footer" />
        </footer>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import TpButton from '@/components/ui/base/TpButton.vue';
import { lockDocumentScroll, unlockDocumentScroll } from '@/lib/scroll-lock';
import {
  formSideDrawerBackdropClass,
  formSideDrawerBodyClass,
  formSideDrawerPanelClass
} from '@/lib/form-side-drawer-ui';
import { cn } from '@/lib/utils';

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    subtitle?: string;
    ariaLabel?: string;
    closeLabel?: string;
    dismissible?: boolean;
    /** 例如 max-w-[min(100vw,720px)] */
    panelWidthClass?: string;
  }>(),
  {
    subtitle: '',
    ariaLabel: '',
    closeLabel: '',
    dismissible: true,
    panelWidthClass: ''
  }
);

const emit = defineEmits<{
  (event: 'close'): void;
}>();

const { t } = useI18n();
const closeLabel = computed(() => props.closeLabel || t('common.actions.close'));

const panelClass = computed(() =>
  props.panelWidthClass ? cn(formSideDrawerPanelClass, props.panelWidthClass) : formSideDrawerPanelClass
);

const bodyClass = formSideDrawerBodyClass;

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open && props.dismissible) {
    emit('close');
  }
}

watch(
  () => props.open,
  (next) => {
    if (next) {
      lockDocumentScroll();
      window.addEventListener('keydown', onKeydown);
    } else {
      unlockDocumentScroll();
      window.removeEventListener('keydown', onKeydown);
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (props.open) unlockDocumentScroll();
  window.removeEventListener('keydown', onKeydown);
});
</script>
