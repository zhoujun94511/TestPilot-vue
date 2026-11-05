# 配置说明

环境变量、向量库、检索和模型接入。安装与登录见 [操作文档](OPERATIONS.md)。

## 配置说明

### 配置管理

TestPilot 支持两种配置方式：

#### 1. 环境变量配置（.env文件）

主要的环境变量配置项：

```bash
# Flask应用配置
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key

# 数据库配置
DATABASE_URL=sqlite:///testpilot.db

# AI模型配置
OPENAI_API_KEY=your-openai-key
DEFAULT_COMPANY=OPENAI  # 默认使用的AI提供商（统一使用大写）

# 文件上传配置
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads

# ===========================================
# 向量存储配置（新增）
# ===========================================

# 向量库总开关（默认 true）。设为 false 时不加载 sqlite-vec/FTS5，无对应库也可运行，便于 PyInstaller 等打包缩减体积；知识库与 RAG 功能不可用
ENABLE_VECTOR_STORE=true

# 向量存储后端（默认 sqlite，历史上支持 sqlite/chroma，当前推荐仅使用 sqlite）
VECTOR_BACKEND=sqlite  # 不建议再使用 chroma，ChromaDB 逻辑已废弃，仅老版本回滚时使用

# SQLite 向量存储配置
SQLITE_VECTOR_DB_PATH=  # 如果为空，使用 vector_store/vector_store.db
SQLITE_VEC_EXTENSION_PATH=  # sqlite-vec 扩展路径（可选）

# Embedding 模型配置（FastEmbed）
EMBEDDING_MODEL_NAME=baai/bge-small-en-v1.5  # FastEmbed 模型名称
EMBEDDING_DIM=384  # 重要：维度一旦确定，不允许再变更（sqlite-vec 要求）
FASTEMBED_CACHE_DIR=  # FastEmbed 模型缓存目录（可选，默认 ~/.cache/fastembed）

# 混合检索配置（FTS5 + sqlite-vec）
ENABLE_HYBRID_RETRIEVAL=true  # 是否启用混合检索
FTS_CANDIDATE_FACTOR=40  # 自适应候选因子（默认 40，对应 topK × 40）
MAX_FTS_CANDIDATE_K=800  # FTS5 候选数量上限（安全上限，避免 SQLite IN 参数问题）
FTS_CANDIDATE_K=200  # FTS5 召回候选数量（已废弃，保留用于向后兼容）
# 自适应策略说明：
# - 基础公式：fts_candidate_k = min(topK × FTS_CANDIDATE_FACTOR, MAX_FTS_CANDIDATE_K)
# - Query 复杂度调节：简单查询（token ≤ 2）扩大召回，复杂查询（token ≥ 8）缩小召回
# - 示例：
#   - topK=5, 中等查询 → 5 × 40 = 200
#   - topK=5, 简单查询 → 5 × 80 = 400
#   - topK=10, 复杂查询 → 10 × 20 = 200

# ChromaDB配置（仅老版本回滚兼容使用，正常情况下可忽略）
# 仅当 VECTOR_BACKEND=chroma 且需要回滚到旧版 ChromaDB 存储时才需要关注
CHROMADB_PERSIST_DIRECTORY=vector_store

# RAG检索配置
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.7
RAG_ENABLE_KEYWORD_FILTER=true

# 智能检索配置
ENABLE_SMART_RETRIEVAL=true
RETRIEVAL_STRATEGY=hybrid  # semantic, keyword, hybrid, context_aware

# 幻觉检测配置
ENABLE_HALLUCINATION_DETECTION=true
HALLUCINATION_SIMILARITY_THRESHOLD=0.8
HALLUCINATION_CONFIDENCE_THRESHOLD=0.7
HALLUCINATION_WARN_THRESHOLD=0.3
HALLUCINATION_AUTO_CORRECT_THRESHOLD=0.5
HALLUCINATION_REGENERATE_THRESHOLD=0.7
HALLUCINATION_FILTER_THRESHOLD=0.9

# 实验动作编排（默认开启；不需要时设为 false）
ENABLE_EXPERIMENTAL_ACTIONS=true
```

