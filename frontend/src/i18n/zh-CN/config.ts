export default {
  toolbar: {
    backendHint: '无法加载配置分类时，请确认后端已启动并连接，然后点击侧栏或顶部的刷新。'
  },
  page: {
    title: '配置中心',
    subtitle: '管理 AI 模型、测试用例生成和系统运行参数'
  },
  category: {
    title: '配置分类',
    loading: '正在加载分类...',
    empty: '暂无可用分类',
    selectHint: '请选择一个分类查看配置',
    current: '当前分类'
  },
  panel: {
    title: '配置项',
    loading: '正在加载配置项...',
    empty: '当前分类暂无配置项',
    hint: '保存后生效'
  },
  section: {
    shared: '通用配置',
    sharedHint: '多个模型共用的配置项',
    providers: '模型分组',
    providerHint: '{provider} 专属配置',
    sharedScopeHint: '以下为通用配置；当存在按服务商区分的项时，会显示在对应分组中。',
    active: '生效中',
    tokenBudget: '单次最大词元数',
    tokenBudgetHint:
      '本区统一管理词元上限：聊天一项、用例与需求分析一项（各厂商共用同一数值）、下方为单会话累计上限。保存后生效。',
    tokenBudgetProviderHint: '用例生成与需求分析',
    tokenSessionGuard: '单会话累计上限',
    tokenSessionGuardHint: '进程内累计超过下列数值后，将拒绝继续调用模型。'
  },
  actions: {
    save: '保存',
    export: '导出',
    exporting: '导出中',
    import: '导入',
    importing: '导入中',
    reload: '重载',
    clearValue: '清空值',
    saving: '保存中'
  },
  form: {
    key: '配置键',
    value: '配置值',
    description: '说明',
    valueType: '值类型',
    updatedAt: '更新时间',
    dirty: '已修改',
    enabled: '开启',
    disabled: '关闭',
    selectPlaceholder: '请选择',
    textPlaceholder: '请输入',
    numberPlaceholder: '请输入数字',
    passwordPlaceholder: '请输入密钥',
    textareaPlaceholder: '请输入多行内容',
    dedupWeights: {
      valueType: '权重（0–1）',
      title: '标题权重',
      steps: '步骤权重',
      expected: '预期结果权重',
      preconditions: '前置条件权重'
    }
  },
  state: {
    loadingCategories: '正在加载分类列表...',
    loadingItems: '正在加载当前分类配置...',
    noCategorySelected: '请选择一个分类',
    noChanges: '',
    pendingChanges: '未保存 {count} 项',
    validationRunning: '正在校验配置'
  },
  message: {
    saved: '配置已保存',
    savedWithWarnings: '配置已保存，但部分项目未通过校验',
    saveFailed: '保存配置失败',
    loadFailed: '加载配置失败',
    exportReady: '配置已导出',
    exportFailed: '导出配置失败',
    importReady: '配置已导入 {count} 项',
    importFailed: '导入配置失败',
    validationPassed: '校验通过',
    validationFailed: '校验未通过',
    validationRequestFailed: '校验请求失败',
    noChangesToSave: '当前没有需要保存的修改',
    unsavedChangesTitle: '未保存的修改',
    unsavedChangesConfirm: '当前分类存在未保存的修改，切换分类后这些修改将丢失，是否继续？',
    apiKeyCleared: '{provider} API Key 已清空',
    apiKeyClearFailed: '清空 API Key 失败'
  },
  audit: {
    title: '最近配置变更',
    subtitle: '只读变更记录；保存或重置配置后会出现在此列表',
    navDescription: '查看保存与重置产生的变更记录',
    loading: '正在加载变更记录...',
    empty: '暂无变更记录',
    change: '旧值: {oldValue} → 新值: {newValue}'
  }
};
