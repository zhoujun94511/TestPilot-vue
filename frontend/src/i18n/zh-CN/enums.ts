export default {
  config: {
    valueType: {
      string: '文本',
      number: '数字',
      int: '整数',
      float: '小数',
      json: 'JSON',
      provider: '提供商',
      boolean: '开关',
      bool: '开关',
      password: '密钥'
    },
    fieldKind: {
      string: '单行文本',
      number: '数字',
      boolean: '开关',
      select: '下拉选项',
      password: '密钥',
      textarea: '多行文本'
    }
  },
  documents: {
    analysisType: {
      requirements: '需求分析',
      test_points: '测试点提取',
      business_rules: '业务规则提取',
      comprehensive: '综合分析'
    },
    status: {
      uploaded: '已上传',
      analyzing: '分析中',
      analyzed: '已分析',
      failed: '失败',
      unknown: '未知'
    },
    requirementStatus: {
      draft: '草稿',
      active: '有效',
      deprecated: '已废弃'
    },
    requirementType: {
      functional: '功能需求',
      non_functional: '非功能需求',
      business: '业务需求',
      technical: '技术需求',
      test_point: '测试点',
      business_rule: '业务规则',
      requirements: '需求',
      unknown: '未知'
    },
    fileType: {
      txt: '文本',
      md: 'Markdown',
      csv: 'CSV',
      docx: 'Word',
      pdf: 'PDF',
      json: 'JSON',
      xlsx: 'Excel',
      yml: 'YAML',
      yaml: 'YAML',
      unknown: '未知'
    }
  },
  cases: {
    priority: {
      P0: 'P0 - 最高优先级',
      P1: 'P1 - 高优先级',
      P2: 'P2 - 中优先级',
      P3: 'P3 - 低优先级',
      P4: 'P4 - 最低优先级'
    },
    status: {
      draft: '草稿',
      active: '有效',
      deprecated: '已废弃'
    },
    category: {
      functional: '功能测试',
      performance: '性能测试',
      security: '安全测试',
      compatibility: '兼容性测试',
      usability: '易用性测试',
      integration: '集成测试',
      regression: '回归测试'
    },
    processMode: {
      sequential: '顺序处理',
      parallel: '并行处理'
    }
  },
  stats: {
    llmUsageSource: {
      chat: 'AI 聊天',
      case_generation: '用例生成',
      document_analysis: '文档分析',
      agent: '智能体',
      llm: '其他'
    }
  }
};
