export const USERNAME_MIN_LEN = 3;
export const USERNAME_MAX_LEN = 64;
export const PASSWORD_MIN_LEN = 8;
export const PASSWORD_MAX_LEN = 128;

/** 与后端 services/auth_service.py 的 _USERNAME_PATTERN / _EMAIL_PATTERN 保持一致 */
const USERNAME_PATTERN = /^[\p{L}\p{N}_.@-]+$/u;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function isWeakUsername(username: string): boolean {
  const name = username.trim();
  if (name.length < USERNAME_MIN_LEN || name.length > USERNAME_MAX_LEN) return true;
  return !USERNAME_PATTERN.test(name);
}

export function passwordMeetsComplexity(password: string): boolean {
  if (!/[A-Za-z]/.test(password)) return false;
  if (!/\d/.test(password)) return false;
  if (!/[^A-Za-z0-9]/.test(password)) return false;
  return true;
}

/** requireComplexity 跟随后端 AUTH_PASSWORD_REQUIRE_COMPLEXITY（check-auth 下发） */
export function isWeakPassword(password: string, requireComplexity = true): boolean {
  const len = password.length;
  if (len < PASSWORD_MIN_LEN || len > PASSWORD_MAX_LEN) return true;
  return requireComplexity && !passwordMeetsComplexity(password);
}

export function credentialsMeetPolicy(
  username: string,
  password: string,
  requireComplexity = true
): boolean {
  return !isWeakUsername(username) && !isWeakPassword(password, requireComplexity);
}

export function isValidEmail(email: string): boolean {
  const text = email.trim();
  return !text || (text.length <= 255 && EMAIL_PATTERN.test(text));
}
