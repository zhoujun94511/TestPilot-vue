# UI 迁移：Tailwind + shadcn-vue

## 现状

- **设计 token**：`src/styles/tokens.css`（含 shadcn 语义别名 `--tp-foreground`、`--tp-ring` 等）
- **Tailwind 3**：`tailwind.config.js`，`preflight: false`（避免覆盖现有全局样式）
- **工具**：`src/lib/utils.ts` 的 `cn()`（clsx + tailwind-merge）
- **shadcn 配置**：根目录 `components.json`（路径别名与 CLI 对齐）

## 已迁移

| 组件 | 说明 |
|------|------|
| `TpButton` | CVA + Tailwind，API 不变 |
| `TpInput` / 表格筛选控件 | 仅 `lib/field-control.ts`（CVA + Tailwind） |
| `TpTag` | 内部使用 `components/ui/badge/Badge.vue` |
| `TpCard` | 内部使用 `components/ui/card/*` |
| `components/ui/badge/Badge.vue` | shadcn 基元 |
| `components/ui/card/*` | shadcn 基元 |
| `ConfirmDialog` | 基于 `components/ui/dialog/*` |
| `PreviewDrawer` | 基于 `components/ui/sheet/*` |
| `TpPager` / `TpProgress` | Tailwind 进度与分页样式 |
| `TpSeparator` | `components/ui/separator/Separator.vue` + token `bg-border` |
| `TpState` / `BaseState` | Tailwind（spinner 用 `animate-spin`） |
| `CasesView` / `ConfigFormItem` 标签 | 原生 `.tp-tag` → `TpTag` |
| `TableToolbar` | Tailwind + token（`lib/table-ui.ts`） |
| 表格筛选控件 | `TableFilterForm` / `TableFilterInput` / `TableFilterSelect`（`field-control` + shadcn 风格） |
| `BaseTable` | 表格壳/表头/行/选中态 Tailwind（`lib/table-ui.ts`）；钩子类 `base-table-block` / `base-table-wrap` |

`components.css` 已移除：`tp-confirm-*`、`tp-progress*`、`tp-dialog__*`、`.tp-tag*`、`.tp-state*`，并去重重复的 `.tp-system-overview` 块。

## 审计对齐（后续修复）

| 项 | 实现 |
|----|------|
| 确认框遮罩/Esc | `ConfirmDialog` 在 `update:open(false)` 且非确认路径时 `emit('cancel')`，避免 History 等页 `deleteConfirmAction` 残留 |
| `TpProgress` 色 | `tone`：`ai`（默认，Dashboard/AiResultCard）\| `primary` |
| CSS 去重 | 删除文件末尾重复的 `.tp-system-overview` 四件套 |
| Dialog a11y | `aria-labelledby` + 打开时聚焦首个可聚焦控件 + Tab 循环 |
| 功能开关同步 | `GET /api/stats/feature-flags` → `refreshAppFeatureFlags()`（壳层挂载；Config 保存后刷新） |
| 知识库向量关闭 | `KnowledgeShellView` 顶栏 `PageNoticeBanner` + `useKnowledgeVectorNotice` |
| Chat 偏好 | `useChatPreferences`（composer 本地开关 localStorage） |
| Chat 会话列表 | `useChatSessions`（分页 / 竞态 seq / ensureSessionVisible） |
| Chat 消息历史 | `useChatHistory`（分页 / 竞态 seq / reload & changeHistoryPage） |
| Chat 发送 / 流式 | `useChatSend` + `useChatStreamRunner` + `useChatAbort`；错误文案 `chat/chatSendErrors` |
| Chat 实验动作待确认 | `usePendingExperimentalAction`（面板 computed + restore / apply） |
| 知识库向量 gate | `useKnowledgeVectorGate` + `BaseUpload.disabled`；向量关时跳过列表请求 + `BaseState` 引导 |
| 知识库 403 识别 | `isVectorStoreDisabledError`（与 `ENABLE_VECTOR_STORE` 全 API 403 对齐） |
| Dashboard 刷新 | `handleRefresh` → `refreshAppFeatureFlags()` |
| 生产安全提示 | 非 DEBUG 且默认 `SECRET_KEY` 时启动告警；`app.py` `sys.path` 与 `run.py` 一致 |
| 壳层与文档再对齐 | 曾出现 `DefaultLayout` 回退为 `tp-shell` 旧结构而全局 CSS 已清理的情况；已恢复为 `shell-ui.ts` + `navigation.ts` + `AppBreadcrumb` + `LanguageSwitcher` + 折叠/`<1200px` 抽屉 |

