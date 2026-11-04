import { getFeatureFlags } from '@/api/stats';
import { useAppStore } from '@/stores';

/** 从后端同步只读功能开关到 Pinia（失败时保留本地默认值） */
export async function refreshAppFeatureFlags(): Promise<void> {
  const appStore = useAppStore();
  try {
    const flags = await getFeatureFlags();
    appStore.setFeatureFlags({
      enableVectorStore: flags.enableVectorStore,
      experimentalActionsEnabled: flags.experimentalActionsEnabled
    });
  } catch {
    // 离线或旧后端：不阻断壳层渲染
  }
}
