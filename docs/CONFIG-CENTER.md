# 配置中心

TestPilot 通过 Web **配置中心**统一管理运行期参数，优先级：**配置中心 > `.env` > `config/settings.py` 默认值**。保存后多数项即时生效，无需重启 Flask。

## 初始化

首次部署或升级后建议执行：

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/init_config_center.py
```

脚本会写入默认分类与配置项，并做迁移（例如 `TR_MAX_TOKENS` 统一词元、`TOKEN_MAX_*` 归入 `ai_model`、legacy `TR_*_MAX_TOKENS` 同步）。

## 前端结构

| 能力 | 说明 |
|------|------|
| 侧栏分类 | 与后端 `GET /api/config/categories` 一致；高亮当前项，无额外「当前分类」标签 |
| 分类表单 | 按分类编辑；敏感项掩码显示，支持显示/隐藏 |
| 导出 / 导入 | 顶栏（**最近配置变更**页隐藏） |
| 最近配置变更 | 侧栏项「最近配置变更」（内部 id：`audit_trail`），只读列表 + 独立刷新 |

页面实现：`frontend/src/views/ConfigCenterView.vue`；导航与审计常量：`frontend/src/lib/config-ui.ts`。

## REST API（前缀 `/api/config`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/categories` | 配置分类列表 |
| GET | `/<category>` | 指定分类下全部项 |
| POST | `/<category>` | 批量更新分类 |
| GET | `/item/<key>` | 单项 |
| PUT | `/item/<key>` | 更新单项 |
| DELETE | `/item/<key>` | 删除项 |
| GET | `/export` | 导出 |
| POST | `/import` | 导入 |
| GET | `/audit-logs` | 配置变更审计（`limit` / `offset` 查询参数） |
| POST | `/validate/<key>` | 校验单项 |

实现：`blueprints/config_center.py`；业务：`services/config_center_service.py`。

## 词元与熔断（摘要）

在 **AI 模型设置** 中维护聊天、用例/需求、会话熔断相关键；UI 与运行期行为详见 [frontend/docs/TOKEN-CONFIG.md](../frontend/docs/TOKEN-CONFIG.md)。

- 接近上限（默认 80%）：`GET /api/stats/token-session` + 前端 Toast 预警  
- 已超限：API 返回 429 与 `message_key`（如 `common.tokenSession.exceededTokens`），文案可在 i18n 中维护

## 联调与发版

- 联调冒烟：`docs/DEV-INTEGRATION.md`（含 `/api/config/categories`、词元 pytest）。
- 手工点检：`frontend/docs/RELEASE-CHECKLIST.md`（Config 矩阵含审计页与词元分区）。
- 前后端契约：`scripts/check_api_contract.py`、`frontend/npm run quality:api-contract`。
