<template>
  <div class="tp-auth-screen">
    <div class="tp-auth-toolbar">
      <LanguageSwitcher />
      <button
        type="button"
        class="tp-auth-icon-btn"
        :title="themeToggleTitle"
        :aria-label="themeToggleTitle"
        @click="toggleTheme"
      >
        <Sun v-if="appStore.theme === 'dark'" :size="18" :stroke-width="2" />
        <Moon v-else :size="18" :stroke-width="2" />
      </button>
    </div>

    <div class="tp-auth-card">
      <div class="tp-auth-brand" :class="{ 'is-solo': !showRegisterTab }">
        <span class="tp-auth-logo-wrap">
          <BrandMark size="lg" />
        </span>
        <h1>{{ t('common.app.brand') }}</h1>
        <p class="tp-auth-subtitle">{{ t('auth.page.subtitle') }}</p>
      </div>

      <div v-if="showRegisterTab" class="tp-auth-tabs">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">
          {{ t('auth.form.tabLogin') }}
        </button>
        <button
          type="button"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          {{ t('auth.form.tabRegister') }}
        </button>
      </div>

      <form class="tp-auth-form" novalidate @submit.prevent="handleSubmit">
        <label>
          <span :id="`${fieldId}-username`">{{ t('auth.form.username') }}</span>
          <input
            v-model.trim="username"
            type="text"
            name="username"
            autocomplete="username"
            :aria-labelledby="`${fieldId}-username`"
            :aria-invalid="showUsernameRule || undefined"
            :aria-describedby="showUsernameRule ? `${fieldId}-username-hint` : undefined"
            :placeholder="t('auth.form.usernamePlaceholder')"
          />
          <small
            v-if="showUsernameRule"
            :id="`${fieldId}-username-hint`"
            class="tp-auth-hint"
            role="alert"
          >
            {{ t('auth.form.usernameRule') }}
          </small>
        </label>

        <label v-if="mode === 'register'">
          <span>{{ t('auth.form.email') }}</span>
          <input
            v-model.trim="email"
            type="email"
            name="email"
            autocomplete="email"
            :placeholder="t('auth.form.emailPlaceholder')"
          />
        </label>

        <label>
          <span :id="`${fieldId}-password`">{{ t('auth.form.password') }}</span>
          <span class="tp-auth-password">
            <input
              v-model="password"
              :type="passwordVisible ? 'text' : 'password'"
              name="password"
              :aria-labelledby="`${fieldId}-password`"
              :aria-invalid="showPasswordRule || undefined"
              :aria-describedby="showPasswordRule ? `${fieldId}-password-hint` : undefined"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              :placeholder="t('auth.form.passwordPlaceholder')"
            />
            <button
              type="button"
              class="tp-auth-password-toggle"
              :aria-pressed="passwordVisible"
              :aria-label="passwordVisible ? t('auth.form.hidePassword') : t('auth.form.showPassword')"
              :title="passwordVisible ? t('auth.form.hidePassword') : t('auth.form.showPassword')"
              @click="passwordVisible = !passwordVisible"
            >
              <EyeOff v-if="passwordVisible" :size="16" :stroke-width="2" />
              <Eye v-else :size="16" :stroke-width="2" />
            </button>
          </span>
          <small
            v-if="showPasswordRule"
            :id="`${fieldId}-password-hint`"
            class="tp-auth-hint"
            role="alert"
          >
            {{ passwordRuleText }}
          </small>
        </label>

        <label v-if="mode === 'register'">
          <span :id="`${fieldId}-confirm-password`">{{ t('auth.form.confirmPassword') }}</span>
          <span class="tp-auth-password">
            <input
              v-model="confirmPassword"
              :type="confirmPasswordVisible ? 'text' : 'password'"
              name="confirm-password"
              :aria-labelledby="`${fieldId}-confirm-password`"
              autocomplete="new-password"
              :placeholder="t('auth.form.confirmPasswordPlaceholder')"
            />
            <button
              type="button"
              class="tp-auth-password-toggle"
              :aria-pressed="confirmPasswordVisible"
              :aria-label="confirmPasswordVisible ? t('auth.form.hidePassword') : t('auth.form.showPassword')"
              :title="confirmPasswordVisible ? t('auth.form.hidePassword') : t('auth.form.showPassword')"
              @click="confirmPasswordVisible = !confirmPasswordVisible"
            >
              <EyeOff v-if="confirmPasswordVisible" :size="16" :stroke-width="2" />
              <Eye v-else :size="16" :stroke-width="2" />
            </button>
          </span>
        </label>

        <p v-if="errorMessage" class="tp-auth-error" role="alert">{{ errorMessage }}</p>
        <p v-if="noticeMessage" class="tp-auth-notice" role="status">{{ noticeMessage }}</p>

        <button class="tp-auth-submit" type="submit" :disabled="submitting || rateLeft > 0">
          <TpSpinner v-if="submitting" size="sm" />
          <span>{{
            submitting ? t('auth.form.working') : mode === 'register'
              ? t('auth.form.submitRegister')
              : t('auth.form.submitLogin')
          }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useId } from 'vue';
