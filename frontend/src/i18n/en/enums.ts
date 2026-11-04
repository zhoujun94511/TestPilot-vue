export default {
  config: {
    valueType: {
      string: 'Text',
      number: 'Number',
      int: 'Integer',
      float: 'Decimal',
      json: 'JSON',
      provider: 'Provider',
      boolean: 'Switch',
      bool: 'Switch',
      password: 'Secret'
    },
    fieldKind: {
      string: 'Single-line text',
      number: 'Number',
      boolean: 'Switch',
      select: 'Dropdown',
      password: 'Secret',
      textarea: 'Multiline text'
    }
  },
  documents: {
    analysisType: {
      requirements: 'Requirement Analysis',
      test_points: 'Test Point Extraction',
      business_rules: 'Business Rule Extraction',
      comprehensive: 'Comprehensive Analysis'
    },
    status: {
      uploaded: 'Uploaded',
      analyzing: 'Analyzing',
      analyzed: 'Analyzed',
      failed: 'Failed',
      unknown: 'Unknown'
    },
    requirementStatus: {
      draft: 'Draft',
      active: 'Active',
      deprecated: 'Deprecated'
    },
    requirementType: {
      functional: 'Functional requirement',
      non_functional: 'Non-functional requirement',
      business: 'Business requirement',
      technical: 'Technical requirement',
      test_point: 'Test point',
      business_rule: 'Business rule',
      requirements: 'Requirement',
      unknown: 'Unknown'
    },
    fileType: {
      txt: 'Text',
      md: 'Markdown',
      csv: 'CSV',
      docx: 'Word',
      pdf: 'PDF',
      json: 'JSON',
      xlsx: 'Excel',
      yml: 'YAML',
      yaml: 'YAML',
      unknown: 'Unknown'
    }
  },
  cases: {
    priority: {
      P0: 'P0 - Highest priority',
      P1: 'P1 - High priority',
      P2: 'P2 - Medium priority',
      P3: 'P3 - Low priority',
      P4: 'P4 - Lowest priority'
    },
    status: {
      draft: 'Draft',
      active: 'Active',
      deprecated: 'Deprecated'
    },
    category: {
      functional: 'Functional Testing',
      performance: 'Performance Testing',
      security: 'Security Testing',
      compatibility: 'Compatibility Testing',
      usability: 'Usability Testing',
      integration: 'Integration Testing',
      regression: 'Regression Testing'
    },
    processMode: {
      sequential: 'Sequential',
      parallel: 'Parallel'
    }
  },
  stats: {
    llmUsageSource: {
      chat: 'AI Chat',
      case_generation: 'Case generation',
      document_analysis: 'Document analysis',
      agent: 'Agent',
      llm: 'Other'
    }
  }
};
