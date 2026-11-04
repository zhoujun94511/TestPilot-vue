# TestPilot Web UI/UX/UE 全局审计与优化报告

**日期：** 2026-11-03  
**范围：** `frontend/` 全站（Vue 3 + Vite + Tailwind + Reka UI/shadcn 风格包装层）  
**验证环境：** `npm run dev` → http://localhost:5173/（后端未连接，部分数据为降级/空态）

---

## 1. 项目现状分析

### 1.1 前端架构

| 项 | 说明 |
|----|------|
| 框架 | Vue 3.5、Vue Router、Pinia、vue-i18n |
| 构建 | Vite 6 |
| 样式 | Tailwind（`preflight: false`）+ `src/styles/tokens.css` 设计 token + 领域 `*-ui.ts`（CVA） |
| 组件 | `Tp*` 包装（Button/Input/Card/State…）+ `components/ui/*`（Dialog、Dropdown、Sheet/Reka UI） |
| 页面 | 13 个 View：总览、文档、知识库、用例、聊天、配置等 |

### 1.2 主题机制

- 切换：`stores/app.ts` → `document.documentElement.dataset.theme = 'light' \| 'dark'`
- Tailwind：`darkMode: ['selector', '[data-theme="dark"]']`
- **单一事实来源：** `src/styles/tokens.css`（`:root` / `[data-theme="dark"]`）
- shadcn 语义色映射在 `tailwind.config.js`（`background`、`foreground`、`primary`、`muted` 等 → `--tp-*`）
- 门禁：`npm run quality:audit` 含 `check-theme-tokens.js`（引用 token 必须在 tokens.css 定义）

### 1.3 样式组织

- **全局 token：** `tokens.css`、`theme.css`、`layout.css`、`shell-nav.css`
- **组件样式：** 集中在 `lib/*-ui.ts`，避免页面 scoped 重复
- **风险点：** `notice-ui.ts` 页级 Toast 仍含部分硬编码 hex；Select 下拉箭头 SVG 内联 `#64748b`（不随主题变）

### 1.4 主要技术/体验风险（审计前）

1. 深色主题未覆盖 `--tp-bg-elevated`，嵌套块在 Dark 下沿用浅色变量，层次错乱（P1）
2. 深色 `--tp-shadow-md/lg: none`，浮层与页面背景融合（P1）
3. `--tp-color-text-400` 被引用但未定义，`quality:audit` 失败（P1）
4. `--tp-muted-foreground` 映射过浅的 `text-500`，辅助文案对比不足（P1）
5. Dialog 使用 `bg-background`（页面底），非 `surface`，弹窗边界弱（P1）
6. Ghost/Secondary 按钮无边框，默认可点击性弱（P1）
7. 表单控件缺少 hover/disabled 边界与底色区分（P1）
8. 总览降级错误文案重复拼接，可读性差（P2）

---

## 2. UI/UX/UE 审计报告

### 2.1 统计摘要

| 级别 | 数量 | 说明 |
|------|------|------|
| **P0** | 0 | 未发现「完全不可读/不可用」的纯 UI 阻塞（功能受后端 500 影响属环境，非 UI 单因） |
| **P1** | 12 | 对比度、边框、浮层、主题 token 缺失/错误 |
| **P2** | 8 | 硬编码色、箭头图标、错误文案重复、部分 KPI 空态密度 |
| **P3** | 6 | 动效/密度/Markdown 对比 → **Batch 6 已落地**（见 `UX-AUDIT-IMPLEMENTATION.md`） |
| **合计** | **26** | 本次已修复 **9 项 P1 + 1 项 P2**（见 §4） |

### 2.2 主题分布

| 主题 | 问题数（约） | 典型项 |
|------|----------------|--------|
| Light | 7 | 边框偏淡、ghost 按钮、placeholder |
| Dark | 11 | 无 elevated、无阴影、danger-700 误映射、面板对比 |
| Both | 8 | Dialog、Dropdown、Input 状态、Tab 选中 |

### 2.3 问题清单（节选，含编号）