import { Eye, EyeOff, Moon, Sun } from '@lucide/vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import BrandMark from '@/components/brand/BrandMark.vue';
import TpSpinner from '@/components/ui/base/TpSpinner.vue';
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue';
import { registerAccount } from '@/api/auth';
import { ApiError } from '@/api/http';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { useAppStore, useAuthStore } from '@/stores';
import { isValidEmail, isWeakPassword, isWeakUsername } from '@/utils/authCredentials';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const appStore = useAppStore();

const fieldId = useId();
const username = ref('');
const password = ref('');
const passwordVisible = ref(false);
const confirmPassword = ref('');
const confirmPasswordVisible = ref(false);
const email = ref('');
const mode = ref<'login' | 'register'>('login');
const submitting = ref(false);
const errorMessage = ref('');
const noticeMessage = ref('');

const rateLeft = ref(0);
let rateTimer: ReturnType<typeof setInterval> | null = null;

const showRegisterTab = computed(() => authStore.registerEnabled);
const passwordRuleText = computed(() =>
  authStore.passwordComplexityRequired ? t('auth.form.passwordRule') : t('auth.form.passwordRuleSimple')
);
const showUsernameRule = computed(
  () => mode.value === 'register' && username.value.trim().length > 0 && isWeakUsername(username.value)
);
const showPasswordRule = computed(
  () =>
    mode.value === 'register' &&
    password.value.length > 0 &&
    isWeakPassword(password.value, authStore.passwordComplexityRequired)
);

const themeToggleTitle = computed(() =>
  appStore.theme === 'dark' ? t('common.shell.switchToLight') : t('common.shell.switchToDark')
);

function toggleTheme() {
  appStore.setTheme(appStore.theme === 'dark' ? 'light' : 'dark');
}

function clearRateLimit() {
  if (rateTimer) clearInterval(rateTimer);
  rateTimer = null;
  rateLeft.value = 0;
}

function startRateLimit(seconds: number, messageKey: string) {
  clearRateLimit();
  rateLeft.value = Math.max(1, Math.ceil(Number(seconds) || 60));
  errorMessage.value = t(messageKey, { seconds: rateLeft.value });
  rateTimer = setInterval(() => {
    rateLeft.value -= 1;
    if (rateLeft.value <= 0) {
      clearRateLimit();
      errorMessage.value = '';
    } else {
      errorMessage.value = t(messageKey, { seconds: rateLeft.value });
    }
  }, 1000);
}

function registerValidationError(): string {
  if (isWeakUsername(username.value)) return t('auth.message.weakCredentials');
  if (isWeakPassword(password.value, authStore.passwordComplexityRequired)) {
    return t('auth.message.weakPassword');
  }
  if (password.value !== confirmPassword.value) return t('auth.message.passwordMismatch');
  if (!isValidEmail(email.value)) return t('auth.message.invalidEmail');
  return '';
}

