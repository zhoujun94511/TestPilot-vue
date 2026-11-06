<template>
  <div v-if="visible" class="flex min-w-0 items-center gap-2">
    <label class="sr-only" for="tp-current-project">{{ t('common.project.label') }}</label>
    <select
      id="tp-current-project"
      v-model.number="currentId"
      class="h-9 max-w-[12rem] rounded-md border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] px-2 text-sm text-foreground"
      :aria-label="t('common.project.label')"
      :title="t('common.project.manageHint')"
      @change="onSelect"
    >
      <option v-for="project in projects" :key="project.id" :value="project.id">
        {{ projectLabel(project) }}
      </option>
    </select>
    <button
      v-if="canManage"
      type="button"
      :class="topbarIconBtnClass()"
      :title="t('common.project.manage')"
      :aria-label="t('common.project.manage')"
      @click="manageOpen = true"
    >
      <FolderCog :size="18" :stroke-width="2" />
    </button>
    <p v-if="errorMessage" class="max-w-[14rem] text-xs text-[var(--tp-color-danger-600)]" role="alert">
      {{ errorMessage }}
    </p>
    <ProjectManageDialog
      v-if="canManage"
      v-model="manageOpen"
      @changed="load"
      @current-changed="reloadPage"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { FolderCog } from '@lucide/vue';
import { useI18n } from 'vue-i18n';
import { listProjects, selectProject, type ProjectRecord } from '@/api/projects';
import ProjectManageDialog from '@/components/shell/ProjectManageDialog.vue';
import { topbarIconBtnClass } from '@/lib/shell-ui';
import { isBuiltinProject } from '@/lib/builtin-labels';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { useAuthStore } from '@/stores';

const { t } = useI18n();
const authStore = useAuthStore();
const projects = ref<ProjectRecord[]>([]);
const currentId = ref<number | null>(null);
const errorMessage = ref('');
const manageOpen = ref(false);

const visible = computed(
  () => authStore.authRequired && authStore.isAuthenticated && !authStore.user?.must_change_password
);
const canManage = computed(() => authStore.hasRole('super_admin', 'admin'));

function projectLabel(project: ProjectRecord) {
  return isBuiltinProject(project) ? t('common.project.defaultName') : project.name;
}

function reloadPage() {
  window.location.reload();
}

async function load() {
  if (!visible.value) return;
  try {
    const data = await listProjects();
    projects.value = data.projects;
    currentId.value = data.currentProjectId;
  } catch (error) {
    errorMessage.value = getUserFacingErrorMessage(error, t('common.project.loadFailed'));
  }
}

async function onSelect() {
  if (currentId.value == null) return;
  errorMessage.value = '';
  try {
    await selectProject(currentId.value);
    reloadPage();
  } catch (error) {
    errorMessage.value = getUserFacingErrorMessage(error, t('common.project.notFound'));
  }
}

onMounted(() => {
  void load();
});

watch(visible, (shown) => {
  if (shown) void load();
});
</script>
