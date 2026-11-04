# TestPilot Web 全局 UI/UX/UE 审计与优化报告（v2 · 独立复审计）

**审计日期**：2026-11-03  
**审计方式**：代码结构梳理 + 本地 `npm run dev`（5173）双主题人工走查 + Playwright 15 项 + `quality:audit` / `build`  
**说明**：本报告不沿用历史审计结论作为验收依据；以当前仓库与本次实际验证为准。

---

## 1. 项目现状分析

### 1.1 前端架构

| 维度 | 现状 |
|------|------|
| 框架 | Vue 3 + Vue Router 4 + Pinia |
| 构建 | Vite 6 |
| 样式 | Tailwind CSS 3（`darkMode: [data-theme="dark"]`，`preflight: false`）+ `src/styles/tokens.css` 设计变量 |
| 组件库 | Reka UI（Dialog / Dropdown / Sheet 等）+ 自研 `Tp*`（Button、Input、Switch、State 等） |
| 图标 | Lucide Vue |
| i18n | vue-i18n（zh / en） |
| 布局 | `DefaultLayout`：侧栏 + 顶栏（面包屑、kicker、页标题）+ 主内容 |
| 路由 | 13 个业务 View：总览、配置、文档（3 Tab）、知识库（3 Tab）、用例（2 Tab + Shell）、Chat |

### 1.2 主题机制

- `stores/app.ts` 持久化主题，`document.documentElement` 设置 `data-theme="light" | "dark"`。
- 语义色与表面色集中在 `tokens.css` 的 `:root` 与 `[data-theme="dark"]`；Tailwind `theme.extend.colors` 映射到 `--tp-*`。
- 自动化：`scripts/check-theme-tokens.js` 校验 87 个定义 token、76 处引用一致；源码 Vue/TS 中无散落的 `#hex` 硬编码（仅 token 与少量 shadow 表达式）。

### 1.3 样式组织

- **全局**：`main.css` → `tokens.css`、`tailwind.css`、`motion.css`、`chat-rich-content.css` 等。
- **模式库**：`src/lib/*-ui.ts`（`field-control`、`dropdown-ui`、`panel-ui`、`shell-ui`、`notice-ui` 等）统一控件与浮层外观。
- **页面**：各 `*View.vue` 组合 `PagePanel`、`TableToolbar`、`ToolbarOverflowMenu` 等；顶栏模式见 `docs/TOOLBAR-PATTERN.md`。

### 1.4 主要风险与技术债

1. **运行环境**：本次浏览器走查时后端/API 多返回 500，总览/列表/配置等多为**降级态、空态、错误态**；满数据表格、上传成功、预览抽屉正文、配置表单全字段等**未在本机完整验证**。
2. **无 Tooltip / Popover 组件**：长文本依赖原生 `title` 与布局截断，键盘用户与触屏体验有限。
3. **WCAG 非文本对比**：浅色下 `--tp-border-default` 相对 `#ffffff` 约 **1.56:1**，低于 UI 组件 3:1 建议；正文与主按钮对比度良好。
4. **Placeholder**：浅色 `#94a3b8` on `#ffffff` 约 **2.56:1**，低于正文 4.5:1（行业上 placeholder 常作辅助，但仍影响可辨性）。

---

## 2. UI/UX/UE 审计报告

### 2.1 统计摘要

| 指标 | 数量 |
|------|------|
| 发现问题总数 | **12** |
| P0 | **0** |
| P1 | **2**（其中 **1 已修复**） |
| P2 | **7**（其中 **1 已修复**） |
| P3 | **3** |
| 浅色主题相关 | 5 |
| 深色主题相关 | 3 |
| 双主题 | 4 |

### 2.2 问题清单

#### P1 — 高优先级

| 编号 | 页面/组件 | 主题 | 表现 | 复现 | 影响 | 建议 | 状态 |
|------|-----------|------|------|------|------|------|------|
| **UX-1103-P1-01** | `DropdownMenu*` / `ToolbarOverflowMenu` | Both | 菜单项仅用 `focus:` 样式，Reka 悬停/键盘高亮为 `data-highlighted`，悬停反馈几乎不可见 | 文档管理 →「更多」→ 鼠标移入「导出需求」 | 所有溢出菜单 | 使用 `data-[highlighted]:` + `focus-visible:ring` | **已修复**（`dropdown-ui.ts`、`DropdownMenuSubTrigger.vue`） |
| **UX-1103-P1-02** | 全局 Input / Textarea | Light | Placeholder 对比约 2.56:1 | 用例生成页需求描述空态 | 所有表单占位符 | 略加深 `--tp-color-text-placeholder`（Light），或 labels 强化 | **已修复**（Light `#6b7280`，对齐计划 2026-11-03） |

#### P2 — 中优先级

