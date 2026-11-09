import { get, post } from '@/api/http';
import { clearSessionToken, writeSessionToken } from '@/api/sessionToken';

export type UserRole = 'super_admin' | 'admin' | 'user';

export interface AuthUser {
  id: number;
  username: string;
  email?: string | null;
  role: UserRole;
  dept_id?: number | null;
  is_active: boolean;
  must_change_password?: boolean;
  failed_login_count?: number;
  is_locked?: boolean;
  locked_until?: string | null;
}

export interface AuthAuditLogEntry {
  id: number;
  event_type: string;
  actor_user_id?: number | null;
  target_user_id?: number | null;
  username?: string | null;
  ip_address?: string | null;
  detail?: string | null;
  created_time?: string | null;
}

export interface CheckAuthPayload {
  success?: boolean;
  data?: {
    authenticated: boolean;
    auth_required: boolean;
    register_enabled: boolean;
    register_requires_approval?: boolean;
    password_complexity_required?: boolean;
    user: AuthUser | null;
  };
  authenticated?: boolean;
  auth_required?: boolean;
  register_enabled?: boolean;
  register_requires_approval?: boolean;
  password_complexity_required?: boolean;
  user?: AuthUser | null;
}

function unwrapCheckAuth(raw: CheckAuthPayload) {
  const data = raw.data ?? raw;
  return {
    authenticated: Boolean(data.authenticated),
    authRequired: Boolean(data.auth_required),
    registerEnabled: Boolean(data.register_enabled),
    registerRequiresApproval: data.register_requires_approval !== false,
    passwordComplexityRequired: data.password_complexity_required !== false,
    user: (data.user ?? null) as AuthUser | null
  };
}

export async function fetchCheckAuth() {
  const raw = await get<CheckAuthPayload>('/auth/check-auth');
  return unwrapCheckAuth(raw);
}

export async function login(username: string, password: string) {
  const raw = await post<{
    data?: { user?: AuthUser; session_token?: string };
    user?: AuthUser;
    session_token?: string;
  }>('/auth/login', {
    username,
    password
  });
  const data = raw.data ?? raw;
  const token = typeof data.session_token === 'string' ? data.session_token : '';
  if (token) writeSessionToken(token);
  return (data.user ?? (raw as { user: AuthUser }).user) as AuthUser;
}

export async function logout() {
  try {
    await post('/auth/logout');
  } finally {
    clearSessionToken();
  }
}

export async function registerAccount(payload: {
  username: string;
  password: string;
  email?: string;
}) {
  const raw = await post<{ data?: { pending_approval?: boolean } }>('/auth/register', payload);
  return { pendingApproval: Boolean(raw?.data?.pending_approval) };
}
