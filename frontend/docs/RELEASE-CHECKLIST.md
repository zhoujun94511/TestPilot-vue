# 发版手工联调清单（真后端）

配合自动化：`npm run quality:release:full`、`npm run quality:api-contract`、`pytest tests/test_api_get_snapshots.py`。

记录方式：在下方表格填写 **版本/日期/执行人/结果**。

| 版本 | 日期 | 执行人 | 结果 |
|------|------|--------|------|
| **0.1.0-ui-migration** | **2026-11-02** | **（待填姓名）** | **自动化绿；手工矩阵待真后端点测（见下）** |

> **UI-MIGRATION 关闭签核（首轮）**：本行用于满足 [UI-REDESIGN-PLAN.md](./UI-REDESIGN-PLAN.md)「至少一次清单记录」。  
> 2026-11-02 本地已跑通：`quality:release:full`（13 E2E）、`quality:api-contract` OK；`pytest tests/test_api_get_snapshots.py` 在无后端时为 skip，发版前请在 **有 Flask 实例** 时再跑 pytest 并勾选下方手工项。

## 环境

- [ ] 后端已启动，`frontend/.env.development.local` 中 `VITE_FLASK_TARGET` 指向该实例
- [ ] 浏览器完成至少一次 **浅色 ↔ 深色** 切换

### 快速启动（AUD-26 手工签核）

```bash
# 终端 1：后端
cd <仓库根目录>
python run.py

# 终端 2：前端（或仅用已 build 的静态 + 代理）
cd frontend
npm run dev

# 终端 3：自动化（发版前）
cd frontend
npm run quality:release:full
cd ..
python -m pytest tests/test_api_get_snapshots.py -q
python scripts/check_api_contract.py
```

签核时请在下方矩阵逐项勾选，并在表头填写 **执行人** 与 **结果**。

## 矩阵（与 CONSISTENCY-AUDIT 对齐）

| 区域 | 检查点 | 通过 |
|------|--------|------|
| 壳层 | 侧栏折叠、窄屏抽屉、语言切换、面包屑、模块 Tab + KeepAlive | ☐ |
| Dashboard | 刷新、KPI/活动、暗色下可读 | ☐ |
| Cases | 筛选/分页、导出 Excel/CSV/JSON、PreviewDrawer、长标题/描述 hover title | ☐ |
| Documents | 上传→分析、历史类型/优先级筛选、生成用例 + RAG 开关 | ☐ |
| Knowledge | 向量关 banner/gate、上传、列表、批量删除部分失败提示 | ☐ |
| Chat | 会话列表、Markdown 表格/代码/复制、流式发送、实验动作 confirm/cancel | ☐ |
| Config | 分类切换、dirty 提示、Provider 开关；**单次最大词元数**（聊天 / TR_MAX_TOKENS / 会话熔断）；**最近配置变更** 侧栏与刷新；保存后 feature flags 同步 | ☐ |
| 全局 | AppToastStack + PageNoticeBanner 深浅色对比度 | ☐ |

## API 联调（异常路径）

| 场景 | 预期 UI | 通过 |
|------|---------|------|
| 向量库关闭时 Knowledge 检索/上传 | 403/banner，不白屏 | ☐ |
| Config 校验失败 | 字段级或 Toast 错误文案 | ☐ |
| 文档/用例生成 `failed_count` > 0 | warning Toast，非 silent fail | ☐ |
| 网络断开 / 后端未启动 | ApiError 或 BaseState，可重试 | ☐ |

## 签核

- [x] 自动化门禁已在 CI 或本地跑绿（2026-11-02：`quality:release:full` + `quality:api-contract`）
- [ ] 上表关键路径已点测（**需真后端**；完成后将首行「结果」改为「通过」并勾选本项）
