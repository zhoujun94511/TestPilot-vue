<template>
  <section class="mx-auto w-full max-w-6xl space-y-4 p-4 md:p-6">
    <PagePanel
      :title="t('admin.users.page.title')"
      :subtitle="t('admin.users.page.subtitle')"
    >
      <template #actions>
        <TpButton
          variant="secondary"
          size="sm"
          :loading="usersRefreshLoading || auditRefreshLoading"
          @click="reloadActive"
        >
          {{ t('common.actions.refresh') }}
        </TpButton>
        <TpButton
          v-if="authStore.hasRole('super_admin') && activeTab === 'users'"
          variant="ghost"
          size="sm"
          @click="showDeptForm = !showDeptForm"
        >
          {{ t('admin.users.actions.createDept') }}
        </TpButton>
      </template>

      <nav
        v-if="authStore.hasRole('super_admin')"
        :class="pageTabsNavClass"
        class="mb-4"
        role="tablist"
        :aria-label="t('admin.users.page.title')"
      >
        <button
          type="button"
          role="tab"
          :class="pageTabItemClass({ active: activeTab === 'users' })"
          :aria-selected="activeTab === 'users'"
          @click="activeTab = 'users'"
        >
          {{ t('admin.users.tabs.users') }}
        </button>
        <button
          type="button"
          role="tab"
          :class="pageTabItemClass({ active: activeTab === 'audit' })"
          :aria-selected="activeTab === 'audit'"
          @click="switchToAudit"
        >
          {{ t('admin.users.tabs.audit') }}
        </button>
      </nav>

      <template v-if="activeTab === 'users'">
        <PageNoticeBanner
          v-if="!authStore.authRequired"
          :notice="{
            type: 'warning',
            message: t('admin.users.hint.authOff')
          }"
        />
        <p v-else-if="authStore.hasRole('admin')" class="text-sm text-muted-foreground">
          {{ t('admin.users.hint.adminScope') }}
        </p>
        <p
          v-if="authStore.authRequired && authStore.registerEnabled && authStore.registerRequiresApproval"
          class="text-sm text-muted-foreground"
        >
          {{ t('admin.users.hint.pendingApproval') }}
        </p>

        <form
          v-if="showDeptForm && authStore.hasRole('super_admin')"
          :class="adminInlineFormShellClass"
          novalidate
          @submit.prevent="handleCreateDept"
        >
          <header :class="adminInlineFormHeaderClass">
            <h3 :class="sectionTitleClass">{{ t('admin.users.form.deptCreateTitle') }}</h3>
            <p :class="sectionSubtitleClass">{{ t('admin.users.form.deptCreateHint') }}</p>
          </header>
          <div :class="adminInlineFormBodyClass">
            <div :class="adminInlineFormRowClass">
              <div :class="colSpan12Md6">
                <TpInput
                  v-model="deptCode"
                  :label="t('admin.users.form.deptCode')"
                  required
                  :error="deptFieldErrors.code"
                />
              </div>
              <div :class="colSpan12Md6">
                <TpInput
                  v-model="deptName"
                  :label="t('admin.users.form.deptName')"
                  required
                  :error="deptFieldErrors.name"
                />
              </div>
            </div>
          </div>
          <div :class="formActionsClass">
            <TpButton type="button" variant="ghost" @click="showDeptForm = false">
              {{ t('common.actions.cancel') }}
            </TpButton>
            <TpButton type="submit" variant="primary" :loading="creatingDept">
              {{ t('admin.users.actions.createDept') }}
            </TpButton>
          </div>
        </form>

        <form :class="adminInlineFormShellClass" novalidate @submit.prevent="handleCreateUser">
          <header :class="adminInlineFormHeaderClass">
            <h3 :class="sectionTitleClass">{{ t('admin.users.form.createTitle') }}</h3>
            <p :class="sectionSubtitleClass">{{ t('admin.users.form.createHint') }}</p>
          </header>
          <div :class="adminInlineFormBodyClass">
            <div :class="adminInlineFormRowClass">
              <div :class="colSpan12Md4">
                <TpInput
                  v-model="form.username"
                  :label="t('admin.users.form.username')"
                  required
                  :error="createUserFieldErrors.username"
                />
              </div>
              <div :class="colSpan12Md4">
                <TpInput
                  v-model="form.password"
                  type="password"
                  :label="t('admin.users.form.password')"
                  required
                  :error="createUserFieldErrors.password"
                />
              </div>
              <div :class="colSpan12Md4">
                <TpInput v-model="form.email" :label="t('admin.users.form.email')" />
              </div>
            </div>
            <div v-if="authStore.hasRole('super_admin')" :class="adminInlineFormRowClass">
              <div :class="colSpan12Md6">
                <TpInput
                  v-model="form.role"
                  as="select"
                  :label="t('admin.users.form.role')"
                  :options="roleSelectOptions"
                />
              </div>
              <div :class="colSpan12Md6">
                <TpInput
                  v-model="form.deptId"
                  as="select"
                  :label="t('admin.users.form.dept')"
                  placeholder="—"
                  :options="deptSelectOptions"
                />
              </div>
            </div>
          </div>
          <div :class="formActionsClass">
            <TpButton
              type="submit"
              variant="primary"
              :loading="creatingUser"
              :disabled="!authStore.authRequired"
            >
              {{ t('admin.users.actions.create') }}
            </TpButton>
          </div>
        </form>

        <BaseState
          v-if="usersListLoading && !users.length"
          variant="loading"
          :title="t('common.status.loading')"
        />
        <BaseState
          v-else-if="error && !users.length"
          variant="error"
          :title="t('common.status.error')"
          :message="error"
          :retry-text="t('common.actions.retry')"
          @retry="() => reload('initial')"
        />
        <div v-else>
          <p v-if="error" class="mb-3 text-sm text-[var(--tp-color-danger-600)]">{{ error }}</p>
          <BaseTable
            :columns="userColumns"
            :data="pagedUsers"
            :loading="usersListLoading"
            keep-content-while-loading
            :loading-title="t('common.status.loading')"
            :empty-title="t('admin.users.table.empty')"
            :empty-message="''"
            row-key="id"
          >
            <template #toolbar>
              <TableToolbar :title="t('admin.users.table.title')" :pagination="usersPagination" />
            </template>
            <template #cell-username="{ row }">
              <span :class="dataTitleClass">{{ (row as AuthUser).username }}</span>
            </template>
            <template #cell-email="{ row }">
              {{ (row as AuthUser).email || '—' }}
            </template>
            <template #cell-role="{ row }">
              <TpTag variant="neutral">{{ roleLabel((row as AuthUser).role) }}</TpTag>
            </template>
            <template #cell-dept="{ row }">
              {{ deptLabel((row as AuthUser).dept_id) }}
            </template>
            <template #cell-active="{ row }">
              <TpTag :variant="(row as AuthUser).is_active ? 'primary' : 'neutral'">
                {{ (row as AuthUser).is_active ? t('admin.users.status.active') : t('admin.users.status.inactive') }}
              </TpTag>
            </template>
            <template #cell-lock="{ row }">
              <TpTag v-if="(row as AuthUser).is_locked" variant="neutral">
                {{ t('admin.users.status.locked') }}
              </TpTag>
              <span v-else class="text-muted-foreground">—</span>
            </template>
            <template #cell-actions="{ row }">
              <div class="flex flex-nowrap justify-end gap-2">
                <TpButton
                  v-if="authStore.hasRole('super_admin') && (row as AuthUser).is_locked"
                  variant="ghost"
                  size="sm"
                  :loading="unlockingId === (row as AuthUser).id"
                  @click="handleUnlock(row as AuthUser)"
                >
                  {{ t('admin.users.actions.unlock') }}
                </TpButton>
                <TpButton
                  v-if="(row as AuthUser).id !== authStore.user?.id"
                  variant="ghost"
                  size="sm"
                  @click="toggleActive(row as AuthUser)"
                >
                  {{
                    (row as AuthUser).is_active
                      ? t('admin.users.actions.deactivate')
                      : t('admin.users.actions.activate')
                  }}
                </TpButton>
                <TpButton variant="ghost" size="sm" @click="openResetPassword(row as AuthUser)">
                  {{ t('admin.users.actions.resetPassword') }}
                </TpButton>
                <TpButton
                  v-if="canDeleteUser(row as AuthUser)"
                  variant="danger"
                  size="sm"
                  @click="openDeleteUser(row as AuthUser)"
                >
                  {{ t('admin.users.actions.delete') }}
                </TpButton>
                <TpButton
                  v-else-if="isLastSuperAdmin(row as AuthUser)"
                  variant="danger"
                  size="sm"
                  disabled
                  :title="t('admin.users.actions.deleteDisabled')"
                >
                  {{ t('admin.users.actions.delete') }}
                </TpButton>
              </div>
            </template>
            <template #footer>
              <ListTablePager :pagination="usersPagination" @change="changeUsersPage" />
            </template>
          </BaseTable>
        </div>
      </template>

      <template v-else-if="activeTab === 'audit'">
        <BaseState
          v-if="auditListLoading && !auditLogs.length"
          variant="loading"
          :title="t('common.status.loading')"
        />
        <BaseState
          v-else-if="auditError && !auditLogs.length"
          variant="error"
          :title="t('common.status.error')"
          :message="auditError"
          :retry-text="t('common.actions.retry')"
          @retry="() => loadAuditLogs(1, 'initial')"
        />
        <div v-else>
          <p v-if="auditError" class="mb-3 text-sm text-[var(--tp-color-danger-600)]">{{ auditError }}</p>
          <BaseTable
            :columns="auditColumns"
            :data="auditLogs"
            :loading="auditListLoading"
            keep-content-while-loading
            :loading-title="t('common.status.loading')"
            :empty-title="t('admin.users.audit.empty')"
            :empty-message="''"
            row-key="id"
          >
            <template #toolbar>
              <TableToolbar :title="t('admin.users.audit.title')" :pagination="auditPagination" />
            </template>
            <template #cell-time="{ row }">
              <span class="whitespace-nowrap">{{ formatAuditTime((row as AuthAuditLogEntry).created_time) }}</span>
            </template>
            <template #cell-event="{ row }">
              {{ auditEventLabel((row as AuthAuditLogEntry).event_type) }}
            </template>
            <template #cell-username="{ row }">
              {{ (row as AuthAuditLogEntry).username || '—' }}
            </template>
            <template #cell-ip="{ row }">
              {{ (row as AuthAuditLogEntry).ip_address || '—' }}
            </template>
            <template #cell-detail="{ row }">
              <div class="max-w-xs truncate" :title="auditDetailLabel((row as AuthAuditLogEntry).detail)">
                {{ auditDetailLabel((row as AuthAuditLogEntry).detail) }}
              </div>
            </template>
            <template #footer>
              <ListTablePager :pagination="auditPagination" @change="changeAuditPage" />
            </template>
          </BaseTable>
        </div>
      </template>
    </PagePanel>

    <ConfirmDialog
      v-model="deleteDialogOpen"
      :title="t('admin.users.delete.title')"
      :message="t('admin.users.delete.message', { username: deleteUsername })"
      :confirm-text="t('admin.users.actions.delete')"
      :cancel-text="t('common.actions.cancel')"
      confirm-variant="danger"
      @confirm="confirmDeleteUser"
    />

    <ResetUserPasswordDialog
      v-model="resetDialogOpen"
      :user-id="resetUserId"
      :username="resetUsername"
      @success="reload"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { AuthAuditLogEntry, AuthUser, UserRole } from '@/api/auth';