## 推荐顺序（渐进）

1. ~~Input / Badge / Card~~（已完成包装层）
2. ~~Dialog / Sheet~~：`ConfirmDialog`、`PreviewDrawer` 已基于 `components/ui/dialog` 与 `components/ui/sheet`
3. ~~`TpPager`、`TpProgress`~~：Tailwind 样式
4. ~~表格层保留 `BaseTable`，工具栏与筛选 shadcn 化~~（见下「第 4 步清单」；单元格内仍为 TpTag/TpButton）
5. ~~`TpSeparator`、`TpState`~~：Tailwind / shadcn 基元

### 第 4 步清单（表格工具栏 / 筛选）

| 页面 | 筛选区 | 表内操作列 |
|------|--------|------------|
| `CasesView` | ✅ TableFilter* | ✅ 已有 TpTag / TpButton |
| `KnowledgeView` | ✅ | ✅ TpButton |
| `DocumentsView` | ✅ | ✅ |
| `DocumentsHistoryView` | ✅ | ✅ |
| `ConfigCenterView` | —（无列表筛选） | — |

已完成：`components.css` / `layout.css` / `theme.css` 中旧 `.tp-table*`、`.tp-table-toolbar*` 规则已移除。

### 第 5 步（表单控件统一）

| 范围 | 状态 |
|------|------|
| `ConfigFormItem` | ✅ 已用 `TpInput` |
| `ConfigCenterView` 快捷 Provider 区 | ✅ `TpInput` |
| `CasesView` 生成表单 | ✅ |
| `DocumentsUploadView` / `KnowledgeUpload` / `KnowledgeSearch` | ✅ |
| `ChatView` 重命名 /  composer / DELETE 确认 | ✅ `TpInput`（`bare` 内联） |

`TpInput` 增强：`bare`（无 field 壳）、`controlClass`、`type="number"` 数值 emit、`required` 绑定控件。

视图内已无裸 `class="tp-input|tp-select|tp-textarea"`；表单样式单一来源为 `field-control.ts`。

### 第 6 步（开关 + 页面 typography）

| 项 | 状态 |
|----|------|
| `TpSwitch` + `lib/switch-ui.ts` | ✅ Config / Chat composer / 文档上传 |
| `lib/page-typography.ts` | ✅ Dashboard KPI/活动、KnowledgeStatsCard、Cases/Documents 迷你 KPI、Chat 侧栏标题 |
| `components.css` 清理 | ✅ 移除旧 switch/KPI/activity/toggle/dead system-overview |

### 第 7 步（Typography + Layout 局部）

| 项 | 状态 |
|----|------|
| `page-typography` 扩展 | ✅ `dataSubtitleDense`、`result*`、brand/page 顶栏标题 |
| 视图替换 `.tp-data-*` / `.tp-section-subtitle` | ✅ Chat/Cases/Documents/Knowledge/Search/Config |
| `DefaultLayout` | ✅ brand、page 标题、折叠/顶栏按钮 → `shell-ui.ts` |
| CSS 清理 | ✅ `components.css` data/section/result；`layout.css` brand/page 标题 |

### 第 8 步（Layout 壳层 + 导航 + 面包屑）

| 项 | 状态 |
|----|------|
| `lib/shell-ui.ts` 扩展 | ✅ shell grid / sidebar / topbar / content / `navItemClass` / breadcrumb |
| `DefaultLayout.vue` | ✅ 全量 Tailwind（含 `<1200px` 抽屉侧栏） |
| `AppBreadcrumb.vue` | ✅ |
| Chat / Config 复用 `navItemClass` | ✅ 会话列表、配置分类 |
| `layout.css` 清理 | ✅ 移除 shell/nav/breadcrumb/topbar/content 与移动端块 |

### 第 9 步（PagePanel / SidebarMenu / PageTabs）

