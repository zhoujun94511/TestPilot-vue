const STORAGE_KEY = 'testpilot_session_token';

function storage(): Storage | null {
  try {
    return sessionStorage;
  } catch {
    return null;
  }
}

export function readSessionToken(): string {
  try {
    return storage()?.getItem(STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

export function writeSessionToken(token: string): void {
  try {
    const box = storage();
    if (!box) return;
    if (!token) {
      box.removeItem(STORAGE_KEY);
      return;
    }
    box.setItem(STORAGE_KEY, token);
  } catch {
    // sessionStorage 不可用时静默失败，同源 cookie 仍能登录
  }
}

export function clearSessionToken(): void {
  try {
    storage()?.removeItem(STORAGE_KEY);
  } catch {
    // 同源 cookie 仍能工作
  }
}

export function authorizationHeader(): Record<string, string> {
  const token = readSessionToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
