/** 每个标签页各自记住当前项目，随请求头发给后端；多开标签页互不覆盖。
 * 新标签页没有自己的记录时，先沿用本机上次选中的项目，这样首屏请求不用等切换器加载。 */
export const PROJECT_HEADER = 'X-Project-Id';
const TAB_KEY = 'testpilot_current_project_id';
const SHARED_KEY = 'testpilot_last_project_id';

let scopeVersion = 0;

function parseProjectId(raw: string | null): number | null {
  const value = raw ? Number(raw) : NaN;
  return Number.isInteger(value) && value > 0 ? value : null;
}

/** 退出登录清掉项目后加一，让下一次登录重新向服务器确认当前项目 */
export function currentProjectScopeVersion(): number {
  return scopeVersion;
}

export function getTabProjectId(): number | null {
  const tab = parseProjectId(sessionStorage.getItem(TAB_KEY));
  if (tab != null) return tab;
  const shared = parseProjectId(localStorage.getItem(SHARED_KEY));
  if (shared == null) return null;
  sessionStorage.setItem(TAB_KEY, String(shared));
  return shared;
}

export function setTabProjectId(projectId: number | null) {
  if (projectId == null) {
    const hadProject = sessionStorage.getItem(TAB_KEY) != null || localStorage.getItem(SHARED_KEY) != null;
    sessionStorage.removeItem(TAB_KEY);
    localStorage.removeItem(SHARED_KEY);
    if (hadProject) scopeVersion += 1;
    return;
  }
  sessionStorage.setItem(TAB_KEY, String(projectId));
  localStorage.setItem(SHARED_KEY, String(projectId));
}

export function projectHeaders(): Record<string, string> {
  const projectId = getTabProjectId();
  return projectId == null ? {} : { [PROJECT_HEADER]: String(projectId) };
}