import {
  createDepartment,
  createManagedUser,
  fetchAuthAuditLogs,
  fetchDepartments,
  fetchManagedUsers,
  deleteManagedUser,
  unlockManagedUser,
  updateManagedUser,
  type DepartmentRecord
} from '@/api/users-admin';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { isBlankField, requiredFieldMessage } from '@/lib/required-field';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import BaseState from '@/components/common/BaseState.vue';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import ListTablePager from '@/components/common/ListTablePager.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import { emptyListPagination } from '@/composables/usePaginatedList';
import { useListPageChange } from '@/composables/useListPageChange';
import { useListTableLoading } from '@/composables/useListTableLoading';
import type { ListFetchMode } from '@/lib/list-fetch-mode';
import { paginationRange } from '@/lib/pagination-ui';
import {
  adminInlineFormBodyClass,
  adminInlineFormHeaderClass,
  adminInlineFormRowClass,
  adminInlineFormShellClass
} from '@/lib/admin-ui';
import { formActionsClass } from '@/lib/page-chrome-ui';
import { colSpan12Md4, colSpan12Md6 } from '@/lib/page-layout-ui';
import { dataTitleClass, sectionSubtitleClass, sectionTitleClass } from '@/lib/page-typography';
import { tableCellAlignEndClass } from '@/lib/table-ui';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useAuthStore } from '@/stores';
import ResetUserPasswordDialog from '@/components/auth/ResetUserPasswordDialog.vue';
import { pageTabItemClass, pageTabsNavClass } from '@/lib/panel-ui';
import { credentialsMeetPolicy } from '@/utils/authCredentials';

