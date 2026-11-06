<template>
  <Dialog :open="modelValue" @update:open="onOpenChange">
    <DialogContent class="max-w-md" :labelled-by="titleId">
      <DialogHeader>
        <DialogTitle :id="titleId">{{ t('auth.password.title') }}</DialogTitle>
        <DialogDescription>
          {{ required ? t('auth.message.passwordChangeRequired') : t('auth.password.subtitle') }}
        </DialogDescription>
      </DialogHeader>
      <form class="space-y-3" novalidate @submit.prevent="handleSubmit">
        <TpInput
          v-if="!required"
          v-model="oldPassword"
          type="password"
          :label="t('auth.password.old')"
          :error="oldPasswordError"
          autocomplete="current-password"
          required
        />
        <TpInput
          v-model="newPassword"
          type="password"
          :label="t('auth.password.new')"
          :error="newPasswordError"
          autocomplete="new-password"
          required
        />
        <TpInput
          v-if="required"
          v-model="confirmPassword"
          type="password"
          :label="t('auth.form.confirmPassword')"
          :placeholder="t('auth.form.confirmPasswordPlaceholder')"
          :error="confirmPasswordError"
          autocomplete="new-password"
          required
        />
        <p v-if="errorMessage" class="text-sm text-[var(--tp-color-danger-600)]">{{ errorMessage }}</p>
      </form>
      <DialogFooter>
        <TpButton v-if="required" variant="secondary" @click="handleLogout">
          {{ t('common.shell.logout') }}
        </TpButton>
        <TpButton v-else variant="secondary" @click="emit('update:modelValue', false)">
          {{ t('common.actions.cancel') }}
        </TpButton>
        <TpButton variant="primary" :loading="submitting" @click="handleSubmit">
          {{ t('auth.password.submit') }}
        </TpButton>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, useId, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import { changeForcedPassword, changeOwnPassword } from '@/api/users-admin';
import { useAuthStore } from '@/stores';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { isWeakPassword } from '@/utils/authCredentials';
import { isBlankField, requiredFieldMessage } from '@/lib/required-field';

const props = withDefaults(defineProps<{ modelValue: boolean; required?: boolean }>(), {
  required: false
});
const emit = defineEmits<{ 'update:modelValue': [boolean] }>();

function onOpenChange(open: boolean) {
  if (!open && props.required) return;
  emit('update:modelValue', open);
}

async function handleLogout() {
  await authStore.logout();
  emit('update:modelValue', false);
  await router.push({ name: 'login' });
}

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const titleId = useId();

const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const oldPasswordError = ref('');
const newPasswordError = ref('');
const confirmPasswordError = ref('');
const submitting = ref(false);
const errorMessage = ref('');

function clearFieldErrors() {
  oldPasswordError.value = '';
  newPasswordError.value = '';
  confirmPasswordError.value = '';
}

watch(
  () => authStore.user?.id,
  () => {
    oldPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    errorMessage.value = '';
    clearFieldErrors();
  }
);

async function handleSubmit() {
  errorMessage.value = '';
  clearFieldErrors();
  const requiredMessage = requiredFieldMessage();
  if (!props.required && isBlankField(oldPassword.value)) {
    oldPasswordError.value = requiredMessage;
  }
  if (isBlankField(newPassword.value)) {
    newPasswordError.value = requiredMessage;
  }
  if (props.required && isBlankField(confirmPassword.value)) {
    confirmPasswordError.value = requiredMessage;
  }
  if (oldPasswordError.value || newPasswordError.value || confirmPasswordError.value) {
    return;
  }
  if (props.required && newPassword.value !== confirmPassword.value) {
    errorMessage.value = t('auth.message.passwordMismatch');
    return;
  }
  if (isWeakPassword(newPassword.value, authStore.passwordComplexityRequired)) {
    errorMessage.value = t('auth.message.weakPassword');
    return;
  }
  submitting.value = true;
  try {
    if (props.required) {
      await changeForcedPassword(newPassword.value);
    } else {
      await changeOwnPassword(oldPassword.value, newPassword.value);
    }
    await authStore.logout();
    emit('update:modelValue', false);
    await router.push({ name: 'login' });
  } catch (err) {
    errorMessage.value = getUserFacingErrorMessage(err, t('auth.message.weakPassword'));
  } finally {
    submitting.value = false;
  }
}
</script>
