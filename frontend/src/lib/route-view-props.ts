import type { RouteLocationNormalizedLoaded } from 'vue-router';

/** DefaultLayout 一级 outlet：切换 documents/knowledge/cases 时必须销毁旧 Shell */
export function shellModuleKey(route: RouteLocationNormalizedLoaded): string {
  const segment = route.path.replace(/\/+$/, '').split('/').filter(Boolean)[0];
  return segment || 'dashboard';
}

/** KeepAlive + `<component :is>` 时需手动传入路由 props（与默认 `<router-view />` 行为一致） */
export function leafRouteProps(route: RouteLocationNormalizedLoaded): Record<string, unknown> {
  const leaf = route.matched.at(-1);
  if (!leaf?.props) return {};

  const raw = leaf.props as
    | boolean
    | Record<string, unknown>
    | ((to: RouteLocationNormalizedLoaded) => Record<string, unknown>);

  if (typeof raw === 'function') {
    return raw(route) ?? {};
  }
  if (raw === true) {
    return { ...route.params };
  }
  if (typeof raw === 'object' && raw !== null) {
    if ('default' in raw) {
      const def = (raw as { default: unknown }).default;
      if (typeof def === 'function') {
        return (def as (to: RouteLocationNormalizedLoaded) => Record<string, unknown>)(route) ?? {};
      }
      if (def === true) {
        return { ...route.params };
      }
      if (typeof def === 'object' && def !== null) {
        return def as Record<string, unknown>;
      }
      return {};
    }
    return raw as Record<string, unknown>;
  }
  return {};
}
