<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogContent class="max-w-md" :labelled-by="titleId">
      <DialogHeader>
        <DialogTitle :id="titleId">{{ t('admin.users.actions.resetPassword') }}</DialogTitle>
        <DialogDescription v-if="username">{{ username }}</DialogDescription>
      </DialogHeader>
      <div class="space-y-3">
        <TpInput
          v-model="password"
          type="password"
          :label="t('admin.users.form.password')"
          autocomplete="new-password"
          required
        />
        <p v-if="errorMessage" class="text-sm text-[var(--tp-color-danger-600)]">{{ errorMessage }}</p>
      </div>
      <DialogFooter>
        <TpButton variant="secondary" @click="emit('update:modelValue', false)">
          {{ t('common.actions.cancel') }}
        </TpButton>
        <TpButton variant="primary" :loading="submitting" @click="handleSubmit">
          {{ t('admin.users.actions.save') }}
        </TpButton>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, useId, watch } from 'vue';
import { useI18n } from 'vue-i18n';
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
import { updateManagedUser } from '@/api/users-admin';
import { isWeakPassword } from '@/utils/authCredentials';
import { useAuthStore } from '@/stores';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { isBlankField, requiredFieldMessage } from '@/lib/required-field';

const props = defineProps<{
  modelValue: boolean;
  userId: number | null;
  username?: string;
}>();
const emit = defineEmits<{ 'update:modelValue': [boolean]; success: [] }>();

const { t } = useI18n();
const authStore = useAuthStore();
const titleId = useId();
const password = ref('');
const submitting = ref(false);
const errorMessage = ref('');

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    password.value = '';
    errorMessage.value = '';
  }
);

async function handleSubmit() {
  if (!props.userId) return;
  if (isBlankField(password.value)) {
    errorMessage.value = requiredFieldMessage();
    return;
  }
  if (isWeakPassword(password.value, authStore.passwordComplexityRequired)) {
    errorMessage.value = t('auth.message.weakPassword');
    return;
  }
  submitting.value = true;
  errorMessage.value = '';
  try {
    await updateManagedUser(props.userId, { password: password.value });
    emit('success');
    emit('update:modelValue', false);
  } catch (err) {
    errorMessage.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  } finally {
    submitting.value = false;
  }
}
</script>
