import { onBeforeUnmount, ref } from 'vue';

/** 路由跳转或操作后短时高亮若干 id，到期自动清除 */
export function useTimedHighlight(defaultDurationMs = 4200) {
  const activeKeys = ref<Set<string>>(new Set());
  let timer: number | null = null;

  function highlight(keys: string[], durationMs = defaultDurationMs, maxKeys = 12) {
    const normalized = keys.map((item) => String(item || '').trim()).filter(Boolean).slice(0, maxKeys);
    if (!normalized.length) return;
    activeKeys.value = new Set(normalized);
    if (timer !== null) {
      window.clearTimeout(timer);
    }
    timer = window.setTimeout(() => {
      activeKeys.value = new Set();
      timer = null;
    }, durationMs);
  }

  function clear() {
    activeKeys.value = new Set();
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  function has(key: string) {
    const id = String(key || '').trim();
    return id ? activeKeys.value.has(id) : false;
  }

  onBeforeUnmount(clear);

  return { activeKeys, highlight, clear, has };
}
