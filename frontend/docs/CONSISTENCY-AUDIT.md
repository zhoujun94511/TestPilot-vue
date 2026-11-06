# 前端一致性 / 显示 / 接口审计（2026-03）

## 审计范围

| 维度 | 覆盖 |
|------|------|
| 主题与颜色 | `tokens.css`、`lib/*-ui.ts`、Tailwind 语义色、深浅切换 |
| 文案与 i18n | `check-i18n.js`、`check-hardcoded-copy.js` |
| 换行与截断 | 表格单元格、Markdown、Preview、`truncate` + `title` |
| 前后端 API | `scripts/check_api_contract.py`（仓库根目录） |

## 自动化门禁（白盒 / 静态）

在 `frontend/` 目录：

```bash
npm run quality:audit          # token 引用、显示启发式、Markdown 渲染冒烟
npm run quality:api-contract   # 需 Python；前后端 path/method 对照
npm run quality:release        # 含 audit + build
npm run quality:release:full   # 再 + Playwright E2E
```

| 脚本 | 作用 |
|------|------|
| `scripts/check-theme-tokens.js` | `var(--tp-*)` 必须在 `tokens.css` 定义 |
| `scripts/check-display-patterns.js` | `v-html` 范围、视图层裸 `#` 色（blocking）；`truncate` 无 `title`（warn） |
| `scripts/test-markdown-render.mjs` | MarkdownIt 表格包装 / 代码块结构 |
| `../scripts/check_api_contract.py` | 后端路由 vs API 路径；**API 导出函数是否在 views/components 等被引用**（见脚本输出第三节） |

E2E（黑盒 UI）：`e2e/shell.spec.ts`、`e2e/ui-regression.spec.ts`（含 Chat Markdown API 桩）。

---

## 主题与颜色 — 结论

### 机制（正确）

- 切换：`data-theme` + `color-scheme`（见 `THEME-I18N-AUDIT.md`）。
- 主路径：`var(--tp-*)`、`bg-background`、`text-foreground`、`bg-muted`。
- 有意硬编码：仅 `lib/notice-ui.ts` 告警色板（均带 `dark:` 对）。

### 已修复（本次走查）

| 项 | 处理 |
|----|------|
| 表格长文本撑破/不换行 | `table-ui.ts` → `tableBodyCell` 增加 `break-words` / `overflow-wrap:anywhere` |
| 文档列表描述截断无提示 | `DocumentsView` 描述列 `title` + `max-w-96` |
| 窄屏抽屉遮罩挡住关闭按钮 | `shell-ui.ts` 遮罩自顶栏下缘起（见 UI-MIGRATION） |

### 建议手测

Dashboard / Cases / Chat / Config / Knowledge 各切换浅↔深；触发 PageNoticeBanner 与 AppToastStack。

---

## 换行与显示 — 结论

| 区域 | 策略 |
|------|------|
| Chat Markdown | `chat-rich-content.css`：`p` 用 `pre-wrap`；代码块 `pre`；表格外层横向滚动 |
| Preview / 分析块 | `documents-ui` / `preview-drawer-ui`：`whitespace-pre-wrap break-words` |
| 表格默认单元格 | 全局 `tableBodyCell` 换行（见上） |
| 会话/文件名 | 保留 `truncate`，依赖 `:title` 或 hover（脚本对无 `title` 的 truncate 仅 **WARN**） |

### 已知 WARN（可逐步补 title）

运行 `npm run quality:audit` 会列出 `truncate-without-title` 行号；优先 Knowledge/Cases/Chat 侧栏。

---

## 前后端接口 — 结论

**`check_api_contract.py` 结果（当前）：无 path/method 不一致。**

前端 API 层未封装、且当前无 UI 需求（属预期）：

- `GET /api/experimental-actions/execution/<id>`（执行详情；确认/取消已由聊天 API 封装，页面在 `/experimental-tools`）
- `POST /api/stats/record`（后端内部埋点）

**2026-11 前后端对齐（已落地）**：用例 `PUT`+编辑抽屉+`getCase`；需求 `GET/PUT`+历史页/分析页编辑；知识库 `PUT` 元数据+上传读 `config`；Chat 快捷回复接 `quick-reply/stats`；配置中心展示 `audit-logs`。

**Token 配置**：运行期以配置中心为准，UI 分区与键说明见 [TOKEN-CONFIG.md](./TOKEN-CONFIG.md)；白盒 `pytest tests/test_token_config.py`。

`check_api_contract.py` 第三节会列出「API 已导出但未在 views/components/composables/stores 检测到引用」的函数；别名/预留入口在脚本 `IGNORED_UNUSED_API_EXPORTS` 中维护。需门禁失败时：`STRICT_API_EXPORTS=1 python ../scripts/check_api_contract.py`。

### 运行时异常（前端责任链）

1. `http.ts`：统一 `ApiError`、numeric `code` 成功判定、`Accept-Language`。
2. `api/core.ts`：`normalizeResponse` / `pickCompatField` 兼容 `data` / 旧字段名。
3. View：`ApiError.message` → Toast / `BaseState`；列表页区分 `listError` 与空态。

联调建议：向量库关闭（403）、Config 校验失败、`generate-from-analysis` 部分失败（`failed_count`）— 各走一条真实请求记入发版清单。

---

## 测试场景矩阵（推荐）

| 场景 | 自动化 | 手工 |
|------|--------|------|
| 主题 token 无悬空变量 | `check-theme-tokens.js` | 浅/深切换各页 |
| 表格长 ID/URL 换行 | E2E 首屏 + 单元格 class | Cases 管理宽列 |
| Chat 表格/代码 | `test-markdown-render.mjs` + E2E 桩 | 真后端长消息 |
| API 路径 | `check_api_contract.py` | 上传/流式/导出 |
| i18n 双语 | `i18n:check` | 顶栏 EN ↔ 简体 |

---

## CI 与集成测试

- 发版前本地检查：`npm run quality:api-contract`、`pytest tests/test_api_get_snapshots.py`、`npm run quality:release:full`。`.github/workflows/frontend-quality.yml` 只覆盖 GitHub，GitLab 不使用这份工作流。
- GET 字段快照：`tests/fixtures/api_get_snapshots.json`；更新：`UPDATE_API_GET_SNAPSHOTS=1 pytest tests/test_api_get_snapshots.py`。
- 发版手工联调：`RELEASE-CHECKLIST.md`。
