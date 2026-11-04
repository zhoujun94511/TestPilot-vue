# 主题与 i18n 审计（2026-03）

## 主题机制

| 项 | 实现 |
|----|------|
| 切换 | `useAppStore().setTheme('light' \| 'dark')`，顶栏按钮 `DefaultLayout.toggleTheme` |
| DOM | `main.ts` → `document.documentElement.dataset.theme` + `colorScheme` |
| Tailwind 暗色 | `tailwind.config.js` → `darkMode: ['selector', '[data-theme="dark"]']` |
| Token | `tokens.css`：`:root` 与 `[data-theme="dark"]` 覆盖 `--tp-*` / shadcn 别名 |

## 审计结论（深浅一致性）

### 已对齐

- 大部分页面/layout 使用 `var(--tp-*)` 或 Tailwind `bg-background` / `text-foreground` / `bg-muted`，随 token 切换。
- `PageNoticeBanner`（页级 toast）、`AppToastStack`、`BaseTable`、`PagePanel` 等已带 `dark:` 或 token 混色。
- `PreviewDrawer`、`TpCard`、表单 `field-control` 依赖 surface/page token。

### 已修复（本次）

| 问题 | 处理 |
|------|------|
| `switch-ui` 引用不存在的 `--tp-color-text-100/200/300` | 改为 `border` / `muted` / token 别名 |
| 多处 `--tp-color-primary-500`、`--tp-surface-raised`、`text-700/800` 未定义 | 在 `tokens.css` 增加别名（含 dark 覆盖） |
| 页级 toast 内 ghost 按钮混 `#ffffff` 且无 dark | `notice-ui` 改为 surface/subtle/page 混色 + `dark:` hover |
| Provider 开关圆点 `bg-white` | 改为 `--tp-bg-surface` + shadow |

### 仍须知（非 bug，但视觉上有意区分）

| 区域 | 说明 |
|------|------|
| `notice-ui` 页级 toast | **浅色模式**用浅粉/浅黄等底；**深色模式**用 `dark:bg-[#3a1e24]` 等独立色板——属成对设计，不是漏写 dark |
| `notice-ui` 图标圆点 | 使用 `text-white` 图标字 on 饱和色底，浅/深共用 |
| 硬编码 `#` 色 | 仅集中在 notice _tone_ CVA；均已配 `dark:` 变体 |

### 建议发版前手测

1. 浅色 ↔ 深色各切一次，停留 Dashboard / Cases 表格 / Chat 消息 / Config 表单 / 知识库列表。
2. 触发 **页级 PageNoticeBanner**（warning/danger）与 **AppToastStack**，看 ghost/关闭按钮与背景。
3. Chat 中带代码块/表格的 Markdown 在两种主题下对比度。

---

## 语言（i18n）

### 支持范围

| Locale | 说明 |
|--------|------|
| `zh-CN` | **简体中文**（唯一中文 locale） |
| `en` | 英文 |

**不支持繁体中文（`zh-TW` / `zh-HK`）**：无 `messages['zh-TW']`、无独立繁体资源；界面「中文」指简体。语言切换按钮的 `aria-label` 会附带 `common.language.unsupportedTraditional` 说明。

### 切换路径

| 入口 | 行为 |
|------|------|
| 顶栏 `DefaultLayout` | `zh-CN` ↔ `en`，按钮文案 `简体` / `EN` |
| `LanguageSwitcher.vue` | 同上（与顶栏逻辑一致；当前壳层使用顶栏按钮） |
| 持久化 | `localStorage.testpilot_locale` + Pinia `appStore.locale` |
| 与 vue-i18n | `main.ts` / `App.vue` watch `appStore.locale` → `i18n.global.locale` |
| `document.documentElement.lang` | 随 locale 更新（`main.ts`、`App.vue`、路由守卫） |
| API | `Accept-Language`（`http.ts` / chat 流）；后端 `x-testpilot-locale` 可回写 locale |

### 切换正确性结论

- **简体 ↔ 英文**：逻辑正确，存储与 i18n 同步。
- **繁体**：**未实现**；若产品需要繁中，需新增 `zh-TW` message 包、扩展 `Locale` 类型与三态/下拉切换 UI。

### 文案说明

- `common.language.zhShort` = **「简体」**（避免与繁体混淆）
- `common.language.unsupportedTraditional`：说明仅简体+英文（可用于关于/帮助，当前未强制展示）

---

## 后续可选

- 三语言下拉（简体 / 繁体 / EN）与 `zh-TW` 资源。
- 将 notice _tone_ 的 hex 色板逐步改为「仅 token + color-mix」以减少硬编码。
- E2E：主题切换 + locale 切换快照测试。