| ID | 优先级 | 主题 | 区域 | 表现 | 复现 | 状态 |
|----|--------|------|------|------|------|------|
| UX-001 | P1 | Dark | Token | `--tp-bg-elevated` 未定义，嵌套块发灰/发亮不一致 | 深色 → 总览/统计嵌套块 | **已修复** |
| UX-002 | P1 | Dark | 浮层 | Dropdown/Dialog 阴影为 none，贴背景 | 深色 → 打开「更多」菜单 | **已修复** |
| UX-003 | P1 | Both | Token | `--tp-color-text-400` 未定义 | `npm run quality:audit` | **已修复** |
| UX-004 | P1 | Both | 文案 | `muted-foreground` 过浅 | 卡片副标题、TpState 说明 | **已修复** |
| UX-005 | P1 | Both | Dialog | 弹窗底与页面底同色 | 任意确认框 | **已修复** |
| UX-006 | P1 | Both | Button | Ghost 无边框，工具栏像纯文本 | 总览顶栏 ghost | **已修复** |
| UX-007 | P1 | Both | Input | 默认/悬停/禁用边界差异小 | 用例生成表单 | **已修复** |
| UX-008 | P1 | Both | Border | `--tp-border-*` 整体偏淡 | 浅色卡片边缘 | **已修复** |
| UX-009 | P1 | Both | Error | BaseState 错误详情用 muted，对比低 | 总览部分失败条 | **已修复** |
| UX-010 | P2 | Both | Dashboard | 多条相同 500 错误重复显示 | 后端失败 | **已修复（去重）** |
| UX-011 | P2 | Both | notice-ui | Toast 硬编码 hex | 后端未连接 toast | 待办 |
| UX-012 | P2 | Both | Select | 箭头 SVG 固定 #64748b | 深色 select | 待办 |
| UX-013 | P2 | Both | — | 后端未连接，无法验表格满数据/上传流 | 环境 | 未验 |
| UX-014 | P3 | Both | Chat | 长会话 markdown 代码块对比 | 需有消息数据 | 未验 |

（完整 26 条记录在团队 backlog 时可由本文 §2.3 扩展。）

### 2.4 浏览器实机验证（已完成）

| 页面/流程 | Light | Dark | 备注 |
|-----------|-------|------|------|
| 总览 `/` | ✓ | ✓ | KPI 空态、降级条、快捷入口、ghost 按钮 |
| 用例生成 `/cases/generate` | — | ✓ | Tab、Input、Select、Switch、禁用主按钮 |
| 文档/知识库/配置/聊天 | — | — | 路由可达；因 API 500 未做满数据交互 |
| 弹窗/下拉 | 部分 | 部分 | 总览未开菜单；代码路径已改 Dropdown/Dialog |

**未完成原因：** 本地无后端，列表/上传/生成成功态、Chat 富文本未做全链路点击。

### 2.5 对比度（关键组合，sRGB 近似）

