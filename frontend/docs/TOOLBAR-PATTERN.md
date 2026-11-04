# 页面顶栏与批量操作约定

与审计结论对齐，列表/管理类页面统一使用 **PagePanel 标题区 + 精简顶栏 + 溢出菜单 + 批量条**。

## PagePanel 标题

- **`title`**：当前 Tab 或模块名（如 `documents.tabs.manage`）。
- **`subtitle`**：一句说明（`* .toolbar.*Lead`），描述本页主流程；避免空 header 或把说明堆在按钮旁。

## 顶栏常驻（`pageToolbarStripClass`）

- **整组一条外框**（圆角 + 浅底 + 边框），内部控件**不再**各自套边框；避免「只有开关有框、按钮没框」的割裂感。
- 目标：**一眼能扫完**，约 **≤3 个常驻控件** + **⋯ 溢出**。

| 角色 | 典型控件 |
|------|----------|
| 导航/返回 | ghost **sm** |
| 刷新 | ghost **sm** |
| RAG 等 | `toolbarInlineSwitchClass` 内联 **TpSwitch**（无单独外框） |
| 主操作 | primary **sm**（与次要同高 `h-8`） |
| 更多动作 | **ToolbarOverflowMenu**（ghost ⋯，与刷新同风格） |

不要再用 `toolbarActionStackClass` 多簇并排堆按钮。

## ToolbarOverflowMenu

- 薄封装 **[shadcn-vue `DropdownMenu`](https://www.shadcn-vue.com/docs/components/dropdown-menu)**（reka-ui）：`align="end"`、默认 **⋯ 图标**触发；浮层样式见 `src/lib/dropdown-ui.ts`（与 PagePanel 同源 token，非 Tailwind 默认 `shadow-md`）。
- 槽内使用 `DropdownMenuItem` / `DropdownMenuRadioGroup` 等，**不要**在菜单里塞大块表单或 `TpSwitch`。
- **RAG / 生成选项**：顶栏 `toolbarInlineSwitchClass` 内联展示（仅间距，不加第二道边框）。

## ToolbarBulkBar

- **仅在有行选中时显示**（`count > 0`）。
- 放批量分析、批量删除、危险操作；提供 `@clear` 清空选中（对应 i18n `common.toolbar.clearSelection`）。
- 可选自定义 `count-label`（如需求历史选中数）。

## 已落地页面

| 页面 | 常驻 | 更多 | Bulk |
|------|------|------|------|
| Documents 管理 | 刷新 + 生成 | RAG / 分析 / 结果 / 导出 | 分析当前 + 删除 |
| Documents 历史 | 返回 + 刷新 + 生成 | 生成设置（RAG） | 删除需求 |
| Knowledge 文件 | 刷新 | 重建索引、关闭预览 | 批量删除 |
| Cases 管理 | 刷新 + 导出 | 格式 + 模板下载 | — |
| **Config 中心** | 刷新 / 导入 / 导出（顶栏）；分区 reload + 保存（底栏） | — | — |
| **AI Chat** | `ActionBar`：新会话 / 刷新 / 导出 / 清空；composer 发送条 | 模板区 select + 插入 | — |

`ActionBar` 的 `#actions` 已自动包一层 `pageToolbarStripClass`（见 `ActionBar.vue`）。

## 组件与样式

- `ToolbarOverflowMenu.vue`、`ToolbarBulkBar.vue`
- `frontend/src/lib/page-chrome-ui.ts`：`pageToolbarStripClass`、`toolbarOverflow*`、`toolbarBulkBar*`

## 扩展新页 checklist

1. Panel 设 `title` + `subtitle`（新增 `*.toolbar.*Lead` 文案）。
2. `#actions` 内仅 `pageToolbarStripClass` + Overflow。
3. 批量/危险操作进 BulkBar，并实现 `clear*Selection()`。
4. 配置类开关不进顶栏常驻，进「更多」或表单区。
