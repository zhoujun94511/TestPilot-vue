# 联调 / Staging UI 手检清单（P2-07）

后端与向量检索可用时，按本清单补完 v2 审计中**无法在无 API 环境验证**的项。建议 **Light + Dark 各走一遍**，并记录截图或缺陷单号。

## 1. 文档模块

- [ ] `/documents/upload`：选择文件、上传进度、成功/失败 Toast
- [ ] `/documents/manage`：满表分页、行选中、BulkBar、「更多」菜单各操作
- [ ] 描述列：`TpTruncateText` 悬停与键盘聚焦（Tab 到单元格内文本）
- [ ] 预览 Drawer：长文、截断提示、关闭与滚动
- [ ] 分析侧栏：加载/错误/空态、生成用例跳转
- [ ] `/documents/history`：筛选、类型/优先级、行操作
- [ ] ConfirmDialog：删除/批量删除确认与取消

## 2. 知识库

- [ ] `/knowledge/upload`、`/knowledge/files`：列表满数据、向量关闭 Banner
- [ ] 文件描述 Tooltip、预览 Drawer
- [ ] `/knowledge/search`：有结果 / 无结果 / 向量不可用

## 3. 测试用例

- [ ] `/cases/generate`：单次/批量 Tab、分号拆分、生成成功结果区
- [ ] `/cases/manage`：表格、批量栏、导出、编辑/删除 Dialog

## 4. Chat

- [ ] 会话列表、重命名、新建、导出、清空
- [ ] 流式/非流式、Markdown 表格与代码块复制（深浅色）
- [ ] 后端不可用 → 顶栏 hint + 侧栏重试（与 e2e 桩行为一致）

## 5. 配置中心

- [ ] 分类加载、切换、脏数据保存、导入/导出
- [ ] 各表单项：focus、disabled、校验错误色

## 6. 总览

- [ ] 满 KPI、系统状态四格、活动流
- [ ] 部分接口失败：仅顶栏 partial Banner + 一次重试刷新（无区块重复重试）

## 7. 全局

- [ ] 主题切换后浮层/表格/输入框无「残留浅色」
- [ ] 1280 / 390 视口：侧栏、抽屉、弹窗不溢出
- [ ] 键盘：主导航、Tab 列表、Dialog 焦点陷阱

## 自动化（本地无后端）

```bash
cd frontend
npm run test:e2e
```

含 `ux-audit-followup.spec.ts`：kicker、backend hint、总览错误合并、文档 Tooltip（API 桩）。
