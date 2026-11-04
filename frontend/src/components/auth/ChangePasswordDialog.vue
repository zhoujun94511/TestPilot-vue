<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogContent class="max-w-md" :labelled-by="titleId">
      <DialogHeader>
        <DialogTitle :id="titleId">{{ t('auth.password.title') }}</DialogTitle>
        <DialogDescription>{{ t('auth.password.subtitle') }}</DialogDescription>
      </DialogHeader>
      <form class="space-y-3" novalidate @submit.prevent="handleSubmit">
        <TpInput
          v-model="oldPassword"
          type="password"
          :label="t('auth.password.old')"
          autocomplete="current-password"
          required
        />
        <TpInput
          v-model="newPassword"
          type="password"
          :label="t('auth.password.new')"
          autocomplete="new-password"
          required
        />
        <p v-if="errorMessage" class="text-sm text-[var(--tp-color-danger-600)]">{{ errorMessage }}</p>
      </form>
      <DialogFooter>
        <TpButton variant="secondary" @click="emit('update:modelValue', false)">
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
import { changeOwnPassword } from '@/api/users-admin';
import { useAuthStore } from '@/stores';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { isWeakPassword } from '@/utils/authCredentials';
import { isBlankField, requiredFieldMessage } from '@/lib/required-field';

defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ 'update:modelValue': [boolean] }>();

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const titleId = useId();

const oldPassword = ref('');
const newPassword = ref('');
const submitting = ref(false);
const errorMessage = ref('');

watch(
  () => authStore.user?.id,
  () => {
    oldPassword.value = '';
    newPassword.value = '';
    errorMessage.value = '';
  }
);

async function handleSubmit() {
  errorMessage.value = '';
  if (isBlankField(oldPassword.value) || isBlankField(newPassword.value)) {
    errorMessage.value = requiredFieldMessage();
    return;
  }
  if (isWeakPassword(newPassword.value, authStore.passwordComplexityRequired)) {
    errorMessage.value = t('auth.message.weakPassword');
    return;
  }
  submitting.value = true;
  try {
    await changeOwnPassword(oldPassword.value, newPassword.value);
    await authStore.logout();
    emit('update:modelValue', false);
    await router.push({ name: 'login' });
  } catch (err) {
    errorMessage.value = getUserFacingErrorMessage(err, t('auth.message.weakCredentials'));
  } finally {
    submitting.value = false;
  }
}
</script>
