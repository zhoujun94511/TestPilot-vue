<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue';

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
}>();

const layerRef = ref<HTMLElement | null>(null);

function onOverlayClick() {
  emit('update:open', false);
}

function listFocusables(scope: HTMLElement) {
  return Array.from(
    scope.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1);
}

function onKeydown(event: KeyboardEvent) {
  if (!props.open) return;

  if (event.key === 'Escape') {
    emit('update:open', false);
    return;
  }

  if (event.key !== 'Tab' || !layerRef.value) return;

  const dialog = layerRef.value.querySelector('[role="dialog"]') as HTMLElement | null;
  const scope = dialog ?? layerRef.value;
  const focusables = listFocusables(scope);
  if (focusables.length === 0) return;

  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  const active = document.activeElement as HTMLElement | null;

  if (event.shiftKey) {
    if (active === first || !scope.contains(active)) {
      event.preventDefault();
      last.focus();
    }
    return;
  }

  if (active === last || !scope.contains(active)) {
    event.preventDefault();
    first.focus();
  }
}

function focusDialogPanel() {
  const dialog = layerRef.value?.querySelector('[role="dialog"]') as HTMLElement | null;
  if (!dialog) return;

  const focusables = listFocusables(dialog);
  (focusables[0] ?? dialog).focus();
}

watch(
  () => props.open,
  async (next) => {
    if (next) {
      window.addEventListener('keydown', onKeydown);
      await nextTick();
      focusDialogPanel();
    } else {
      window.removeEventListener('keydown', onKeydown);
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="layerRef"
      class="fixed inset-0 z-[1050] flex items-center justify-center p-5"
      role="presentation"
    >
      <div
        class="fixed inset-0 bg-[var(--tp-overlay-scrim)] backdrop-blur-sm"
        aria-hidden="true"
        @click="onOverlayClick"
      />
      <slot />
    </div>
  </Teleport>
</template>
