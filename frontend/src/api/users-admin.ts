import { del, get, post, put } from '@/api/http';
import type { AuthAuditLogEntry, AuthUser, UserRole } from '@/api/auth';

export interface DepartmentRecord {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
}

function unwrapData<T extends object>(raw: { data?: T }): T {
  if (raw && typeof raw === 'object' && 'data' in raw && raw.data !== undefined) {
    return raw.data;
  }
  return raw as unknown as T;
}

export async function fetchDepartments(): Promise<DepartmentRecord[]> {
  const raw = await get<{ data?: { departments: DepartmentRecord[] }; departments?: DepartmentRecord[] }>(
    '/auth/departments'
  );
  const data = unwrapData(raw);
  return data.departments ?? [];
}

export async function createDepartment(payload: { code: string; name: string }) {
  await post('/auth/departments', payload);
}

export async function fetchManagedUsers(): Promise<AuthUser[]> {
  const raw = await get<{ data?: { users: AuthUser[] }; users?: AuthUser[] }>('/auth/users');
  const data = unwrapData(raw);
  return data.users ?? [];
}

export async function createManagedUser(payload: {
  username: string;
  password: string;
  email?: string;
  role: UserRole;
  dept_id?: number | null;
}) {
  const raw = await post<{ data?: { user: AuthUser }; user?: AuthUser }>('/auth/users', payload);
  const data = unwrapData(raw);
  return data.user;
}

export async function updateManagedUser(
  userId: number,
  payload: Partial<{
    email: string;
    role: UserRole;
    dept_id: number;
    is_active: boolean;
    password: string;
  }>
) {
  const raw = await put<{ data?: { user: AuthUser }; user?: AuthUser }>(`/auth/users/${userId}`, payload);
  const data = unwrapData(raw);
  return data.user;
}

export async function deleteManagedUser(userId: number) {
  await del(`/auth/users/${userId}`);
}

export async function changeOwnPassword(oldPassword: string, newPassword: string) {
  await post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  });
}

export interface AuthAuditLogsPageResult {
  logs: AuthAuditLogEntry[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_prev: boolean;
    has_next: boolean;
  };
}

export async function fetchAuthAuditLogs(
  page = 1,
  perPage = 20
): Promise<AuthAuditLogsPageResult> {
  const raw = await get<{
    data?: AuthAuditLogsPageResult;
    logs?: AuthAuditLogEntry[];
    pagination?: AuthAuditLogsPageResult['pagination'];
  }>(`/auth/audit-logs?page=${page}&per_page=${perPage}`);
  const data = unwrapData(raw);
  const logs = data.logs ?? [];
  const pagination = data.pagination ?? {
    page,
    per_page: perPage,
    total: logs.length,
    pages: logs.length ? 1 : 0,
    has_prev: false,
    has_next: false
  };
  return { logs, pagination };
}

export async function unlockManagedUser(userId: number): Promise<AuthUser> {
  const raw = await post<{ data?: { user: AuthUser }; user?: AuthUser }>(
    `/auth/users/${userId}/unlock`,
    {}
  );
  const data = unwrapData(raw);
  return data.user as AuthUser;
}