详细配置请参考 `.env.example` 文件。

### 向量存储配置矩阵

| 配置键                         | 默认值                            | 影响              | 说明                                                                                         |
|-----------------------------|--------------------------------|-----------------|--------------------------------------------------------------------------------------------|
| `ENABLE_VECTOR_STORE`       | `true`                         | 向量库总开关          | `false`：不加载 sqlite-vec/FTS5，无对应库也可运行；知识库与 RAG 不可用。**打包（如 PyInstaller）时可设为 `false` 以缩减体积**  |
| `VECTOR_BACKEND`            | `sqlite`                       | 向量存储后端          | `sqlite`：使用 SQLite + sqlite-vec（当前默认且推荐）<br>`chroma`：使用 ChromaDB（**已废弃，不推荐使用，仅老版本回滚场景保留**） |
| `EMBEDDING_MODEL_NAME`      | `baai/bge-small-en-v1.5`       | Embedding 模型    | FastEmbed 模型名称，必须与 `EMBEDDING_DIM` 一致                                                      |
| `EMBEDDING_DIM`             | `384`                          | Embedding 维度    | **重要**：维度一旦确定，不允许再变更（sqlite-vec 要求）<br>变更维度需要重建向量库                                         |
| `FASTEMBED_CACHE_DIR`       | `~/.cache/fastembed`           | 模型缓存目录          | 离线部署时，可指定自定义缓存目录                                                                           |
| `SQLITE_VECTOR_DB_PATH`     | `vector_store/vector_store.db` | SQLite 数据库路径    | 如果为空，使用默认路径                                                                                |
| `SQLITE_VEC_EXTENSION_PATH` | `''`                           | sqlite-vec 扩展路径 | 可选，未设置时自动尝试从常见位置加载                                                                         |
| `ENABLE_HYBRID_RETRIEVAL`   | `true`                         | 混合检索开关          | `true`：启用 FTS5 + sqlite-vec 混合检索<br>`false`：仅使用纯向量检索                                       |
| `FTS_CANDIDATE_FACTOR`      | `40`                           | 自适应候选因子         | 基础因子，用于计算 `fts_candidate_k = topK × factor`<br>会根据 query 复杂度自动调整（简单查询 ×2，复杂查询 ÷2）          |
| `MAX_FTS_CANDIDATE_K`       | `800`                          | FTS5 候选数量上限     | 安全上限，避免 SQLite IN 参数问题                                                                     |
| `FTS_CANDIDATE_K`           | `200`                          | FTS5 候选数量（已废弃）  | 保留用于向后兼容，实际使用自适应策略                                                                         |

### 实验动作编排说明（低耦合、可拆卸）

- 默认可用：只有显式设置 `ENABLE_EXPERIMENTAL_ACTIONS=false` 时实验接口才返回 403；普通 Chat 模式不受影响
- 独立模块：实现位于 `experiments/action_runtime`，不侵入核心业务服务
- 安全机制：
  - 会写入库的动作先预览，确认时按已保存的预览入库，不重新调用模型
  - 确认限于发起人或管理员
  - 实验接口带轻量限流保护（每 60 秒最多 12 次/调用方）
- 审计追踪：所有动作写入 `tool_execution_logs`，可按 `execution_id` 查询详情

### 检索模式说明

#### 1. 纯向量检索

**配置**：`ENABLE_HYBRID_RETRIEVAL=false`

**流程**：
- 直接使用 sqlite-vec 对全量数据进行向量相似度搜索
- 返回 topK 个最相似的文档

**适用场景**：
- 数据量较小（< 10万条）
- 关键词匹配不重要的场景

#### 2. 混合检索（FTS5 + sqlite-vec）

**配置**：`ENABLE_HYBRID_RETRIEVAL=true`（默认）