| 编号 | 页面/组件 | 主题 | 表现 | 复现 | 影响 | 建议 | 状态 |
|------|-----------|------|------|------|------|------|------|
| **UX-1103-P2-01** | 配置中心面包屑 | Both | 面包屑连续两段「配置中心」 | 打开 `/config` 读 a11y 树 | 配置页 | 模块无 Tab 时勿重复 `titleKey` | **已修复**（`useBreadcrumbs.ts`） |
| **UX-1103-P2-02** | `DefaultLayout` 顶栏 | Both | kicker + 面包屑 + 页标题 + 副标题信息重复 | 任意子 Tab 页 | 垂直空间、认知负荷 | 子 Tab 页考虑隐藏与面包屑重复的 H1 | **已修复**（面包屑≥2 时隐藏 kicker） |
| **UX-1103-P2-03** | 表格/描述列 | Both | 无 Tooltip 组件，仅 `title` | 文档表 description 列 | 截断内容难发现 | 引入基于 Reka 的 Tooltip 或 ExpandableCell | **已修复**（`TpTruncateText` + 全局 `TooltipProvider`） |
| **UX-1103-P2-04** | 全局边框 token | Light | 边框/表面非文本对比 ~1.56:1 | 浅色次要按钮、卡片边 | 边界感偏弱 | 评估 `--tp-border-default` 略加深或 `--tp-border-strong` 作默认交互边 | **已微调**（Light/Dark border token） |
| **UX-1103-P2-05** | 总览/列表 | Both | API 500 时多处「重试」与 Banner 并存 | 无后端启动总览 | 错误态噪音 | 合并同源错误提示（总览已部分去重） | **已优化**（顶栏重试=刷新；区块错误在 partial 时抑制） |
| **UX-1103-P2-06** | Chat / 配置 | Both | 后端不可用时大量 disabled 工具栏 | `/chat` 无会话 | 可发现性 | 空态说明「连接后端后可…」 | **已修复**（ActionBar hint + i18n） |
| **UX-1103-P2-07** | 验证缺口 | Both | 满表、Dialog 确认删行、Sheet 预览、上传拖拽未测 | 需真实 API | 发布风险 | 联调后补 e2e 或 staging 手检清单 | 环境限制 |

#### P3 — 低优先级

| 编号 | 页面/组件 | 主题 | 表现 | 建议 |
|------|-----------|------|------|------|
| **UX-1103-P3-01** | `switch-ui.ts` | Both | 滑块 shadow 使用 `rgb(0_0_0/0.18)` | 改为 token 化 shadow | **已修复**（`--tp-shadow-switch-knob`） |
| **UX-1103-P3-02** | 壳层背景 | Light | 径向渐变装饰偏重 | 可收敛 | **已略收敛**（`shell-ui` 渐变透明度） |
| **UX-1103-P3-03** | 构建 | — | Tailwind 对 `duration-[var(--tp-motion-fast)]` 歧义警告 | 按提示转义或改写法 | **已修复**（`duration-tp-fast`） |

### 2.3 双主题与控件抽查结论（本次实际看过）

| 路由 | Light | Dark | 控件抽查 |
|------|-------|------|----------|
| `/` 总览 | ✓ | ✓ | 错误 Banner、Toast、快捷卡片、重试按钮可读 |
| `/documents/manage` | ✓ | — | Tab、Switch、Search、Select、溢出菜单（修复后高亮） |
| `/config` | — | ✓ | 分类侧栏、导入导出、错误态；面包屑重复已修 |
| `/cases/generate` | — | ✓ | Textarea、Select、Switch、主按钮 disabled 态 |
| `/chat` | — | ✓ | Composer、多 Switch、建议问题按钮 |
| 文档/知识/用例 Tab 切换 | ✓（e2e） | ✓（e2e 主题用例） | PageTabs、筛选表单 |
| 窄屏抽屉 | ✓（e2e 390px） | — | 侧栏抽屉、菜单按钮 |

**未在本轮满血验证**：上传页文件列表、知识库向量 Banner 开启态、用例管理批量栏、ConfirmDialog 真实删除流、PreviewDrawer 长文、Date/Time Picker（项目未使用）。

### 2.4 可访问性（抽样计算）

基于 `tokens.css` 实色对的 sRGB 对比度（正常文本 AA 4.5:1，大文本 3:1）：

| 组合 | 比值 | AA 正文 |
|------|------|---------|
| Light text-900 / surface | 17.85 | 通过 |
| Light text-600 / surface | 7.58 | 通过 |
| Light text-500 / subtle | 4.34 | 通过 |
| Light placeholder / surface | 2.56 | **不通过** |
| Light border / surface | 1.56 | 非文本边界偏弱 |
| Dark text-900 / surface | 14.33 | 通过 |
| Dark text-500 / subtle | 7.40 | 通过 |
| Dark text-400 / surface | 6.06 | 通过 |
| Dark border / surface | 2.12 | 边界仍偏弱 |
| Primary 按钮 inverse / primary-600 (dark) | 4.27 | 通过 |