function switchMode(next: 'login' | 'register') {
  mode.value = next;
  passwordVisible.value = false;
  confirmPasswordVisible.value = false;
  confirmPassword.value = '';
  noticeMessage.value = '';
  if (rateLeft.value <= 0) errorMessage.value = '';
}

async function handleSubmit() {
  if (rateLeft.value > 0) return;
  errorMessage.value = '';
  noticeMessage.value = '';

  if (!username.value.trim() || !password.value) {
    errorMessage.value = t('auth.form.fillAllFields');
    return;
  }

  submitting.value = true;
  try {
    if (mode.value === 'register') {
      if (showUsernameRule.value || showPasswordRule.value) return;
      const invalid = registerValidationError();
      if (invalid) {
        errorMessage.value = invalid;
        return;
      }
      const { pendingApproval } = await registerAccount({
        username: username.value.trim(),
        password: password.value,
        email: email.value.trim() || undefined
      });
      mode.value = 'login';
      password.value = '';
      confirmPassword.value = '';
      passwordVisible.value = false;
      confirmPasswordVisible.value = false;
      noticeMessage.value = pendingApproval
        ? t('auth.message.registerPending')
        : t('auth.message.registerOk');
      return;
    }

    await authStore.login(username.value.trim(), password.value);
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
    await router.replace(redirect || '/');
  } catch (error) {
    if (error instanceof ApiError && error.code === 429) {
      const detailSeconds =
        typeof error.details === 'object' &&
        error.details !== null &&
        'seconds' in error.details
          ? Number((error.details as { seconds?: number }).seconds)
          : 60;
      startRateLimit(
        detailSeconds,
        mode.value === 'register' ? 'auth.message.registerRateLimited' : 'auth.message.loginRateLimited'
      );
      return;
    }
    errorMessage.value = getUserFacingErrorMessage(error, t('auth.message.invalidCredentials'));
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  if (!authStore.bootstrapped) {
    await authStore.bootstrap();
  }
  if (!authStore.registerEnabled && mode.value === 'register') {
    mode.value = 'login';
  }
  if (route.query.expired === '1') {
    noticeMessage.value = t('auth.message.sessionExpired');
  }
});

onUnmounted(clearRateLimit);
</script>

<style scoped>
.tp-auth-screen {
  position: relative;
  box-sizing: border-box;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  padding-top: max(24px, env(safe-area-inset-top, 0px));
  background: var(--tp-bg-page);
  color: var(--tp-color-text-900);
  overflow: hidden;
}

.tp-auth-screen::before,
.tp-auth-screen::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  background: var(--tp-color-primary-600);
  filter: blur(90px);
  opacity: 0.18;
  pointer-events: none;
  z-index: 0;
}

.tp-auth-screen::before {
  width: 380px;
  height: 380px;
  top: -130px;
  left: -110px;
}

.tp-auth-screen::after {
  width: 320px;
  height: 320px;
  right: -110px;
  bottom: -130px;
}

.tp-auth-toolbar {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 10px;
}

.tp-auth-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md, 10px);
  background: var(--tp-bg-surface);
  color: var(--tp-color-text-600);
  cursor: pointer;
}

.tp-auth-icon-btn:hover {
  color: var(--tp-color-text-900);
  border-color: color-mix(in srgb, var(--tp-color-primary-600) 35%, var(--tp-border-default));
}

.tp-auth-card {
  position: relative;
  z-index: 1;
  width: min(420px, 100%);
  max-width: 100%;
  min-width: 0;
  margin-top: -2.5vh;
  background: var(--tp-bg-surface);
  border: 1px solid var(--tp-border-default);
  border-radius: 16px;
  box-shadow: var(--tp-shadow-md, 0 12px 40px rgba(15, 23, 42, 0.08));
  padding: 28px 32px 32px;
}

.tp-auth-brand {
  text-align: center;
  margin-bottom: 16px;
}

.tp-auth-brand.is-solo {
  margin-bottom: 28px;
}