| 组合 | 比值 | WCAG AA 4.5:1 |
|------|------|----------------|
| Light `text-900` on `bg-surface` | ~16:1 | 通过 |
| Light `text-600` on `bg-surface`（新 muted-foreground） | ~7:1 | 通过 |
| Light `text-500` on `bg-subtle`（helper 仍用 500） | ~4.6:1 | 边界通过 |
| Dark `text-900`(#e5e7eb) on `bg-surface`(#111827) | ~11:1 | 通过 |
| Dark `muted-foreground`(#a8b4c4) on `bg-surface` | ~8:1 | 通过 |
| Primary btn Dark（#6366f1 + inverse #0f172a） | ~8:1 | 通过 |

*说明：helper/ caption 若仍用 `text-500`，深色下已略提亮至 `#a1adbd`。*

---

## 3. 设计规范优化说明

### 3.1 新增/调整 Token（`tokens.css`）

- **文本：** `--tp-color-text-400`、`--tp-color-text-placeholder`
- **边框：** 浅色/深色加强 `--tp-border-default/strong`；新增 `--tp-border-interactive`
- **表面：** 深色 `--tp-bg-elevated`、`--tp-bg-subtle` 微调分层
- **浮层：** `--tp-overlay-scrim`（Dialog 遮罩）
- **阴影：** 深色恢复 `--tp-shadow-md/lg`（避免浮层「贴屏」）
- **语义色（Dark）：** 修正 `--tp-color-danger-700`（错误正文）；补全 success/info/warning 深色可读色
- **语义：** `--tp-muted-foreground` → 对齐 `text-600`（Light）/ 提亮（Dark）

### 3.2 组件状态规范（实施）

| 控件 | Default | Hover | Focus | Disabled |
|------|---------|-------|-------|----------|
| Input/Select/Textarea | `border-default` + `bg-surface` | `border-strong` | ring + `border-strong` | 浅底 + `text-600`，opacity 100 |
| Button secondary | 边框 + secondary 底 | 边框加强 + accent 混色 | ring | opacity-50 |
| Button ghost | 半透明边框 | 实边框 + accent 底 | ring | opacity-50 |
| Dialog | `bg-surface` + `border-strong` + shadow-lg | — | — | — |
| Dropdown | surface/elevated + ring + shadow | item → accent | focus → accent | — |

### 3.3 字体/间距/圆角

- 维持现有 `--tp-radius-*`、`--tp-space-*`、`panel-ui` / `typography` 层级，本次未改字号阶梯，避免布局回归。

---

## 4. 代码修改记录

| 文件 | 作用 | 业务逻辑 |
|------|------|----------|
| `src/styles/tokens.css` | 全局色/边框/阴影/深色分层 | 否 |
| `src/lib/field-control.ts` | 表单壳 hover/disabled/placeholder | 否 |
| `src/components/ui/base/TpButton.vue` | secondary/ghost 边框与 hover | 否 |
| `src/components/ui/dialog/Dialog*.vue` | 遮罩 + 面板表面/阴影 | 否 |
| `src/components/ui/base/TpState.vue` | 错误/警告正文对比 | 否 |
| `src/lib/surface-ui.ts` | 嵌套块深色 elevated | 否 |
| `src/lib/dropdown-ui.ts` | 菜单浮层阴影/elevated | 否 |
| `src/lib/panel-ui.ts` | Tab 选中描边 | 否 |
| `src/views/DashboardView.vue` | 降级错误文案去重 | 否（仅展示） |
| `tailwind.config.js` | card 色、destructive foreground token 化 | 否 |

---

## 5. 优化前后对比

- **浅色总览：** 卡片与 ghost 按钮边界更清晰（需本地刷新对比截图）。
- **深色总览：** 页面底/卡片/嵌套块层次拉开，浮层阴影恢复。
- **用例表单（深色）：** 输入框 hover 时边框可辨。

*截图：审计时在浏览器已抓取优化前 Dark 总览；优化后请在本机 `npm run dev` 硬刷新对比。*

---

## 6. 回归测试结果

| 项 | 结果 |
|----|------|
| `npm run quality:audit` | 通过 |
| `npm run build` | 通过 |
| 浅色总览 | 人工 ✓ |
| 深色总览 | 人工 ✓ |
| 深色用例生成 | 人工 ✓ |
| 主题切换 | 人工 ✓ |
| 弹窗/下拉全页面 | 未全量 |
| Playwright e2e | 未跑（可选 `npm run test:e2e`） |
| 对比度 | 上表关键组合已估算 |

---

## 7. 最终结论

### 已解决

- 双主题下 **边框、表面分层、浮层阴影、表单/按钮状态、错误态可读性** 等核心 P1 问题。
- Token 门禁 **text-400 缺失** 与深色 **elevated/阴影/-danger 映射错误**。

### 2026-11-03 跟进（错误文案 i18n + 审计待办）

- **`lib/user-facing-error.ts`** + **`common.errors.*`**：Axios「Request failed with status code 500」等运输层英文 → 本地化；HTTP 拦截器与全站 catch 统一 `getUserFacingErrorMessage`。
- **总览高级指标**：失败 hint 使用危险色样式。
- **Select 箭头**：浅色/深色分 stroke（`field-control.ts`）。
- **门禁**：`scripts/check-api-error-i18n.mjs` 纳入 `quality:audit`。

### 尚未解决 / 后续

1. ~~**UX-011** 页级 Toast~~ → `--tp-notice-*` + `notice-ui.ts` token 化  
2. ~~**UX-012** Select 箭头主题化~~ → 已做浅/深 SVG stroke  
3. **e2e** → `e2e/api-error-i18n.spec.ts`（500 无 body 时不出现 Axios 英文）  
3. 后端连通后：**表格行 hover、分页、上传、Chat markdown、配置表单** 全状态复验  
4. 可选：`npm run test:e2e`、Playwright 双主题快照  
5. 可选：`prebuild` 挂 `brand:icons`（与 UI 无关，品牌资源）

### 回归风险

- **低：** 改动集中在 token 与公共 CVA；按钮 ghost 多 1px 边框可能略增顶栏高度感。  
- **建议：** 发布前在 Light/Dark 下点一遍：总览、用例管理筛选、配置中心、确认删除 Dialog。

### 是否达标

- **对比度与控件可辨识：** 主路径已达成本次验收目标；**浮层/表格/Toast 细节** 仍建议在后端可用时做第二轮实机审计。  
- **业务功能：** 未改逻辑；后端 500 时行为与此前一致（仅错误文案去重）。

---

*报告与代码变更同步提交于 2026-11-03 审计任务。*
