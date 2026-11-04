<template>
  <div :class="appToastStackClass" aria-live="polite" aria-relevant="additions text">
    <TransitionGroup :name="APP_TOAST_TRANSITION_NAME">
      <article
        v-for="toast in appStore.toasts"
        :key="toast.id"
        :class="appToastItemClass({ type: toast.type as AppToastType })"
        role="status"
      >
        <div :class="appToastIconClass({ type: toast.type as AppToastType })" aria-hidden="true">
          <CheckCircle2 v-if="toast.type === 'success'" :size="18" :stroke-width="2" />
          <AlertTriangle v-else-if="toast.type === 'warning'" :size="18" :stroke-width="2" />
          <CircleAlert v-else-if="toast.type === 'danger'" :size="18" :stroke-width="2" />
          <Info v-else :size="18" :stroke-width="2" />
        </div>
        <div :class="appToastBodyClass">
          <div v-if="toast.title" :class="appToastTitleClass">{{ toast.title }}</div>
          <div :class="appToastMessageClass">{{ toast.message }}</div>
        </div>
        <button
          type="button"
          :class="appToastCloseClass"
          :aria-label="t('common.actions.close')"
          @click="dismiss(toast.id)"
        >
          <X :size="16" :stroke-width="2" />
        </button>
      </article>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue';
import { AlertTriangle, CheckCircle2, CircleAlert, Info, X } from '@lucide/vue';
import { useI18n } from 'vue-i18n';
import { useAppStore } from '@/stores';
import {
  APP_TOAST_TRANSITION_NAME,
  appToastBodyClass,
  appToastCloseClass,
  appToastIconClass,
  appToastItemClass,
  appToastMessageClass,
  appToastStackClass,
  appToastTitleClass,
  type AppToastType
} from '@/lib/toast-ui';

const { t } = useI18n();
const appStore = useAppStore();

const timers = new Map<number, number>();

function dismiss(id: number) {
  const timer = timers.get(id);
  if (timer) {
    window.clearTimeout(timer);
    timers.delete(id);
  }
  appStore.removeToast(id);
}

watch(
  () => appStore.toasts.map((toast) => ({ id: toast.id, timeout: toast.timeout })),
  (entries) => {
    const activeIds = new Set(entries.map((entry) => entry.id));

    timers.forEach((timer, id) => {
      if (!activeIds.has(id)) {
        window.clearTimeout(timer);
        timers.delete(id);
      }
    });

    entries.forEach((entry) => {
      if (timers.has(entry.id)) return;
      const timeout = entry.timeout ?? 4500;
      if (timeout <= 0) return;
      const timer = window.setTimeout(() => dismiss(entry.id), timeout);
      timers.set(entry.id, timer);
    });
  },
  { deep: true, immediate: true }
);

onBeforeUnmount(() => {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers.clear();
});
</script>