const { t } = useI18n();
const authStore = useAuthStore();

type AdminTab = 'users' | 'audit';

const ADMIN_LIST_PER_PAGE = 20;

const activeTab = ref<AdminTab>('users');
const usersPagination = ref(emptyListPagination(ADMIN_LIST_PER_PAGE));
const auditPagination = ref(emptyListPagination(ADMIN_LIST_PER_PAGE));
const usersRefreshLoading = ref(false);
const auditRefreshLoading = ref(false);
const users = ref<AuthUser[]>([]);
const auditLogs = ref<AuthAuditLogEntry[]>([]);
const {
  listLoading: usersListLoading,
  beginLoad: beginUsersLoad,
  endLoad: endUsersLoad
} = useListTableLoading(users, { refreshLoading: usersRefreshLoading });
const {
  listLoading: auditListLoading,
  beginLoad: beginAuditLoad,
  endLoad: endAuditLoad
} = useListTableLoading(auditLogs, { refreshLoading: auditRefreshLoading });
const creatingUser = ref(false);
const creatingDept = ref(false);
const unlockingId = ref<number | null>(null);
const error = ref('');
const auditError = ref('');
const departments = ref<DepartmentRecord[]>([]);
const showDeptForm = ref(false);
const deptCode = ref('');
const deptName = ref('');
const deleteDialogOpen = ref(false);
const deleteUserId = ref<number | null>(null);
const deleteUsername = ref('');
const superAdminCount = computed(() => users.value.filter((item) => item.role === 'super_admin').length);

