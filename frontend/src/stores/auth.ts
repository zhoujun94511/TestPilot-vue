import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { AuthUser, UserRole } from '@/api/auth';
import { fetchCheckAuth, login as apiLogin, logout as apiLogout } from '@/api/auth';

export const useAuthStore = defineStore('auth', () => {
  const bootstrapped = ref(false);
  const authRequired = ref(false);
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
  }

  async function logout() {
    try {
      await apiLogout();
    } finally {
      user.value = null;
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
    logout,
    hasRole,
    canSeeConfigCenter
  };
});
