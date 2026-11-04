export default {
  nav: {
    users: '用户管理'
  },
  users: {
    page: {
      title: '用户管理',
      subtitle: '为本部门或全平台创建与维护账号'
    },
    tabs: {
      users: '账号',
      audit: '认证审计'
    },
    table: {
      title: '账号列表',
      username: '用户名',
      email: '邮箱',
      role: '角色',
      dept: '部门',
      active: '状态',
      lock: '锁定',
      actions: '操作',
      empty: '暂无用户'
    },
    role: {
      super_admin: '超级管理员',
      admin: '管理员',
      user: '普通用户'
    },
    status: {
      active: '启用',
      inactive: '停用',
      locked: '已锁定'
    },
    actions: {
      create: '新建用户',
      createDept: '新建部门',
      save: '保存',
      deactivate: '停用',
      activate: '启用',
      resetPassword: '重置密码',
      unlock: '解锁',
      delete: '删除',
      deleteDisabled: '至少保留一个超级管理员，不能删除'
    },
    audit: {
      title: '认证记录',
      time: '时间',
      event: '事件',
      username: '用户名',
      ip: 'IP',
      detail: '详情',
      empty: '暂无审计记录',
      details: {
        separator: '、',
        account_locked: '账户已锁定',
        account_inactive: '账号未启用',
        pending_approval: '待管理员审核启用',
        roleAssigned: '角色：{role}',
        fields: {
          is_active: '启用状态',
          email: '邮箱',
          role: '角色',
          dept_id: '部门',
          password: '密码'
        }
      },
      events: {
        login_success: '登录成功',
        login_failed: '登录失败',
        login_locked: '登录锁定',
        login_inactive: '未启用账号尝试登录',
        logout: '退出登录',
        user_registered: '自助注册',
        password_changed: '修改密码',
        user_created: '创建用户',
        user_updated: '更新用户',
        user_deleted: '删除用户',
        account_unlocked: '手动解锁'
      }
    },
    dept: {
      defaultName: '默认部门'
    },
    form: {
      createTitle: '新建账号',
      createHint:
        "标有 * 为必填。初始密码：8～128 位，且须同时包含字母、数字与符号；用户名 3～64 位，仅限字母、数字、汉字及 . _ - {'@'}。",
      deptCreateTitle: '新建部门',
      deptCreateHint: '部门编码创建后不可随意修改，请使用简短英文标识。',
      username: '用户名',
      password: '初始密码',
      email: '邮箱',
      role: '角色',
      dept: '部门',
      deptCode: '部门编码',
      deptName: '部门名称',
      deptOption: '{name}（{code}）'
    },
    hint: {
      authOff: '未开启 AUTH_REQUIRE_AUTH，账号管理 API 不可用',
      adminScope: '管理员仅可管理本部门普通用户',
      pendingApproval: '自助注册的账号默认为「停用」，确认身份后点「启用」即可登录'
    },
    delete: {
      title: '删除账号',
      message: '确定删除账号「{username}」？删除后无法登录。已生成的用例、需求和聊天记录会保留。'
    }
  }
};
