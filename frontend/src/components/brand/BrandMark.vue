<template>
  <img
    :src="brandMarkSrc"
    :srcset="brandMarkSrcSet"
    sizes="(max-width: 768px) 32px, 40px"
    :alt="altText"
    :class="[brandMarkSizeClass(size), brandMarkInsetClass, props.class]"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { brandMarkSrc, brandMarkSrcSet } from '@/lib/brand';
import { brandMarkInsetClass, brandMarkSizeClass, type BrandMarkSize } from '@/lib/brand-ui';

const props = withDefaults(
  defineProps<{
    size?: BrandMarkSize;
    decorative?: boolean;
    class?: string;
  }>(),
  {
    size: 'md',
    decorative: false,
    class: ''
  }
);

const { t } = useI18n();

const altText = computed(() => (props.decorative ? '' : t('common.app.brand')));
</script>
