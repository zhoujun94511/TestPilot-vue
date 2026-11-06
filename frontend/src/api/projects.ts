import { del, get, patch, post, put } from '@/api/http';
import { setTabProjectId } from '@/lib/current-project';

export interface ProjectUsage {
  documents: number;
  requirements: number;
  cases: number;
}

export interface ProjectRecord {
  id: number;
  name: string;
  name_key?: string | null;
  dept_id: number;
  created_time?: string | null;
  usage?: ProjectUsage;
}

interface ProjectListPayload {
  data?: {
    projects?: ProjectRecord[];
    current_project_id?: number | null;
  };
  projects?: ProjectRecord[];
  current_project_id?: number | null;
}

interface ProjectPayload {
  data?: { project?: ProjectRecord; current_project_id?: number | null };
  project?: ProjectRecord;
  current_project_id?: number | null;
}

function unwrapProject(raw: ProjectPayload) {
  const data = raw.data ?? raw;
  return { project: data.project ?? null, currentProjectId: data.current_project_id ?? null };
}

/** 后端按请求头解析出的当前项目为准，同步回本标签页 */
export async function listProjects(options: { withUsage?: boolean } = {}) {
  const raw = await get<ProjectListPayload>(
    '/projects',
    options.withUsage ? { with_usage: 1 } : undefined,
    { skipProjectBootstrap: true }
  );
  const data = raw.data ?? raw;
  const currentProjectId = data.current_project_id ?? null;
  setTabProjectId(currentProjectId);
  return { projects: data.projects ?? [], currentProjectId };
}

export async function createProject(name: string, deptId?: number | null) {
  const body: Record<string, unknown> = { name };
  if (deptId != null) body.dept_id = deptId;
  const result = unwrapProject(await post<ProjectPayload>('/projects', body));
  setTabProjectId(result.currentProjectId);
  return result;
}

export async function renameProject(projectId: number, name: string) {
  return unwrapProject(await patch<ProjectPayload>(`/projects/${projectId}`, { name })).project;
}

export async function deleteProject(projectId: number) {
  const raw = await del<{ data?: { current_project_id?: number | null }; current_project_id?: number | null }>(
    `/projects/${projectId}`
  );
  const data = raw.data ?? raw;
  setTabProjectId(data.current_project_id ?? null);
  return data.current_project_id ?? null;
}

export async function selectProject(projectId: number) {
  const { currentProjectId } = unwrapProject(await put<ProjectPayload>('/projects/current', { project_id: projectId }));
  const resolved = currentProjectId ?? projectId;
  setTabProjectId(resolved);
  return resolved;
}
