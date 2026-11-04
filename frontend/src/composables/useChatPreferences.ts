import { ref, watch, type Ref } from 'vue';

const STORAGE_PREFIX = 'chat.';

export function readChatBooleanSetting(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${key}`);
    if (raw === '1') return true;
    if (raw === '0') return false;
    return fallback;
  } catch {
    return fallback;
  }
}

export function persistChatBooleanSetting(key: string, value: boolean): void {
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${key}`, value ? '1' : '0');
  } catch {
    // private mode 等场景忽略
  }
}

/** Chat  composer 本地开关（localStorage `chat.*`） */
export function useChatBooleanPreference(key: string, fallback: boolean): Ref<boolean> {
  const value = ref(readChatBooleanSetting(key, fallback));
  watch(value, (next) => persistChatBooleanSetting(key, next));
  return value;
}

export function chatSwitchStateLabel(enabled: boolean, locale: string): string {
  const isZh = String(locale || '').toLowerCase().startsWith('zh');
  if (isZh) return enabled ? '开' : '关';
  return enabled ? 'ON' : 'OFF';
}
