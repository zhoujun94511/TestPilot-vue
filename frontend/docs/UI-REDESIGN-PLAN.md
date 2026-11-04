# TestPilot 前端 UI 重设计总纲

> 轻量总纲：串联现有文档，定义「规划完成」与发版签核，**非**大厂五段式 + 设计委员会流程。

## 1. 目标

- 在 **不整包迁入 vue-vben-admin** 的前提下，将管理台 UI 统一到 **Tailwind + design token + shadcn-vue 基元 + 自研 `Tp*` / 壳层**。
- 交互层对齐常见 Admin 模式：侧栏导航、模块内 Tab、表格工具栏与筛选、确认框/抽屉、主题与 i18n。
- 后端 **非必要不改**；前端通过静态路由与现有 Flask API 契约工作。

## 2. 范围（已交付）

| 块 | 说明 | 详细文档 |
|----|------|----------|
| 迁移 4～26 步 | 组件/表格/表单/布局/Toast/utilities 收口 | [UI-MIGRATION.md](./UI-MIGRATION.md) |
| 品牌 | Logo、色板、图标生成 | [BRAND.md](./BRAND.md) |
| 壳层 | `DefaultLayout`、`shell-ui.ts`、`navigation.ts` | UI-MIGRATION「审计对齐」 |
| 主题 / i18n | token、暗色、942 keys | [THEME-I18N-AUDIT.md](./THEME-I18N-AUDIT.md) |
| 一致性 / 显示 / API | 静态审计 + GET 快照 | [CONSISTENCY-AUDIT.md](./CONSISTENCY-AUDIT.md) |
| UX 审计落地 | Batch 1～2 体验债 | [UX-AUDIT-IMPLEMENTATION.md](./UX-AUDIT-IMPLEMENTATION.md) |
| 自动化门禁 | i18n、build、audit、E2E、api-contract、pytest | `package.json` → `quality:release:full` |

## 3. 非目标（刻意不做）

- **Vben Pro 整包**：动态后端菜单、全局多 Tab 工作台、ProTable/Form 全家桶。
- **Figma 全稿 + 正式设计评审签字**（无合规硬性要求时）。
- **用 E2E 桩完全替代真后端联调**（流式 Chat、403 向量、Config 保存、大 Preview 等仍靠人工清单）。

与 Vben 的差异表见 [UI-MIGRATION.md](./UI-MIGRATION.md#与-vben-pro-的差异刻意范围)。

## 4. 参考

- [shadcn-vue](https://www.shadcn-vue.com/)：基元组件与 token 语义。
- [vue-vben-admin](https://github.com/vbenjs/vue-vben-admin)：侧栏 + Tab + 表格工具栏等 **交互参考**，非依赖库。

## 5. 完成定义（Sign-off）

满足以下 **全部** 即视为 **UI 重设计 / UI-MIGRATION 规划已关闭**：

1. **代码**：第 4～26 步及 UI-MIGRATION「审计对齐」项已合入主分支（见 UI-MIGRATION 各步 ✅）。
2. **自动化**：`cd frontend && npm run quality:release:full` 与 `npm run quality:api-contract`、根目录 `pytest tests/test_api_get_snapshots.py -q` 在 CI 或发版前本地 **绿**。
3. **发版签核**：至少一次填写 [RELEASE-CHECKLIST.md](./RELEASE-CHECKLIST.md)（真后端 + 关键路径点测）；自动化绿 **不能** 替代第 3 条中的手工矩阵。

**设计评审替代**：发版负责人确认已读 CONSISTENCY-AUDIT + 清单签核，无需单独签字页。

## 6. 发版流程（每次）

```bash
cd frontend
npm run quality:release:full
npm run quality:api-contract
python -m pytest ../tests/test_api_get_snapshots.py -q
# 启动真后端，按 RELEASE-CHECKLIST 点测并更新表格
```

## 7. 后续若产品改需求

仅在 **书面新需求** 下再评估独立 epic，例如：

- 按钮级权限 + 运营可配菜单 → 动态路由/菜单契约。
- 同时保活大量跨模块 Tab → 全局 Tab 层（不必等于整包 Vben）。
