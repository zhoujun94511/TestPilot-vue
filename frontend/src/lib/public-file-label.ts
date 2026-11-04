const WINDOWS_ABS = /^[A-Za-z]:[\\/]/;
const UNC_ABS = /^\\\\/;
const UNIX_MACHINE_ABS = /^\/(?:home|Users|var|opt|tmp|usr|data|mnt|root|private|projectx)\//;
const EMBEDDED_LOCAL_PATH =
  /[A-Za-z]:[\\/][^\s"'<>|]+|\\\\[^\s"'<>|]+|\/(?:home|Users|var|opt|tmp|usr|data|mnt|root|private|projectx)\/[^\s"'<>|]+/g;

function basename(value: string) {
  const parts = value.replace(/\\/g, '/').split('/').filter(Boolean);
  return parts[parts.length - 1] || value;
}

/** 本机绝对路径只留文件名；普通文件名、相对路径和 URL 原样返回 */
export function publicFileLabel(value: string) {
  const text = value.trim();
  if (!text) return text;
  if (WINDOWS_ABS.test(text) || UNC_ABS.test(text) || UNIX_MACHINE_ABS.test(text)) {
    return basename(text);
  }
  return text;
}

/** 把句子里夹带的本机绝对路径换成文件名 */
export function redactLocalPaths(value: string) {
  return value.replace(EMBEDDED_LOCAL_PATH, (match) => basename(match));
}