const userColumns = computed<BaseTableColumn[]>(() => {
  const columns: BaseTableColumn[] = [
    { key: 'username', label: t('admin.users.table.username') },
    { key: 'email', label: t('admin.users.table.email') },
    { key: 'role', label: t('admin.users.table.role') },
    { key: 'dept', label: t('admin.users.table.dept') },
    { key: 'active', label: t('admin.users.table.active') }
  ];
  if (authStore.hasRole('super_admin')) {
    columns.push({ key: 'lock', label: t('admin.users.table.lock') });
  }
  columns.push({
    key: 'actions',
    label: t('admin.users.table.actions'),
    headerClass: tableCellAlignEndClass,
    cellClass: tableCellAlignEndClass
  });
  return columns;
});

const auditColumns = computed<BaseTableColumn[]>(() => [
  { key: 'time', label: t('admin.users.audit.time') },
  { key: 'event', label: t('admin.users.audit.event') },
  { key: 'username', label: t('admin.users.audit.username') },
  { key: 'ip', label: t('admin.users.audit.ip') },
  { key: 'detail', label: t('admin.users.audit.detail') }
]);

function isLastSuperAdmin(row: AuthUser) {
  return row.role === 'super_admin' && superAdminCount.value <= 1;
}

function canDeleteUser(row: AuthUser) {
  return row.id !== authStore.user?.id && !isLastSuperAdmin(row);
}

const resetDialogOpen = ref(false);
const resetUserId = ref<number | null>(null);
const resetUsername = ref('');

const pagedUsers = computed(() => {
  const { page, perPage } = paginationRange(usersPagination.value);
  const start = (page - 1) * perPage;
  return users.value.slice(start, start + perPage);
});

const roleSelectOptions = computed(() => [
  { value: 'user', label: t('admin.users.role.user') },
  { value: 'admin', label: t('admin.users.role.admin') },
  { value: 'super_admin', label: t('admin.users.role.super_admin') }
]);

const deptSelectOptions = computed(() =>
  departments.value.map((dept) => ({
    value: String(dept.id),
    label: formatDeptOptionLabel(dept)
  }))
);

