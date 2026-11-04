<template>
  <div
    v-if="notice && !isPageNoticeToastSuppressed(notice.type)"
    :class="pageNoticeBannerShellClass({ tone: notice.type })"
    :style="{ '--page-notice-accent': pageNoticeAccentVar(notice.type) }"
    role="status"
    aria-live="polite"
  >
    <span
      :class="cn(pageNoticeBannerIconWrapClass, pageNoticeBannerIconSurfaceClass({ tone: notice.type }))"
      aria-hidden="true"
    >
      {{ pageNoticeIconGlyph(notice.type) }}
    </span>
    <div :class="flexWrapBetweenStartGap3Class">
      <div :class="flexGrowMinClass">
        <div v-if="notice.title" class="mb-1 font-bold">{{ notice.title }}</div>
        <div :class="pageNoticeBannerMessageClass({ tone: notice.type })">{{ notice.message }}</div>
        <div v-if="notice.details?.length" class="mt-2">
          <TpButton
            variant="ghost"
            size="sm"
            :class="pageNoticeGhostButtonClass"
            @click="detailsExpanded = !detailsExpanded"
          >
            {{ detailsExpanded ? t('common.actions.collapse') : t('common.actions.expand') }}
          </TpButton>
          <ul v-if="detailsExpanded" :class="[captionTextClass, 'mb-0 mt-2 list-disc ps-4']">
            <li v-for="(detail, index) in notice.details" :key="index">{{ detail }}</li>
          </ul>
        </div>
      </div>
      <div :class="flexCenterGap2Class">
        <TpButton
          v-if="notice.actionLabel"
          variant="secondary"
          size="sm"
          @click="emit('action')"
        >
          {{ notice.actionLabel }}
        </TpButton>
        <TpButton
          variant="ghost"
          size="sm"
          :class="pageNoticeGhostButtonClass"
          :aria-label="t('common.actions.close')"
          @click="emit('close')"
        >
          {{ t('common.actions.close') }}
        </TpButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import TpButton from '@/components/ui/base/TpButton.vue';
import {
  flexCenterGap2Class,
  flexGrowMinClass,
  flexWrapBetweenStartGap3Class
} from '@/lib/page-chrome-ui';
import { captionTextClass } from '@/lib/page-typography';
import {
  isPageNoticeToastSuppressed,
  pageNoticeGhostButtonClass,
  pageNoticeAccentVar,
  pageNoticeBannerIconSurfaceClass,
  pageNoticeBannerIconWrapClass,
  pageNoticeBannerMessageClass,
  pageNoticeBannerShellClass,
  pageNoticeIconGlyph
} from '@/lib/notice-ui';
import { cn } from '@/lib/utils';
import type { PageBannerNotice } from '@/composables/usePageNotice';

const props = defineProps<{
  notice: PageBannerNotice | null;
}>();

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'action'): void;
}>();

const { t } = useI18n();
const detailsExpanded = ref(false);

watch(
  () => props.notice,
  () => {
    detailsExpanded.value = false;
  }
);
</script>
