<template>
  <TpCard>
    <div class="tp-kpi-card">
      <div class="tp-flex tp-align-start tp-justify-between tp-gap-2">
        <div>
          <div class="tp-kpi-label">{{ label }}</div>
          <div class="tp-kpi-value">{{ value }}</div>
        </div>
        <div class="tp-kpi-icon" aria-hidden="true">{{ icon }}</div>
      </div>
      <div>
        <div class="tp-card__subtitle tp-mt-2" :class="{ 'tp-kpi-hint--placeholder': !hint }">
          {{ hint || '\u00A0' }}
        </div>
      </div>
    </div>
  </TpCard>
</template>

<script setup lang="ts">
import TpCard from '@/components/ui/base/TpCard.vue';

defineProps<{
  label: string;
  value: string | number;
  icon?: string;
  hint?: string;
}>();
</script>

<style scoped>
.tp-kpi-card {
  min-height: 98px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.tp-kpi-hint--placeholder {
  visibility: hidden;
}
</style>
