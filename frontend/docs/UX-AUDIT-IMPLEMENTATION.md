# UX 审计落地记录（Batch 1）

对应会话审计项 **P1/P2**，与 [UI-REDESIGN-PLAN.md](./UI-REDESIGN-PLAN.md) 发版流程并行。

## Batch 1（已完成）

| 审计 ID | 内容 | 变更 |
|---------|------|------|
| UX-P1-01 | 侧栏 Focus | `shell-ui.ts` `navItemClass` → ring-inset |
| UX-P1-07 | 壳层裁切 | `shellRootClass` `overflow-clip` → `overflow-x-clip` |
| UX-P1-02 | ActionBar 约定 | `page-chrome-ui.ts` 注释；Chat 导出改 `ghost` |
| UX-P1-04 | Chat 模板区 | 默认关闭模板 panel；去掉占位段落；i18n 文案 |
| UX-P1-03 | Chat 空会话 | 侧栏 empty 增加「新建会话」按钮；composer 去掉重复「清空会话」 |
| UX-P1-06 | Dashboard 离线 | `showOfflineMetrics` → 未连接/暂无数据，避免 Unknown+0% 墙 |
| UX-P0-02 | Config 加载失败 | `loadCategories` catch 清空 categories，优先 error 态 |
| UX-P1-05 | 输入框回归 | `e2e/field-controls.spec.ts` computed style 断言 |

## Batch 2（已完成）

| 审计 ID | 内容 | 变更 |
|---------|------|------|
| UX-P1-02 | Cases ActionBar | 导出/模板 → `ghost`；刷新 `secondary` 置前 |
| UX-P1-02 | Documents 导出需求 | `secondary` → `ghost` |
| UX-P2-07 | TpSwitch a11y | `aria-labelledby` + 有文案时 ON/OFF 徽章 `aria-hidden`；field 模式 `sr-only` 标签 |

Documents / Knowledge 表格 `truncate` 已带 `:title`；Chat 会话标题已有 `:title`。

## Batch 3（AUD-26 · 已完成）

| 审计 ID | 内容 | 变更 |
|---------|------|------|
| AUD-26-P1-04 | Focus 统一 | `lib/focus-ui.ts`；顶栏/侧栏折叠/Tab/Toast 关闭钮 ring-inset |
| AUD-26-P1-02 | Chat 工具栏 | 无会话时 ActionBar `#lead` 提示文案 |
| AUD-26-P1-03 | Documents 工具栏 | `toolbarActionStackClass` 列表区 \| 生成/导出区分组 |
| AUD-26-P1-05 | Dashboard KPI | overview 失败时 KPI 显示「暂无数据」 |
| 文档 | 复查索引 | `UX-AUDIT-2026-11-02.md` |

## Batch 4（已完成）

| 审计 ID | 内容 | 变更 |
|---------|------|------|
| AUD-26-P1-03 | Knowledge 文件页 ActionBar | 刷新 \| 重建/删除/关闭预览 分组 |
| AUD-26-P1-03 | Documents 历史 ActionBar | 返回+刷新 \| RAG/生成/删除 分组 |
| 工程 | Focus 去重 | `field-control`、`upload-ui`、面包屑链接用 `focus-ui` |
| AUD-26-P1-01 | 发版清单 | `RELEASE-CHECKLIST.md` 增加快速启动命令块 |

## Batch 6（P3 密度 / 装饰 · 2026-11-03）

| 审计 ID | 内容 | 变更 |
|---------|------|------|
| UX-P3-01 | 动效 token | `tokens.css`：`--tp-motion-*`、`--tp-page-block-gap` |
| UX-P3-02 | 减弱动效 | `motion.css` + `prefers-reduced-motion` |
| UX-P3-03 | Chat Markdown | `--tp-rich-code-*`；代码块/表头深色对比；间距 `--tp-space-2` |
| UX-P3-04 | 列表密度 | `stats-ui` p-3.5；Chat 气泡/列表/Composer；Switch field 间距 |
| UX-P3-05 | 排版 | `sectionSubtitle` / `cardSubtitle` `leading-snug` |
| UX-P3-06 | 总览高级指标行 | `dashboardAdvancedMetricRow` 略收紧 |

## Batch 5（进行中）

| 审计 ID | 内容 | 变更 |
|---------|------|------|
| AUD-26-P0 | 停后端 empty 误导 | `BaseTable` 有 `emptyMessage` 且无数据 → `error` 态 + 可选 `@retry`；Knowledge / Documents 历史接入 |
| 工程 | E2E | `e2e/load-error.spec.ts` Knowledge 列表 503 |

- **AUD-26-P1-01**：矩阵勾选 + 表头执行人（需人工，见 `RELEASE-CHECKLIST.md`）
- 可选：axe/Lighthouse 抽样

## 验证

```bash
cd frontend
npm run quality:audit
npm run build
npx playwright test e2e/shell.spec.ts e2e/field-controls.spec.ts
npm run quality:release:full   # 发版前
```