const form = reactive({
  username: '',
  password: '',
  email: '',
  role: 'user' as UserRole,
  deptId: ''
});

const createUserFieldErrors = reactive({ username: '', password: '' });
const deptFieldErrors = reactive({ code: '', name: '' });

function clearCreateUserFieldErrors() {
  createUserFieldErrors.username = '';
  createUserFieldErrors.password = '';
}

function clearDeptFieldErrors() {
  deptFieldErrors.code = '';
  deptFieldErrors.name = '';
}

function validateCreateUserRequired(): boolean {
  clearCreateUserFieldErrors();
  let ok = true;
  if (isBlankField(form.username)) {
    createUserFieldErrors.username = requiredFieldMessage();
    ok = false;
  }
  if (isBlankField(form.password)) {
    createUserFieldErrors.password = requiredFieldMessage();
    ok = false;
  }
  return ok;
}

function validateCreateDeptRequired(): boolean {
  clearDeptFieldErrors();
  let ok = true;
  if (isBlankField(deptCode.value)) {
    deptFieldErrors.code = requiredFieldMessage();
    ok = false;
  }
  if (isBlankField(deptName.value)) {
    deptFieldErrors.name = requiredFieldMessage();
    ok = false;
  }
  return ok;
}

watch(
  () => form.username,
  () => {
    if (createUserFieldErrors.username) createUserFieldErrors.username = '';
  }
);
watch(
  () => form.password,
  () => {
    if (createUserFieldErrors.password) createUserFieldErrors.password = '';
  }
);
watch(deptCode, () => {
  if (deptFieldErrors.code) deptFieldErrors.code = '';
});
watch(deptName, () => {
  if (deptFieldErrors.name) deptFieldErrors.name = '';
});

function roleLabel(role: UserRole) {
  return t(`admin.users.role.${role}`);
}

function resolveDeptDisplayName(dept: DepartmentRecord) {
  if (dept.code === 'default') {
    return t('admin.users.dept.defaultName');
  }
  return dept.name;
}

function formatDeptOptionLabel(dept: DepartmentRecord) {
  return t('admin.users.form.deptOption', {
    name: resolveDeptDisplayName(dept),
    code: dept.code
  });
}

function deptLabel(deptId?: number | null) {
  if (!deptId) return '—';
  const dept = departments.value.find((item) => item.id === deptId);
  return dept ? resolveDeptDisplayName(dept) : `#${deptId}`;
}

function auditEventLabel(eventType: string) {
  const key = `admin.users.audit.events.${eventType}`;
  const label = t(key);
  return label === key ? eventType : label;
}

function auditDetailLabel(detail?: string | null) {
  const raw = (detail || '').trim();
  if (!raw) return '—';
  if (raw === 'account_locked') {
    return t('admin.users.audit.details.account_locked');
  }
  if (raw === 'account_inactive') {
    return t('admin.users.audit.details.account_inactive');
  }
  if (raw === 'pending_approval') {
    return t('admin.users.audit.details.pending_approval');
  }
  const roleMatch = raw.match(/^role=(.+)$/);
  if (roleMatch) {
    const role = roleMatch[1].trim();
    const roleKey = `admin.users.role.${role}`;
    const roleLabelText = t(roleKey);
    return t('admin.users.audit.details.roleAssigned', {
      role: roleLabelText === roleKey ? role : roleLabelText
    });
  }
  return raw
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const key = `admin.users.audit.details.fields.${part}`;
      const label = t(key);
      return label === key ? part : label;
    })
    .join(t('admin.users.audit.details.separator'));
}

function formatAuditTime(iso?: string | null) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function syncUsersPagination() {
  const per_page = Number(usersPagination.value.per_page ?? ADMIN_LIST_PER_PAGE);
  const total = users.value.length;
  const pages = total ? Math.ceil(total / per_page) : 0;
  let page = Number(usersPagination.value.page ?? 1);
  if (pages && page > pages) page = pages;
  if (!pages) page = 1;
  usersPagination.value = {
    page,
    per_page,
    total,
    pages,
    has_prev: page > 1,
    has_next: Boolean(pages && page < pages)
  };
}

