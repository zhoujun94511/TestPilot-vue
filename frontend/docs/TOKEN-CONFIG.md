# 词元配置单一真相源（2026-11）

运行期**以配置中心数据库为准**；`.env` 与 `config/settings.py` 仅在冷启动或库中无对应项时作为默认值。

## 配置键与分类

| 键 | 分类 | 作用 |
|----|------|------|
| `MAX_TOKENS` | ai_model | **聊天**、快捷回复、Ollama 单次 `max_tokens` |
| `TR_MAX_TOKENS` | ai_model | **用例生成**与**需求分析**共用单次最大词元数 |
| `TOKEN_MAX_PER_SESSION` | ai_model | TokenMonitor：单会话累计词元熔断 |
| `TOKEN_MAX_CALLS_PER_SESSION` | ai_model | TokenMonitor：单会话模型调用次数熔断 |

### 与 legacy 键的关系

- 历史项 `TR_OPENAI_MAX_TOKENS`、`TR_DEEPSEEK_MAX_TOKENS`、`TR_GEMINI_MAX_TOKENS`、`TR_QWEN_MAX_TOKENS` 仍可在库中存在；`scripts/init_config_center.py` 会迁移/同步。
- 解析顺序（`utils/utils_ai_models/get_llm.py`）：配置中心 **`TR_MAX_TOKENS` 优先**，否则回退各厂商 legacy 键。
- 在配置中心保存 **`TR_MAX_TOKENS`** 时，前端会同步写入各 legacy 键，便于旧脚本与导出一致。

修改后请在配置中心**保存**；AI 相关键会重载 LLM，词元熔断键会调用 `refresh_token_monitor_session_limits()`（见 `blueprints/config_center.py`）。

### 会话熔断体验（2026-11）

- **80% 预警**：累计词元或调用次数达到上限的 80% 时，`GET /api/stats/token-session` 返回 `level: warning`；前端在用例/文档/聊天/配置页每 45s 轮询并 **Toast 提示**（同一用量签名只提示一次）。
- **超限阻断**：抛出 `TokenSessionLimitExceeded`，经 `build_model_error_result` 返回 HTTP **429** 与 i18n `message_key`（如 `common.tokenSession.exceededTokens`），前端 Toast 展示友好文案。
- 计数范围为**后端进程单例**；重启 Flask 会重置。与仪表盘「近 N 天聊天词元统计」无关。

## 配置中心 UI

- 入口：**配置中心 → AI 模型设置**。
- 分区 **「单次最大词元数」**（`config-token-ui.ts` + `PagePanel`）：
  - 聊天：`MAX_TOKENS`
  - 用例与需求分析：`TR_MAX_TOKENS`（**不再**按四厂商分开展示）
  - 会话熔断：`TOKEN_MAX_PER_SESSION`、`TOKEN_MAX_CALLS_PER_SESSION`
- **最近配置变更**：侧栏虚拟分类 `audit_trail`（`CONFIG_AUDIT_CATEGORY_ID`），独立视图；该页顶栏「刷新」仅拉审计列表，隐藏导出/导入。

## 代码入口

| 场景 | 位置 |
|------|------|
| 单次上限（用例/需求 vs 聊天） | `utils/utils_ai_models/get_llm.py` |
| 聊天默认 `max_tokens` | `blueprints/chat.py` |
| 快捷回复词元分配 | `smart_quick_reply_generator.py`（由 `MAX_TOKENS` 按比例推导，无单独配置键） |
| 会话熔断 | `utils/utils_performance_monitoring/token_monitor.py` |

## 前端字段类型

键名含 `TOKEN` 的**整数**配置（如 `MAX_TOKENS`、`TR_MAX_TOKENS`）不得按 API 密钥渲染；见 `frontend/src/api/config.ts` 中 `inferInputKind` / `isNumericTokenLimitKey`。

白盒：`cd frontend && node scripts/test-config-infer.mjs`（含 `quality:audit` 链路）。

## 白盒测试

仓库根目录（建议 `-p no:xonsh`）：

```bash
pytest tests/test_token_config.py -q
```
