import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { AuthUser, UserRole } from '@/api/auth';
import { fetchCheckAuth, login as apiLogin, logout as apiLogout } from '@/api/auth';
import { EXPERIMENTAL_TOOLS_SESSION_STORAGE_KEY } from '@/config/experimentalTools';
import { setTabProjectId } from '@/lib/current-project';
import { clearSessionToken } from '@/api/sessionToken';

export const useAuthStore = defineStore('auth', () => {
  const bootstrapped = ref(false);
  // 与后端 AUTH_REQUIRE_AUTH 默认值一致；探测失败时按需要登录处理
  const authRequired = ref(true);
  const registerEnabled = ref(false);
  const registerRequiresApproval = ref(true);
  const passwordComplexityRequired = ref(true);
  const user = ref<AuthUser | null>(null);

  const isAuthenticated = computed(() => user.value !== null);
  const role = computed(() => user.value?.role ?? null);

  async function bootstrap() {
    const state = await fetchCheckAuth();
    authRequired.value = state.authRequired;
    registerEnabled.value = state.registerEnabled;
    registerRequiresApproval.value = state.registerRequiresApproval;
    passwordComplexityRequired.value = state.passwordComplexityRequired;
    user.value = state.user;
    bootstrapped.value = true;
    return state;
  }

  async function login(username: string, password: string) {
    const loggedIn = await apiLogin(username, password);
    user.value = loggedIn;
  }

  function clearSession() {
    user.value = null;
    clearSessionToken();
  }

  function markPasswordChangeRequired() {
    if (user.value && !user.value.must_change_password) {
      user.value = { ...user.value, must_change_password: true };
    }
  }

  /** 不抛错：接口失败时本地状态照样清掉，调用方可以直接跳到登录页 */
  async function logout() {
    try {
      await apiLogout();
    } catch (error) {
      console.warn('logout request failed', error);
    } finally {
      clearSession();
      localStorage.removeItem(EXPERIMENTAL_TOOLS_SESSION_STORAGE_KEY);
      setTabProjectId(null);
    }
  }

  function hasRole(...roles: UserRole[]) {
    const current = user.value?.role;
    if (!current) return false;
    return roles.includes(current);
  }

  function canSeeConfigCenter() {
    if (!authRequired.value) return true;
    return hasRole('super_admin');
  }

  function canManageKnowledgeIndex() {
    if (!authRequired.value) return true;
    return hasRole('super_admin', 'admin');
  }

  return {
    bootstrapped,
    authRequired,
    registerEnabled,
    registerRequiresApproval,
    passwordComplexityRequired,
    user,
    isAuthenticated,
    role,
    bootstrap,
    login,
    clearSession,
    markPasswordChangeRequired,
    logout,
    hasRole,
    canSeeConfigCenter,
    canManageKnowledgeIndex
  };
});
