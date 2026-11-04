# UX 审计结论对齐计划（2026-11-03）

依据 [UI-UX-AUDIT-REPORT-2026-11-03-v2.md](./UI-UX-AUDIT-REPORT-2026-11-03-v2.md) 中**待办项**，结合当前工程（Vue 3 + tokens + Reka UI、无满数据后端）制定可交付计划。

## 原则

- 优先 **全局 token / 壳层 / 公共组件**，再改单页。
- **P2-07**（满数据 e2e）依赖联调环境，本轮仅补充文档说明，不虚构测试。
- 已修复项（P1-01 菜单高亮、P2-01 面包屑）不再重复改动。

## Todo 与审计编号映射

| Todo ID | 审计编号 | 交付物 |
|---------|----------|--------|
| p1-tokens | P1-02、P2-04 | `tokens.css` placeholder / border |
| p2-topbar | P2-02 | `DefaultLayout` 子路由隐藏 kicker |
| p2-tooltip | P2-03 | `TooltipProvider`、`TpTruncateText`、文档/会话列表 |
| p2-dashboard | P2-05 | `DashboardView` 错误合并 + 顶栏重试刷新 |
| p2-config-chat | P2-06 | 配置/Chat 顶栏后端不可用说明 + i18n |
| p3-polish | P3-01~03 | switch token、duration 类名、shell 装饰略收敛 |
| regression | §6 | audit / build / playwright、更新 v2 报告状态 |

## 验收

- `npm run quality:audit`、`npm run build`、`npm run test:e2e` 通过。
- Light/Dark 下 placeholder、边框、菜单、顶栏信息密度可目视或脚本对比度改善。

## 实施状态（2026-11-03）

| Todo | 状态 |
|------|------|
| p1-tokens | ✅ 已完成 |
| p2-topbar | ✅ 已完成 |
| p2-tooltip | ✅ 已完成（文档描述列 + Chat 会话预览） |
| p2-dashboard | ✅ 已完成 |
| p2-config-chat | ✅ 已完成 |
| p3-polish | ✅ 已完成 |
| p2-07 满数据手检 | 📋 [STAGING-UI-CHECKLIST.md](./STAGING-UI-CHECKLIST.md) + API 桩 e2e |
| regression | ✅ audit + build + e2e（含 ux-audit-followup） |
