<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <DialogContent class="max-w-2xl" :labelled-by="titleId">
      <DialogHeader>
        <DialogTitle :id="titleId">{{ t('common.project.manageTitle') }}</DialogTitle>
        <DialogDescription>{{ t('common.project.manageHint') }}</DialogDescription>
      </DialogHeader>

      <form class="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end" novalidate @submit.prevent="onCreate">
        <div class="grid min-w-0 gap-3" :class="isSuperAdmin ? 'sm:grid-cols-2' : ''">
          <TpInput
            v-model="draftName"
            :label="t('common.project.create')"
            :placeholder="t('common.project.namePlaceholder')"
            :error="createError"
            maxlength="120"
            required
          />
          <TpInput
            v-if="isSuperAdmin"
            v-model="draftDeptId"
            as="select"
            :label="t('common.project.department')"
            :options="departmentOptions"
          />
        </div>
        <TpButton type="submit" variant="primary" :loading="creating" :class="createError ? 'sm:mb-6' : ''">
          {{ t('common.project.create') }}
        </TpButton>
      </form>

      <div class="max-h-[50vh] overflow-y-auto rounded-md border border-[var(--tp-border-default)]">
        <p v-if="loadError" class="p-4 text-sm text-[var(--tp-color-danger-600)]">{{ loadError }}</p>
        <p v-else-if="!projects.length" class="p-4 text-sm text-muted-foreground">{{ t('common.project.empty') }}</p>
        <ul v-else class="divide-y divide-[var(--tp-border-default)]">
          <li v-for="project in projects" :key="project.id" class="grid gap-2 p-3">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <template v-if="editingId === project.id">
                <TpInput
                  v-model="editingName"
                  bare
                  class="min-w-0 flex-1"
                  :aria-label="t('common.project.namePlaceholder')"
                  maxlength="120"
                  @keydown.enter.prevent="onRename(project)"
                />
                <TpButton size="sm" variant="primary" :loading="busyId === project.id" @click="onRename(project)">
                  {{ t('common.project.save') }}
                </TpButton>
                <TpButton size="sm" variant="secondary" @click="cancelEdit">
                  {{ t('common.actions.cancel') }}
                </TpButton>
              </template>
              <template v-else>
                <span class="min-w-0 flex-1 truncate font-semibold" :title="projectLabel(project)">
                  {{ projectLabel(project) }}
                </span>
                <TpTag v-if="project.id === currentProjectId" variant="primary">{{ t('common.project.current') }}</TpTag>
                <template v-if="!isDefault(project)">
                  <TpButton size="sm" variant="ghost" @click="startEdit(project)">
                    {{ t('common.project.rename') }}
                  </TpButton>
                  <TpButton
                    size="sm"
                    variant="ghost"
                    :disabled="hasData(project)"
                    :title="hasData(project) ? t('common.project.notEmpty') : undefined"
                    @click="pendingDeleteId = project.id"
                  >
                    {{ t('common.project.delete') }}
                  </TpButton>
                </template>
              </template>
            </div>
            <div class="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
              <span v-if="isSuperAdmin">{{ t('common.project.departmentValue', { name: departmentName(project.dept_id) }) }}</span>
              <span v-if="project.usage">{{ t('common.project.usage', project.usage) }}</span>
            </div>
            <div
              v-if="pendingDeleteId === project.id"
              class="flex flex-wrap items-center gap-2 rounded-md bg-[var(--tp-bg-subtle)] p-2 text-sm"
              role="alert"
            >
              <span class="min-w-0 flex-1">{{ t('common.project.deleteConfirm', { name: projectLabel(project) }) }}</span>
              <TpButton size="sm" variant="danger" :loading="busyId === project.id" @click="onDelete(project)">
                {{ t('common.project.delete') }}
              </TpButton>
              <TpButton size="sm" variant="secondary" @click="pendingDeleteId = null">
                {{ t('common.actions.cancel') }}
              </TpButton>
            </div>
            <p v-if="rowErrors[project.id]" class="text-xs text-[var(--tp-color-danger-600)]">{{ rowErrors[project.id] }}</p>
          </li>
        </ul>
      </div>

      <DialogFooter>
        <TpButton variant="secondary" @click="emit('update:modelValue', false)">
          {{ t('common.actions.close') }}
        </TpButton>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useId, watch } from 'vue';
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
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  createProject,
  deleteProject,
  listProjects,
  renameProject,
  type ProjectRecord
} from '@/api/projects';
import { fetchDepartments, type DepartmentRecord } from '@/api/users-admin';
import { isBuiltinDepartment, isBuiltinProject } from '@/lib/builtin-labels';
import { useToast } from '@/composables/useToast';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { useAuthStore } from '@/stores';

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{
  'update:modelValue': [boolean];
  /** 当前项目变了（新建后切过去、或删掉了当前项目），外层要重载页面数据 */
  'current-changed': [];
  /** 名称等变化，外层刷新下拉 */
  changed: [];
}>();