| 项 | 状态 |
|----|------|
| `lib/panel-ui.ts` | ✅ panel 壳/标题、`sidebarMenu*`、`pageTab*` |
| `PagePanel` / `SidebarMenu` / `PageTabs` | ✅ Tailwind + 配置区 `configSection` 标题 |
| 视图内裸 `tp-panel__title` | ✅ Cases / Documents / KnowledgeSearch |
| `layout.css` / `theme.css` 清理 | ✅ panel、sidebar-menu、page-tabs |

### 第 10 步（页面 chrome + 配置分区）

| 项 | 状态 |
|----|------|
| `lib/page-chrome-ui.ts` | ✅ ActionBar 工具栏、Cases 表单 `formActionsClass` |
| `lib/config-ui.ts` | ✅ `configSectionPanelClass`（provider 色条 / active）、页脚 |
| `ConfigCenterView` | ✅ PagePanel 分区 class 迁出 CSS |
| `layout.css` / `components.css` 清理 | ✅ page-toolbar、form-actions、config-section* |

### 第 11 步（页面壳 + 配置概览布局）

| 项 | 状态 |
|----|------|
| `lib/page-layout-ui.ts` | ✅ `pageRootClass`、`pageShellClass`、`pageFluidShellSectionClass` |
| Shell / Chat / Config / 主要列表页 | ✅ 替换 `tp-page` / `tp-page-shell` |
| `config-ui` 扩展 | ✅ overview、meta、form-stack、sidebar sticky 等 |
| `ConfigCenterView` + `AiProviderSettingsPanel` | ✅ |
| `layout.css` | ✅ 仅保留迁移说明（原 `.tp-page` 已清空） |

### 第 12 步（布局 utility 试点 + Chat 会话行）

| 项 | 状态 |
|----|------|
| `page-layout-ui` 12 列网格 | ✅ `grid12*` / `colSpan12*` |
| `page-typography.captionTextClass` | ✅ 替代 `.tp-small`（Config 审计区等） |
| `lib/chat-ui.ts` | ✅ 侧栏会话行布局 |
| `ConfigCenterView` | ✅ 去掉 `tp-row` / `tp-flex` / `tp-mb-3` 等 |
| `ChatView` | ✅ 主布局网格 + 会话行；移除 session scoped/CSS |

### 第 13 步（Cases / Documents / Knowledge 布局 utility）

| 项 | 状态 |
|----|------|
| `page-layout-ui` 列宽扩展 | ✅ `colSpan12Md6*`、`casesDistributionItemClass` |
| `CasesView` | ✅ 12 列网格、flex、间距；分布区 scoped 精简 |
| `DocumentsView` | ✅ 网格/KPI/需求列表 flex + `captionTextClass` |
| `KnowledgeView` | ✅ 统计卡与主栏网格（scoped 已于第 19～20 步移除） |

### 第 14 步（子页 + Chat composer）

| 项 | 状态 |
|----|------|
| `lib/upload-ui.ts` | ✅ 上传分类宽、进度条、文档自动分析 toggle |
| `KnowledgeSearchView` | ✅ 网格检索表单 + 结果区 utility |
| `DocumentsUploadView` / `KnowledgeUploadView` | ✅ Tailwind，去掉 scoped 进度/宽度 |
| `lib/chat-ui.ts` 扩展 | ✅ composer / 模板 / 实验动作 / 空状态 |
| `ChatView` | ✅ composer 与空状态迁出 scoped（保留消息区壳） |

### 第 15 步（History + Chat 消息区 utility）

| 项 | 状态 |
|----|------|
| `lib/documents-ui.ts` | ✅ 历史来源列 truncate |
| `DocumentsHistoryView` | ✅ `pageRootClass`，去掉 scoped |
| `chat-ui` 扩展 | ✅ 主卡片、消息行、建议问题、会话列表 grid |
| `ChatView` | ✅ 消息区/header/侧栏列表 utility（保留 message 卡片 scoped） |

### 第 16 步（Dashboard + 共享组件 flex/网格）

