/** 库里的内置名称固定是中文。界面语言可能是英文，展示必须走文案键，不能直接渲染 name。 */

export function isBuiltinProject(project: { name: string; name_key?: string | null }) {
  return project.name_key === 'common.project.defaultName' || project.name === '默认项目';
}

export function isBuiltinDepartment(dept: { name: string; code?: string; name_key?: string | null }) {
  return dept.code === 'default' || dept.name_key === 'admin.users.dept.defaultName' || dept.name === '默认部门';
}