const { t } = useI18n();
const toast = useToast();
const authStore = useAuthStore();
const titleId = useId();

const projects = ref<ProjectRecord[]>([]);
const currentProjectId = ref<number | null>(null);
const departments = ref<DepartmentRecord[]>([]);
const loadError = ref('');
const draftName = ref('');
const draftDeptId = ref<string | number | boolean | null>(null);
const createError = ref('');
const creating = ref(false);
const editingId = ref<number | null>(null);
const editingName = ref('');
const pendingDeleteId = ref<number | null>(null);
const busyId = ref<number | null>(null);
const rowErrors = reactive<Record<number, string>>({});

const isSuperAdmin = computed(() => authStore.hasRole('super_admin'));
const departmentOptions = computed(() =>
  departments.value.map((dept) => ({ value: dept.id, label: departmentLabel(dept) }))
);

function projectLabel(project: ProjectRecord) {
  return isBuiltinProject(project) ? t('common.project.defaultName') : project.name;
}

function isDefault(project: ProjectRecord) {
  return isBuiltinProject(project);
}

function departmentLabel(dept: DepartmentRecord) {
  return isBuiltinDepartment(dept) ? t('admin.users.dept.defaultName') : dept.name;
}

function hasData(project: ProjectRecord) {
  const usage = project.usage;
  return Boolean(usage && (usage.documents || usage.requirements || usage.cases));
}

function departmentName(deptId: number) {
  const dept = departments.value.find((item) => item.id === deptId);
  return dept ? departmentLabel(dept) : String(deptId);
}

function clearRowError(projectId: number) {
  delete rowErrors[projectId];
}

async function load() {
  loadError.value = '';
  try {
    const data = await listProjects({ withUsage: true });
    projects.value = data.projects;
    currentProjectId.value = data.currentProjectId;
  } catch (error) {
    loadError.value = getUserFacingErrorMessage(error, t('common.project.loadFailed'));
  }
  if (isSuperAdmin.value && !departments.value.length) {
    try {
      departments.value = await fetchDepartments();
      const current = projects.value.find((item) => item.id === currentProjectId.value);
      draftDeptId.value = current?.dept_id ?? departments.value[0]?.id ?? null;
    } catch {
      departments.value = [];
    }
  }
}

async function onCreate() {
  const name = draftName.value.trim();
  createError.value = '';
  if (!name) {
    createError.value = t('common.project.invalidName');
    return;
  }
  creating.value = true;
  try {
    const deptId = isSuperAdmin.value && draftDeptId.value != null ? Number(draftDeptId.value) : null;
    await createProject(name, deptId);
    draftName.value = '';
    toast.success(t('common.project.created'));
    emit('current-changed');
  } catch (error) {
    createError.value = getUserFacingErrorMessage(error, t('common.project.invalidName'));
  } finally {
    creating.value = false;
  }
}

function startEdit(project: ProjectRecord) {
  pendingDeleteId.value = null;
  editingId.value = project.id;
  editingName.value = project.name;
  clearRowError(project.id);
}

function cancelEdit() {
  editingId.value = null;
  editingName.value = '';
}

async function onRename(project: ProjectRecord) {
  const name = editingName.value.trim();
  clearRowError(project.id);
  if (!name) {
    rowErrors[project.id] = t('common.project.invalidName');
    return;
  }
  busyId.value = project.id;
  try {
    await renameProject(project.id, name);
    cancelEdit();
    toast.success(t('common.project.renamed'));
    await load();
    emit('changed');
  } catch (error) {
    rowErrors[project.id] = getUserFacingErrorMessage(error, t('common.project.invalidName'));
  } finally {
    busyId.value = null;
  }
}

async function onDelete(project: ProjectRecord) {
  clearRowError(project.id);
  busyId.value = project.id;
  const wasCurrent = project.id === currentProjectId.value;
  try {
    await deleteProject(project.id);
    pendingDeleteId.value = null;
    toast.success(t('common.project.deleted'));
    if (wasCurrent) {
      emit('current-changed');
      return;
    }
    await load();
    emit('changed');
  } catch (error) {
    rowErrors[project.id] = getUserFacingErrorMessage(error, t('common.project.notFound'));
    await load();
  } finally {
    busyId.value = null;
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      cancelEdit();
      pendingDeleteId.value = null;
      createError.value = '';
      return;
    }
    void load();
  },
  { immediate: true }
);
</script>