| 项 | 状态 |
|----|------|
| `lib/dashboard-ui.ts` | ✅ 系统摘要区、AI 能力卡 |
| `page-layout-ui` 扩展 | ✅ `colSpan12Md4`、`colSpan12Min1400_5/7`、`sectionStackGapClass` |
| `page-chrome-ui` flex 组合 | ✅ 供 Dashboard / PageNoticeBanner 复用 |
| `page-typography` | ✅ `welcomePageHeadingClass` / `welcomePageSubtitleClass` |
| `DashboardView` | ✅ 去掉 `tp-row` / `tp-flex` / scoped 系统区 |
| `PageNoticeBanner` / `KnowledgeStatsCard` / `ConfigFormItem` | ✅ flex/间距 utility |
| `utilities.css` | ✅ 见第 17 步（本步不再重复） |

### 第 17 步（utilities 精简 + 活动图标 + 表单/通知）

| 项 | 状态 |
|----|------|
| `utilities.css` | ✅ 仅保留 `tp-container-fluid`、`min-w-0`、`text-truncate` |
| `dashboard-ui` 活动图标 | ✅ CVA + `resolveDashboardActivityTone`；删 `components.css` 活动图标块 |
| `PAGE_NOTICE_BANNER_MARKER` | ✅ 替代 toast 选择器对 `tp-mb-3` 的依赖 |
| `config-ui` 表单项脚注 | ✅ `ConfigFormItem` helper/error |
| `table-ui.tableCellAlignEndClass` | ✅ Knowledge 操作列 |

### 第 18 步（notice / AI 结果卡 + Cases 领域 utility）

| 项 | 状态 |
|----|------|
| `lib/notice-ui.ts` | ✅ 内联 risk CVA、toast 色调钩子 |
| `lib/ai-result-ui.ts` | ✅ `AiResultCard` 布局/折叠 |
| `PageNoticeBanner` | ✅ 按 `notice.type` 设色；移除 `banner-class` prop |
| `usePageNotice` | ✅ 不再导出 `bannerClass` |
| `AiResultCard` | ✅ Tailwind + `riskBlockPanelClass` |
| `lib/cases-ui.ts` | ✅ 表格列 clamp、导出 select、同步高亮等 |
| `CasesView` scoped | ✅ 仅保留行高亮动画 |
| `components.css` | ✅ 删 inline risk/AI 卡、废弃 `tp-cases-toast` |

### 第 19 步（Documents / Knowledge 壳 + 页级 toast Tailwind）

| 项 | 状态 |
|----|------|
| `documents-ui` 扩展 | ✅ raw 块、分析需求项、行/需求高亮 + keyframes |
| `DocumentsView` | ✅ 去掉 scoped |
| `knowledge-ui.ts` | ✅ 布局/文件面板/表格 flex 链 |
| `KnowledgeView` | ✅ Tailwind + 向量 gate + `PageNoticeBanner` |
| `notice-ui` 页级 toast | ✅ CVA + 图标节点；删 `components.css` ~170 行 toast |
| `tailwind.config.js` | ✅ `page-toast-in`、`doc-row-highlight-fade` |

### 第 20 步（滚动条全局 + Chat 消息卡 + components 清理）

| 项 | 状态 |
|----|------|
| `tailwind.css` @layer | ✅ `tp-subtle-scrollbar`、Chat 消息区高度/滚动、Knowledge `.base-table-wrap` |
| `KnowledgeView` | ✅ 去掉 scoped（滚动条改全局） |
| `chat-ui` 扩展 | ✅ 用户/助手消息卡、消息列表、`chatJumpLatestButtonClass` |
| `ChatView` | ✅ 去掉全部 scoped |
| `components.css` | ✅ 删未引用：`tp-page-title*`、`tp-toolbar`、`tp-section`、`tp-icon-button`、`tp-subsurface`、旧 Chat 块 |

### 第 21 步（页根钩子 + 上传面板 + TpCard 标题）

| 项 | 状态 |
|----|------|
| `page-layout-ui` | ✅ `pageMarker*` + `pageRootMarkedClass` / `pageFluidShellMarkedClass` |
| 主要列表/子页 View | ✅ 根节点改用 marker 常量（类名仍为 `tp-*-page`） |
| `upload-ui` | ✅ `BaseUpload` 全量 Tailwind；去掉 scoped |
| `page-typography.cardSubtitleClass` | ✅ `TpCard` / `AiProviderSettingsPanel` 标题 |
| `TpCard` | ✅ 去掉 scoped（卡片壳 Tailwind 见第 24 步） |
| `components.css` | ✅ 删 `tp-surface*`、`.tp-card__title/subtitle`、`tp-upload-panel*` |

