export default {
  app: {
    brand: 'TestPilot',
    subtitle: '智能用例生成'
  },
  nav: {
    dashboard: '总览',
    configCenter: '配置中心',
    knowledgeBase: '知识库',
    documents: '文档',
    documentHistory: '需求历史',
    chat: 'AI 聊天',
    experimentalTools: '实验工具',
    cases: '测试用例'
  },
  shell: {
    mainNav: '主导航',
    breadcrumb: '面包屑导航',
    collapseSidebar: '收起侧边栏',
    expandSidebar: '展开侧边栏',
    openMenu: '打开菜单',
    logout: '退出登录',
    account: '个人管理',
    signedInAs: '已登录：{name}',
    closeMenu: '关闭菜单',
    switchToChinese: '切换到中文',
    switchToEnglish: 'Switch to English',
    switchToDark: 'Switch to Dark Mode',
    switchToLight: 'Switch to Light Mode',
    groups: {
      overview: '概览',
      analysis: '分析',
      generation: '生成',
      assistant: 'AI 助手',
      system: '系统'
    },
    theme: {
      light: '浅色主题',
      dark: '深色主题',
      lightShort: '浅色',
      darkShort: '深色'
    },
    system: {
      busy: '系统忙碌',
      ready: '系统就绪'
    },
    sidebarFooter: '侧栏页脚',
    sidebarCopyright: '© {yearRange} {brand} · 版权所有'
  },
  language: {
    label: '语言',
    zhCn: '简体中文',
    en: '英文',
    zhShort: '简体',
    enShort: 'EN',
    unsupportedTraditional: '当前仅支持简体中文与英文，不包含繁体中文。'
  },
  actions: {
    save: '保存',
    refresh: '刷新',
    chooseFile: '选择文件',
    upload: '上传',
    analyze: '分析',
    generate: '生成',
    loading: '加载中',
    retry: '重试',
    cancel: '取消',
    close: '关闭',
    copy: '复制内容',
    copied: '已复制',
    delete: '删除',
    edit: '编辑',
    confirm: '确认',
    expand: '查看失败详情',
    collapse: '收起详情',
    previous: '上一页',
    next: '下一页',
    more: '更多'
  },
  toolbar: {
    selectedCount: '已选 {count} 项',
    clearSelection: '取消选择',
    selectAllMatching: '选择全部 {count} 条'
  },
  pagination: {
    /** 列表工具栏 / 分页器共用的条数摘要 */
    range: '第 {start}–{end} 条，共 {total} 条'
  },
  status: {
    loading: '加载中',
    empty: '暂无数据',
    error: '加载失败',
    healthy: '健康',
    warning: '警告',
    unhealthy: '异常',
    connected: '已连接',
    disconnected: '未连接',
    noData: '暂无数据'
  },
  boolean: {
    yes: '是',
    no: '否'
  },
  feedback: {
    success: '操作成功',
    warning: '请检查输入内容',
    info: '提示'
  },
  tokenSession: {
    statusLoaded: '词元会话状态已更新',
    warningTokens:
      '词元会话用量已达 {tokenPercent}%（{tokenUsed}/{tokenMax}），接近上限 {warnPercent}%。可在配置中心调整「单会话累计词元上限」，或重启后端以重置计数。',
    warningCalls:
      '模型调用次数已达 {callPercent}%（{callUsed}/{callMax}），接近上限 {warnPercent}%。可在配置中心调整「单会话模型调用次数上限」，或重启后端以重置计数。',
    exceededTokens:
      '本服务会话累计词元已达上限（{used}/{limit}）。请在配置中心提高「单会话累计词元上限」，或重启后端服务后重试。',
    exceededCalls:
      '本服务会话模型调用次数已达上限（{used}/{limit}）。请在配置中心提高「单会话模型调用次数上限」，或重启后端服务后重试。'
  },
  project: {
    label: '当前项目',
    defaultName: '默认项目',
    create: '新建项目',
    namePlaceholder: '项目名称',
    invalidName: '项目名称无效',
    invalidDept: '部门无效',
    duplicateName: '同部门已有这个项目名称',
    required: '请选择项目',
    notFound: '项目不存在或当前账号不能进入',
    defaultLocked: '默认项目不能重命名或删除',
    notEmpty: '项目里还有文档、需求或用例，请先删除或移走',
    manage: '管理项目',
    manageTitle: '项目管理',
    manageHint: '文档、需求和用例归属项目；知识库与 AI 聊天在部门内共用，不随项目切换。',
    department: '所属部门',
    departmentValue: '所属部门：{name}',
    usage: '文档 {documents} · 需求 {requirements} · 用例 {cases}',
    current: '当前',
    rename: '重命名',
    save: '保存',
    delete: '删除',
    deleteConfirm: '确定删除项目「{name}」吗？删除后无法恢复。',
    deleted: '项目已删除',
    renamed: '项目已重命名',
    created: '项目已创建并切换过去',
    empty: '还没有项目',
    loadFailed: '项目列表加载失败'
  },
  conflict: {
    stale: '这条记录刚被别人改过，请重新打开后再保存',
    revisionRequired: '请重新打开这条记录后再保存'
  },
  errors: {
    requestFailed: '请求失败，请稍后重试',
    network: '网络异常，请检查连接或后端服务',
    http401: '未登录或会话已过期',
    http403: '没有权限执行此操作',
    http404: '请求的资源不存在',
    http408: '请求超时，请重试',
    http429: '请求过于频繁，请稍后再试',
    http4xx: '请求无法完成（{status}）',
    http5xx: '服务暂时不可用（{status}）'
  }
};
