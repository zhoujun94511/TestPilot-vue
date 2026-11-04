export default {
  page: {
    title: '实验工具',
    subtitle: '选择工具并填写参数后运行，结果显示在下方'
  },
  disabled: {
    title: '实验工具暂不可用',
    message: '请在后端设置 ENABLE_EXPERIMENTAL_ACTIONS=true 后刷新本页。'
  },
  results: {
    title: '运行结果',
    empty: '选择工具并运行后，结果会显示在这里',
    clear: '清空结果',
    openCases: '在用例管理中查看',
    confirmSave: '确认入库',
    skeletonFromGaps: '用 {count} 个缺口生成骨架',
    skeletonFromGapsHint: '已切到「规则骨架预览」并带入缺口，运行后确认才会入库。'
  },
  requirements: {
    loading: '正在加载需求…',
    empty: '当前账号没有可见的需求。请先在「文档」中解析并保存需求。',
    truncated: '仅列出最近 {shown} 条需求，共 {total} 条。',
    loadFailed: '需求列表加载失败，请刷新页面重试。'
  },
  sessionPreparing: '正在准备工具会话…'
};