### 第 22 步（TpButton 收尾 + Cases 高亮 + Provider UI）

| 项 | 状态 |
|----|------|
| `components.css` | ✅ 删除 legacy `.tp-btn*`（样式仅 `TpButton` CVA） |
| `TpButton` | ✅ loading 用 `animate-spin`；去掉 scoped |
| `notice-ui` | ✅ `pageNoticeGhostButtonClass` 修复 toast 内 ghost 按钮样式 |
| `tailwind.config.js` | ✅ `cases-row-highlight-fade` |
| `cases-ui` / `CasesView` | ✅ 行高亮 Tailwind；去掉最后 scoped |
| `config-ui` | ✅ Provider 面板/卡片/模型 chip/开关 |
| `AiProviderSettingsPanel` | ✅ 全 Tailwind，去掉 scoped |

### 第 23 步（field-control 标签 + Chat Markdown 全局）

| 项 | 状态 |
|----|------|
| `field-control.ts` | ✅ `formLabelClass`、`helpTextClass`、必填/错误/meta |
| `TpInput` / `ConfigFormItem` / `BaseUpload` / `ChatView` | ✅ 替换 `tp-form-label` / `tp-help-text` / `tp-field__*` |
| `components.css` | ✅ 删表单标签与 field 脚注块 |
| `styles/chat-rich-content.css` | ✅ Markdown / 代码块 / 表格 / 骨架动画 |
| `ChatMessageContent` / `Skeleton` | ✅ 去掉 scoped（v-html 改全局样式） |

### 第 24 步（PreviewDrawer + components.css 收官）

| 项 | 状态 |
|----|------|
| `lib/preview-drawer-ui.ts` | ✅ Sheet 根偏移、面板尺寸、预览 `<pre>` |
| `Sheet.vue` | ✅ 可选 `rootClass`（Preview 顶栏下缘） |
| `PreviewDrawer` | ✅ Tailwind；去掉 scoped（全库 View/组件无 scoped） |
| `TpCard` | ✅ 壳样式 inline Tailwind；不再依赖 `.tp-card` CSS |
| `LanguageSwitcher` | ✅ `shell-ui.languageSwitcherClass` |
| `components.css` | ✅ 清空为迁移占位（规则已全部迁出） |

### 第 25 步（全局 Toast + 删除 components.css）

| 项 | 状态 |
|----|------|
| `lib/toast-ui.ts` | ✅ `AppToastStack` CVA + Tailwind |
| `feedback.css` | ✅ 仅保留 `app-toast` Transition 钩子 |
| `theme.css` | ✅ 暗色 toast 并入 item class |
| `main.css` | ✅ 移除空 `components.css` import（文件已删） |

### 第 26 步（utilities 删除 + 文档/回归清单）

| 项 | 状态 |
|----|------|
| `pageContainerFluidClass` | ✅ 替代 `.tp-container-fluid` |
| `utilities.css` | ✅ 已删，`main.css` 不再 import |
| 文档勘误 | ✅ 第 13 / 21 步过时描述已改 |
| README | ✅ 前端 UI 栈与迁移文档链接 |
| 总纲 | ✅ [UI-REDESIGN-PLAN.md](./UI-REDESIGN-PLAN.md) |

### 迁移完成（第 4～26 步）

- **样式入口**：`tokens.css` + `tailwind.css` + 领域 CSS（`chat-rich-content.css`、`feedback.css`）+ `lib/*-ui.ts`
- **仍有意保留的 `tp-*` 类名**：页面 marker（`pageMarker*`）、`chat-message-panel` / `tp-subtle-scrollbar` 等全局滚动与富文本钩子
- **面板/嵌套块**：`lib/surface-ui.ts`（`surfacePanelClass`、`surfaceNestedBlockClass`）；Chat 主卡 flex 链在 `lib/chat-ui.ts` 的 `chatMainCardClass`
- **Overlay API**：`Sheet` 支持 `rootClass`（PreviewDrawer 顶栏偏移）；Confirm 仍用 Dialog 基元