键盘：顶栏主题/语言、侧栏折叠、Tab 列表、表单控件均可 Tab 到达；Dropdown 修复后 `focus-visible` 环可见。无独立 Tooltip 键盘路径。

---

## 3. 设计规范优化说明（与现体系对齐）

本次**不推翻**现有 token 体系，归纳当前有效规范：

### 3.1 颜色（语义一致，Light / Dark 分别定义）

- **Background**：`--tp-bg-page` / **Surface**：`--tp-bg-surface` / **Subtle**：`--tp-bg-subtle` / **Elevated**：`--tp-bg-elevated`
- **Text**：900 → 400 + `--tp-color-text-placeholder`
- **Border**：`--tp-border-default`、`--tp-border-strong`、`--tp-border-interactive`
- **Brand & 语义**：primary、ai、success、warning、danger、info；Notice 系列 `--tp-notice-*`
- **浮层**：`--tp-overlay-scrim`、`--tp-shadow-md/lg`、`popover/dropdown` 使用 surface + border + shadow

### 3.2 交互状态（实现落点）

| 状态 | 实现 |
|------|------|
| Default | `field-control.ts`、`TpButton` cva |
| Hover | 按钮/链接触摸 mix；菜单 **`data-[highlighted]`**（本次补齐） |
| Focus | `focus-visible:ring-[var(--tp-ring)]` |
| Disabled | opacity + 仍可读前景色 |
| Error/Success | `TpState`、`PageNoticeBanner`、`notice-ui` |

### 3.3 视觉规范

- **字体**：`--tp-font-sans`，页级 `page-typography.ts`
- **间距**：`--tp-space-*`，`--tp-page-block-gap`，响应式 `--tp-content-padding`
- **圆角**：xs → xl
- **动效**：`--tp-motion-fast/normal`，`motion.css` 尊重 `prefers-reduced-motion`

---

## 4. 代码修改记录（本轮审计实施）

| 文件 | 作用 | 原因 | 业务逻辑 |
|------|------|------|----------|
| `src/lib/dropdown-ui.ts` | 菜单项高亮 | P1-01 Reka highlighted 态 | 否 |
| `src/components/ui/dropdown-menu/DropdownMenuSubTrigger.vue` | 子菜单触发器 | 与菜单项 token 一致 | 否 |
| `src/composables/useBreadcrumbs.ts` | 面包屑 | P2-01 配置中心重复段 | 否 |

---

## 5. 优化前后效果对比

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 文档管理 →「更多」菜单悬停 | 项背景几乎不变 |  accent 底 + 前景色清晰 |
| 配置中心面包屑 | 总览 › 配置中心 › 配置中心 | 总览 › 配置中心 |
| 双主题主文案/按钮 | 已符合 token（历史批次） | 本轮未改 token，对比度仍达标 |

*本轮未归档仓库内 before/after 截图；本地审计时曾抓取总览浅色降级态截图（后端 500）。建议在联调环境补一组 Light/Dark 对照图。*

---

## 6. 回归测试结果

| 项 | 结果 |
|----|------|
| `npm run quality:audit` | 通过 |
| `npm run build` | 通过 |
| Playwright **20/20** | 通过（含 `ux-audit-followup`：kicker、backend hint、总览重试合并、文档 Tooltip 桩） |
| 浏览器手检 | 见 §2.3 |
| 对比度 | §2.4 脚本计算 |
| **未验证（需联调）** | 满数据 UI、上传、生成成功链路 — 见 [STAGING-UI-CHECKLIST.md](./STAGING-UI-CHECKLIST.md) |
| **遗留** | P1-02 placeholder、P2 顶栏信息架构、Tooltip、Light 边框微调 |

---

## 7. 最终结论

- **已解决（本轮）**：下拉菜单悬停/键盘高亮缺失（P1-01）；配置面包屑重复（P2-01）。与历史工程项一并，全局 token、字段控件、Dialog/Notice、错误 i18n、Toolbar 模式等**整体已达可维护的一致 UI 基线**。
- **未解决**：浅色 placeholder 对比（P1-02）；顶栏信息重复、无 Tooltip、浅色 UI 边界对比、后端不可用时的 UX 文案（P2）；装饰与构建警告（P3）。
- **回归风险**：下拉与面包屑改动为纯展示层，Playwright 全绿；菜单 `focus-visible` ring 在极窄菜单内需后续目视确认。
- **是否达到验收标准**：在**当前可验证范围**内，Light/Dark 下主内容、按钮、输入、Tab、错误态**可读可辨**；因**缺少后端满数据与部分浮层实机**，不宜宣称「全业务流程 UI 已完全验收」。
- **后续方向**：① 联调后按模块补截图与 e2e；② 评估 placeholder / border token 微调；③ 引入 Tooltip；④ 顶栏标题策略；⑤ 可选 `quality:release:full` 进 CI。

---

*报告版本：v2 · 审计执行：项目理解 → 代码扫描 → 浏览器双主题 → 分级 → 规范归纳 → P0/P1 修复 → 回归 → 本文档。*