.tp-auth-brand .tp-auth-logo-wrap {
  display: flex;
  box-sizing: border-box;
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  align-items: center;
  justify-content: center;
}

.tp-auth-brand .tp-auth-logo-wrap img {
  box-sizing: border-box;
  width: 56px;
  height: 56px;
  margin: 0;
  padding: 6px;
}

.tp-auth-brand h1 {
  font-size: 1.25rem;
  margin: 0 0 6px;
  font-weight: 600;
  color: var(--tp-color-text-900);
}

.tp-auth-subtitle {
  margin: 0;
  font-size: 0.85rem;
  color: var(--tp-color-text-500);
}

.tp-auth-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 22px;
  padding: 4px;
  background: var(--tp-bg-subtle);
  border: 1px solid var(--tp-border-default);
  border-radius: 12px;
}

.tp-auth-tabs button {
  flex: 1;
  padding: 8px 10px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: var(--tp-color-text-500);
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: background 0.15s ease, color 0.15s ease;
}

.tp-auth-tabs button:hover:not(.active) {
  color: var(--tp-color-text-800);
}

.tp-auth-tabs button.active {
  background: color-mix(in srgb, var(--tp-color-primary-600) 16%, transparent);
  color: var(--tp-color-text-900);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--tp-color-primary-600) 38%, transparent);
}

.tp-auth-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  max-width: 100%;
}

.tp-auth-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  font-size: 0.8rem;
  color: var(--tp-color-text-500);
}

.tp-auth-hint {
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--tp-color-danger-700);
}

.tp-auth-form input {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--tp-border-default);
  border-radius: 10px;
  background: var(--tp-bg-subtle);
  color: var(--tp-color-text-900);
  font-size: 0.95rem;
}

.tp-auth-password {
  position: relative;
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.tp-auth-password input {
  padding-right: 40px;
}

.tp-auth-password input::-ms-reveal,
.tp-auth-password input::-ms-clear {
  display: none;
}

.tp-auth-password-toggle {
  position: absolute;
  top: 50%;
  right: 4px;
  display: inline-flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--tp-color-text-500);
  cursor: pointer;
  transform: translateY(-50%);
}

.tp-auth-password-toggle:hover {
  background: color-mix(in srgb, var(--tp-bg-surface) 70%, transparent);
  color: var(--tp-color-text-900);
}

.tp-auth-password-toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--tp-color-primary-600) 45%, transparent);
}

.tp-auth-form input:focus {
  outline: none;
  border-color: var(--tp-color-primary-600);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tp-color-primary-600) 28%, transparent);
}

.tp-auth-submit {
  margin-top: 6px;
  padding: 11px;
  border: none;
  border-radius: 10px;
  background: var(--tp-color-primary-600);
  color: var(--tp-color-text-inverse);
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.tp-auth-submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.tp-auth-error {
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--tp-color-danger-600) 12%, transparent);
  color: var(--tp-color-danger-700);
  border: 1px solid color-mix(in srgb, var(--tp-color-danger-600) 32%, transparent);
  font-size: 0.82rem;
  text-align: center;
}

.tp-auth-notice {
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--tp-color-success-600) 12%, transparent);
  color: var(--tp-notice-success-fg-emphasis);
  border: 1px solid color-mix(in srgb, var(--tp-color-success-600) 32%, transparent);
  font-size: 0.82rem;
  text-align: center;
}

:root[data-theme='light'] .tp-auth-error,
html:not(.dark) .tp-auth-error {
  background: var(--tp-notice-danger-bg);
  color: var(--tp-notice-danger-fg-emphasis);
  border-color: color-mix(in srgb, var(--tp-color-danger-600) 28%, transparent);
}

:root[data-theme='light'] .tp-auth-notice,
html:not(.dark) .tp-auth-notice {
  background: var(--tp-notice-success-bg);
  color: var(--tp-notice-success-fg-emphasis);
  border-color: color-mix(in srgb, var(--tp-color-success-600) 28%, transparent);
}
</style>