async function reload(mode: ListFetchMode = 'refresh') {
  beginUsersLoad(mode);
  if (mode === 'initial' || !users.value.length) {
    error.value = '';
  }
  try {
    const [userRows, deptRows] = await Promise.all([fetchManagedUsers(), fetchDepartments()]);
    users.value = userRows;
    departments.value = deptRows;
    syncUsersPagination();
    error.value = '';
  } catch (err) {
    error.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  } finally {
    endUsersLoad();
  }
}

async function loadAuditLogs(page = auditPagination.value.page ?? 1, mode: ListFetchMode = 'refresh') {
  beginAuditLoad(mode);
  if (mode === 'initial' || !auditLogs.value.length) {
    auditError.value = '';
  }
  try {
    const result = await fetchAuthAuditLogs(page, ADMIN_LIST_PER_PAGE);
    auditLogs.value = result.logs;
    auditPagination.value = result.pagination;
    auditError.value = '';
  } catch (err) {
    auditError.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  } finally {
    endAuditLoad();
  }
}

const { changePage: changeUsersPage } = useListPageChange(usersPagination, (page) => {
  const pages = Math.max(1, Number(usersPagination.value.pages || 1));
  usersPagination.value = {
    ...usersPagination.value,
    page,
    has_prev: page > 1,
    has_next: page < pages
  };
});

const { changePage: changeAuditPage } = useListPageChange(auditPagination, (page) =>
  loadAuditLogs(page, 'page')
);

function switchToAudit() {
  activeTab.value = 'audit';
  if (!auditLogs.value.length && !auditListLoading.value) {
    void loadAuditLogs(1, 'initial');
  }
}

function reloadActive() {
  if (activeTab.value === 'audit') {
    void loadAuditLogs(auditPagination.value.page ?? 1, 'refresh');
  } else {
    void reload('refresh');
  }
}

async function handleCreateUser() {
  creatingUser.value = true;
  error.value = '';
  if (!validateCreateUserRequired()) {
    creatingUser.value = false;
    return;
  }
  if (!credentialsMeetPolicy(form.username, form.password, authStore.passwordComplexityRequired)) {
    error.value = t('auth.message.weakCredentials');
    creatingUser.value = false;
    return;
  }
  try {
    await createManagedUser({
      username: form.username.trim(),
      password: form.password,
      email: form.email.trim() || undefined,
      role: authStore.hasRole('super_admin') ? form.role : 'user',
      dept_id: form.deptId ? Number(form.deptId) : authStore.user?.dept_id ?? null
    });
    form.username = '';
    form.password = '';
    form.email = '';
    await reload();
  } catch (err) {
    error.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  } finally {
    creatingUser.value = false;
  }
}

async function handleCreateDept() {
  creatingDept.value = true;
  error.value = '';
  if (!validateCreateDeptRequired()) {
    creatingDept.value = false;
    return;
  }
  try {
    await createDepartment({ code: deptCode.value.trim(), name: deptName.value.trim() });
    deptCode.value = '';
    deptName.value = '';
    showDeptForm.value = false;
    await reload();
  } catch (err) {
    error.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  } finally {
    creatingDept.value = false;
  }
}

async function toggleActive(row: AuthUser) {
  try {
    await updateManagedUser(row.id, { is_active: !row.is_active });
    await reload();
  } catch (err) {
    error.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  }
}

async function handleUnlock(row: AuthUser) {
  unlockingId.value = row.id;
  error.value = '';
  try {
    await unlockManagedUser(row.id);
    await reload();
  } catch (err) {
    error.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  } finally {
    unlockingId.value = null;
  }
}

function openResetPassword(row: AuthUser) {
  resetUserId.value = row.id;
  resetUsername.value = row.username;
  resetDialogOpen.value = true;
}

function openDeleteUser(row: AuthUser) {
  deleteUserId.value = row.id;
  deleteUsername.value = row.username;
  deleteDialogOpen.value = true;
}

async function confirmDeleteUser() {
  const userId = deleteUserId.value;
  deleteDialogOpen.value = false;
  if (userId == null) return;
  error.value = '';
  try {
    await deleteManagedUser(userId);
    await reload();
  } catch (err) {
    error.value = getUserFacingErrorMessage(err, t('common.errors.requestFailed'));
  }
}

onMounted(() => {
  void reload('initial');
});
</script>