主题与语言专项审计见 [THEME-I18N-AUDIT.md](./THEME-I18N-AUDIT.md)。一致性 / 显示 / API 走查见 [CONSISTENCY-AUDIT.md](./CONSISTENCY-AUDIT.md)。

### 发版前自动化门禁

```bash
cd frontend
npm run quality:release        # i18n + copy + native-dialog + production build
npm run test:e2e:install       # 首次：安装 Chromium
npm run quality:release:full     # 上述 + Playwright 壳层/关键页冒烟
```

Playwright 覆盖：

- 壳层（侧栏、抽屉、主题）、Chat/Config/Cases 首屏（`e2e/shell.spec.ts`）
- Cases 导出/筛选、Documents 子 Tab 与历史类型/优先级筛选（`e2e/ui-regression.spec.ts`）
- Chat Markdown 表格与代码块（`e2e/ui-regression.spec.ts` + `/api/**` 最小桩，无需真实后端）

**仍建议人工点测**：PreviewDrawer 大文件、真实联调流式 Chat、Config Provider 保存、Knowledge 向量关闭联调等。

### 与 Vben Pro 的差异（刻意范围）

| Vben 能力 | 本项目 |
|-----------|--------|
| 动态后端菜单 / 权限路由工厂 | 静态 `navigation.ts` + 现有业务路由 |
| 多 Tab 页签 + 全局 KeepAlive | 模块内 `PageTabs` + 子路由 `KeepAlive`（Cases/Documents/Knowledge Shell） |
| ProTable / Form 全家桶 | `BaseTable` + `TableFilter*` + `Tp*` 包装 shadcn 基元 |

不计划整包迁入 Vben；仅在交互层对齐「侧栏 + Tab + 表格工具栏」模式。

### 手工回归清单（发版前建议）

| 区域 | 检查点 |
|------|--------|
| 壳层 | 侧栏折叠、`<1200px` 抽屉、语言切换、面包屑；模块 Tab 切换后返回上一 Tab 状态（KeepAlive） |
| Dashboard | 刷新、KPI/活动列表、暗色主题 |
| Cases | 筛选分页、导出格式下拉、同步后行高亮、PreviewDrawer |
| Documents | 需求分析高亮、History、上传 |
| Knowledge | 向量关闭 banner + gate、文件列表滚动、上传/检索 |
| Chat | 会话分页、消息 Markdown（代码/表格/复制）、composer、页级 notice toast |
| Config | 表单 dirty、Provider 面板开关/chip、保存后 feature flags |
| 全局 Toast | 右下角 success/danger、自动消失与关闭 |

## 迁移 Sign-off（规划关闭）

**Epic 状态：已关闭**（第 4～26 步 + 上文「审计对齐」已交付）。

| 条件 | 状态 |
|------|------|
| 迁移步骤 4～26 | ✅ 见上文各步清单 |
| 总纲与非目标 | ✅ [UI-REDESIGN-PLAN.md](./UI-REDESIGN-PLAN.md) |
| 自动化门禁 | 发版前执行 `quality:release:full` + api-contract + pytest snapshots（见「发版前自动化门禁」） |
| 真后端签核 | [RELEASE-CHECKLIST.md](./RELEASE-CHECKLIST.md)（每次发版更新；**UI epic 关闭** 要求至少 **一次** 已填记录） |

**完成定义**：与 UI-REDESIGN-PLAN 第 5 节一致——代码已交付 + 自动化绿 + 清单至少签核一轮。  
**非目标**：不整包 Vben、不做全局多 Tab、不做动态后端菜单（见「与 Vben Pro 的差异」）。

## 添加 shadcn 组件

```bash
cd frontend
npx shadcn-vue@latest add button
```

未使用 CLI 时，可复制 [shadcn-vue](https://www.shadcn-vue.com/) 文档中的组件到 `src/components/ui/`，并沿用 `@/lib/utils` 与现有 CSS 变量。

## 注意

- 暗色主题仍由 `[data-theme="dark"]` 驱动，与 Tailwind `darkMode: ['selector', '[data-theme="dark"]']` 一致。
- 旧类名（`tp-*`）与 Tailwind 长期并存；新样式优先 Tailwind + token，避免重复定义颜色。
