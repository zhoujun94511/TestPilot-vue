import { onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { getTokenSessionStatus, type TokenSessionStatus } from '@/api/stats';
import { useToast } from '@/composables/useToast';

const AI_ROUTE_PREFIXES = ['/cases', '/documents', '/chat', '/config'];

let lastWarnSignature = '';

function isAiHeavyRoute(path: string) {
  return AI_ROUTE_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

function resolveNoticeMessage(status: TokenSessionStatus, t: (key: string, params?: Record<string, unknown>) => string) {
  if (status.level !== 'warning' || !status.message_key) {
    return null;
  }
  return t(status.message_key, status.message_params || {});
}

/**
 * 在会触发 LLM 的页面轮询后端 TokenMonitor，接近会话上限时 Toast 预警（每档签名只提示一次）。
 */
export function useTokenSessionNotice() {
  const route = useRoute();
  const { t } = useI18n();
  const toast = useToast();
  let timer: ReturnType<typeof setInterval> | undefined;

  async function poll() {
    if (!isAiHeavyRoute(route.path)) {
      return;
    }
    try {
      const status = await getTokenSessionStatus();
      if (status.level !== 'warning' || !status.notice_signature) {
        return;
      }
      if (status.notice_signature === lastWarnSignature) {
        return;
      }
      const message = resolveNoticeMessage(status, t);
      if (!message) {
        return;
      }
      lastWarnSignature = status.notice_signature;
      toast.warning(message);
    } catch {
      // 非关键路径，忽略网络错误
    }
  }

  watch(
    () => route.path,
    () => {
      void poll();
    }
  );

  onMounted(() => {
    void poll();
    timer = setInterval(() => void poll(), 45000);
  });

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer);
    }
  });
}

/** 供单测或手动刷新：重置已展示预警签名 */
export function resetTokenSessionNoticeDedupe() {
  lastWarnSignature = '';
}