**流程**：
1. **第一阶段**：FTS5 关键词召回候选集（自适应候选数量，根据 topK 和 query 复杂度动态计算）
2. **第二阶段**：sqlite-vec 对候选集做向量精排，返回 topK 个

**优势**：
- 关键词召回：快速过滤不相关文档
- 向量精排：只计算候选集的相似度，性能优于纯向量（数据量增长时）

**适用场景**：
- 数据量较大（> 10万条）
- 需要关键词匹配的场景

#### 3. Fallback 行为

**自动降级机制**（可预期）：
- sqlite-vec 扩展不可用 → 自动降级到全表扫描（纯 Python 计算）
- FTS5 不可用 → 自动降级到纯向量检索
- FTS5 返回为空 → 自动降级到纯向量检索
- 所有 fallback 都有 `warning` 日志记录，不 silent fail

**验证 fallback**：
```bash
# 查看日志，确认 fallback 状态
grep "降级\|fallback\|warning" logs/testpilot_*.log
```

#### 2. 配置中心（Web界面）

TestPilot 提供了可视化的配置中心，支持：

- **统一管理**：通过 Web 界面管理所有配置项
- **分类组织**：按功能模块分类；**最近配置变更** 为独立侧栏项
- **实时生效**：保存后即时生效（词元等触发热重载）
- **审计日志**：`GET /api/config/audit-logs`，配置中心内只读浏览
- **配置验证**：自动验证格式与必填项
- **词元分区**：AI 模型设置 → **单次最大词元数**（详见 TOKEN-CONFIG.md）

**配置优先级**：配置中心 > `.env` > 默认值

**文档**：[CONFIG-CENTER.md](CONFIG-CENTER.md)、词元说明 [TOKEN-CONFIG.md](../frontend/docs/TOKEN-CONFIG.md)

首次初始化会写入缺省配置并记下游标，见 [操作文档](OPERATIONS.md)。`python scripts/init_config_center.py --force` 会清空后恢复内置默认（`DEFAULT_COMPANY=OPENAI`），只在确认要出厂重置时使用。

### AI模型配置

TestPilot支持多种AI模型，配置示例：

```bash
# OpenAI
DEFAULT_COMPANY=OPENAI
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-5

# Google Gemini
DEFAULT_COMPANY=GEMINI
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash

# DeepSeek
DEFAULT_COMPANY=DEEPSEEK
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL=deepseek-flash

# Qwen
DEFAULT_COMPANY=QWEN
QWEN_API_KEY=your-qwen-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-flash
QWEN_TEMPERATURE=0.7
QWEN_TIMEOUT=60

# Anthropic / Claude
# 走 Messages API，不走 OpenAI 兼容地址。密钥以 sk-ant- 开头。
# 只打开 ENABLE_ANTHROPIC，并让 DEFAULT_COMPANY 与它一致。
ENABLE_ANTHROPIC=true
ENABLE_OPENAI=false
ENABLE_DEEPSEEK=false
ENABLE_OLLAMA=false
ENABLE_GEMINI=false
ENABLE_QWEN=false
DEFAULT_COMPANY=ANTHROPIC
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-5-5
TR_ANTHROPIC_MAX_TOKENS=8000

# 词元（冷启动默认；运行期请在配置中心维护 TR_MAX_TOKENS / MAX_TOKENS）
TR_MAX_TOKENS=8000
MAX_TOKENS=4000
TOKEN_MAX_PER_SESSION=50000
TOKEN_MAX_CALLS_PER_SESSION=100

# Ollama (本地部署)
DEFAULT_COMPANY=OLLAMA
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

Claude 当前型号 `claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5`、`claude-fable-5-1` 不接受 `temperature`、`top_p`、`top_k`，请求只带 `max_tokens`。短别名 `opus`、`sonnet`、`haiku`、`fable`，以及已退役的 `claude-3-*`、`claude-sonnet-4-5`、`claude-opus-4-1` 会映射到上面的当前型号。未填写 `ANTHROPIC_MODEL` 时默认 `claude-sonnet-5-5`。同一时间只启用一个 `ENABLE_*` 提供商。

