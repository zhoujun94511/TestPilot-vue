export default {
  page: {
    title: 'AI 对话助手',
    subtitle: '先把会话和消息链路做稳，再逐步补充增强能力'
  },
  actions: {
    newSession: '新建会话',
    refresh: '刷新',
    export: '导出记录',
    exporting: '导出中',
    send: '发送',
    sending: '发送中',
    jumpToLatest: '有 {count} 条新消息，回到底部',
    deleteSession: '删除',
    renameSession: '重命名',
    clearSession: '清空会话',
    insertTemplate: '插入模板',
    confirmAction: '确认动作',
    cancelAction: '取消动作'
  },
  sessions: {
    title: '会话列表',
    count: '{count} 个会话',
    emptyTitle: '暂无会话',
    emptyMessage: '点击“新建会话”开始新的对话',
    untitled: '未命名会话',
    defaultTitle: 'AI 对话助手',
    emptyPreview: '暂无预览',
    currentId: '当前会话',
    noSessionSelected: '尚未选择会话'
  },
  composer: {
    label: '输入消息',
    placeholder: '输入你的问题，Enter 发送，Shift+Enter 换行',
    hint: '已启用流式返回，回复会实时显示',
    streamToggle: '启用流式返回',
    smartReplyToggle: '启用智能建议',
    templateToggle: '启用提问模板',
    experimentalActionsToggle: '启用实验动作'
  },
  state: {
    loadingSessions: '正在加载会话列表...',
    loadingHistory: '正在加载历史消息...',
    emptyTitle: '暂无消息',
    emptyMessage: '选择会话或发送第一条消息开始对话',
    welcomeLead: '你好！我是你的AI测试助手，我可以帮助你解答测试相关的问题。',
    welcomePrompt: '你可以试着这么问我：',
    starters: {
      caseDesignReview: '如何开展测试用例设计和评审工作？',
      testStrategy: '如何开展测试策略制定工作？',
      defectAnalysis: '如何进行缺陷分析和定位工作？',
      automation: '如何开展自动化测试？',
      performance: '如何开展性能测试？'
    },
    thinking: 'AI 思考中...'
  },
  metrics: {
    tokens: '{count} 个 tokens'
  },
  message: {
    loadSessionsFailed: '加载会话列表失败',
    loadHistoryFailed: '加载历史消息失败',
    sendFailed: '发送消息失败',
    llmNotInitialized: '聊天模型未就绪：请在配置中心检查当前服务商与 API Key 配置后重试。',
    apiKeyInvalid: 'API Key 不可用：请在配置中心或 .env 中检查并更新后重试。',
    providerRateLimited: '模型服务请求过于频繁或配额不足，请稍后重试。',
    providerTimeout: '模型服务响应超时，请稍后重试。',
    providerNetworkError: '模型服务网络连接失败，请检查网络或服务地址。',
    sendSuccess: '消息已发送',
    newSessionReady: '新会话已创建',
    createSessionFailed: '创建会话失败',
    noHistory: '当前会话暂无历史消息',
    exportSuccess: '聊天记录导出已开始',
    exportFailed: '导出聊天记录失败',
    clearSessionConfirm: '确认清空当前会话的所有消息吗？该操作不可恢复。',
    clearSessionSuccess: '当前会话已清空',
    clearSessionFailed: '清空会话失败',
    templateInserted: '模板内容已插入输入框',
    templateEmpty: '模板为空，无法插入',
    templateLoadFailed: '加载模板失败',
    deleteSessionConfirm: '确认删除会话「{title}」吗？该操作不可恢复。',
    deleteSessionSuccess: '会话已删除',
    deleteSessionFailed: '删除会话失败',
    renameSessionSuccess: '会话已重命名',
    renameSessionFailed: '重命名会话失败',
    renameSessionEmpty: '会话名称不能为空',
    experimentalToggleSuccess: '实验动作开关已更新',
    experimentalToggleFailed: '更新实验动作开关失败'
  },
  roles: {
    user: '你',
    assistant: 'AI',
    system: '系统'
  },
  modelStatus: {
    configError: '配置错误',
    serviceUnavailable: '服务不可用',
    connectionFailed: '连接失败',
    unknownModel: '未知模型'
  },
  history: {
    title: '历史消息'
  },
  template: {
    title: '模板',
    placeholder: '模板与设置将在后续版本中补充',
    selectLabel: '提问模板',
    loading: '正在加载模板...',
    empty: '暂无模板内容',
    types: {
      testStrategy: '测试策略咨询',
      caseReview: '用例评审建议',
      bugAnalysis: '缺陷分析指导',
      automationAdvice: '自动化建议',
      performanceTest: '性能测试指导'
    }
  },
  setting: {
    title: '设置',
    placeholder: '预留给后续增强'
  },
  export: {
    title: '导出'
  },
  richContent: {
    copy: '复制',
    copied: '已复制',
    copyFailed: '复制失败',
    expand: '展开',
    collapse: '收起',
    tableHint: '表格较宽，可左右滑动查看'
  },
  messageCount: '{count} 条消息'
  ,
  quickReply: {
    title: '猜你想问',
    stats: '建议 {total} / 点击 {clicked} / 点击率 {rate}'
  },
  action: {
    pendingTitle: '待确认动作',
    executionId: '执行ID',
    plan: '动作计划',
    intent: '意图',
    tool: '工具',
    risk: '风险',
    args: '参数',
    preview: '预演结果',
    deletePreviewTitle: '即将删除对象（预演）',
    highRiskHint: '高风险动作：确认后将实际执行，请谨慎操作。',
    deleteConfirmLabel: '请输入 DELETE 进行二次确认',
    deleteConfirmPlaceholder: '输入 DELETE 后可确认',
    deleteConfirmInvalid: '请输入 DELETE 后再确认',
    deleteConfirmReady: '二次确认已通过，可执行确认',
    deleteConfirmPending: '等待二次确认（请输入 DELETE）',
    field: {
      success: '是否成功',
      message: '提示信息',
      caseId: '用例ID',
      title: '标题',
      status: '状态',
      deleted: '将删除',
      dryRun: '预演模式',
      total: '总数',
      count: '数量',
      useRag: '启用RAG'
    }
  }
};
