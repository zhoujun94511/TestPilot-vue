# 认证与 RBAC（部门数据隔离）

英文版：[AUTH-RBAC.en.md](AUTH-RBAC.en.md)。

本文描述 TestPilot 当前实现的登录、角色、部门隔离与数据库迁移，与代码路径 `services/auth_*`、`services/data_scope.py`、`blueprints/auth.py` 保持一致。

## 设计目标

- **默认要求登录**：首次初始化创建超级管理员、管理员、普通用户各一个，由用户自行选择登录。界面不提示默认账号。用例、需求、知识库、聊天、导出、统计等按 **角色 + 部门** 隔离。
- **单机匿名**：`AUTH_REQUIRE_AUTH=false` 时不强制登录，数据范围过滤不生效。
- **配置中心**：仅 **super_admin** 可改运行期密钥与模型配置。

## 环境变量（`.env`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `AUTH_REQUIRE_AUTH` | `true` | `true` 时除公开 auth 接口外，所有 `/api/*` 需登录 |
| `AUTH_REGISTER_ENABLED` | `false` | `true` 时开放 `POST /api/auth/register`（注册为 **user** + 默认部门） |
| `AUTH_REGISTER_REQUIRE_APPROVAL` | `true` | 自助注册的账号创建为**停用**，管理员在用户管理点「启用」后才能登录；设为 `false` 则注册后立即可用，并能读写默认部门（含历史数据） |
| `AUTH_TRUST_PROXY_HEADERS` | `false` | `true` 时按 `X-Forwarded-For` 首段识别客户端 IP（登录/注册限流、审计 IP）；只在可信反向代理之后开启 |
| `AUTH_BOOTSTRAP_SUPER_USERNAME` | `admin` | 首次初始化的超级管理员用户名 |
| `AUTH_BOOTSTRAP_SUPER_PASSWORD` | （空） | 超管密码；为空时用内置 `TestPilot@2026`。日志只告警，不写出口令 |
| `AUTH_BOOTSTRAP_SUPER_EMAIL` | （空） | 可选邮箱 |
| `AUTH_BOOTSTRAP_ADMIN_USERNAME` | `manager` | 首次初始化的管理员用户名 |
| `AUTH_BOOTSTRAP_ADMIN_PASSWORD` | （空） | 为空时沿用超管密码，超管密码也为空则用内置密码 |
| `AUTH_BOOTSTRAP_USER_USERNAME` | `member` | 首次初始化的普通用户用户名 |
| `AUTH_BOOTSTRAP_USER_PASSWORD` | （空） | 规则同管理员密码 |

复制模板：`cp .env.example .env`

## 角色与能力（摘要）

| 角色 | 数据范围 | 典型能力 |
|------|----------|----------|
| **super_admin** | 全站 | 配置中心、全部门数据、知识库 rebuild `clear_all`、平台级 stats 健康/日志 |
| **admin** | 本部门 | 用户管理（本部门 user）、导出、部门内业务数据 |
| **user** | 本部门 / 本人聊天 | 业务读写与导出（只含本人可见数据），**不可**配置中心 |

聊天：`admin` 看本部门会话；`user` 主要看 `owner_user_id` / `user_id` 匹配的会话。

## 默认账号说明

| 账号 | 是否自动创建 | 密码 |
|------|----------------|------|
| **super_admin**（默认 `admin`） | 首次初始化一次 | `AUTH_BOOTSTRAP_SUPER_PASSWORD`，否则 `TestPilot@2026` |
| **admin**（默认 `manager`） | 首次初始化一次 | `AUTH_BOOTSTRAP_ADMIN_PASSWORD`，否则沿用超管密码 |
| **user**（默认 `member`） | 首次初始化一次 | `AUTH_BOOTSTRAP_USER_PASSWORD`，否则沿用超管密码 |

游标 `app_bootstrap_markers.first_run` 写入后，再启动不会补建被删掉的账号，也不会重置密码。登录页不预填、不提示这些账号。同名用户已存在时跳过，不改角色、不改密码。

## 数据库与迁移

### 表结构

- **认证**：`departments`、`users`、`user_sessions`（`models/auth_models.py`）
- **业务隔离列**：`test_cases`、`requirements`、`rag_file_records`、`chat_sessions`、`llm_usage_logs` 等上的 `dept_id` / `owner_user_id`（及 llm 的 `user_id`）

### 迁移入口（推荐顺序）

1. **应用启动**：`create_app()` → `init_database()` → `run_auth_migrations()`，再按游标决定是否 `run_first_run_bootstrap()`
   - `ensure_scope_columns()`：SQLite `ALTER TABLE` 补列（每次启动，只加列）
   - 无游标时：三类账号（已有同名不改）+ 配置中心缺省项（不覆盖）+ 写入 `first_run`
   - 有游标时：跳过账号和配置种子
   - `backfill_legacy_dept_id()` / `llm_usage` 回填

2. **CLI**：`python scripts/init_first_run.py`（同一套游标逻辑，不启动服务，也不清空向量库）

3. **legacy**：`scripts/init_db.py migrate` / `full-migrate` 主要维护**历史业务表结构**；RBAC 列以 **`run_auth_migrations`** 为准，两者并存时需都执行或至少保证已启动过一次完整 `create_app`。

### 创建数据时的归属

写入业务记录时调用 `stamp_ownership()`（已登录且开启认证）：填充 `dept_id`、`owner_user_id` 等。文档上传另写 `.meta.json` 的 `dept_id` / `owner_user_id`。

## API 门禁

- **全局**：`install_auth_gate`（`services/auth_gate.py`）— 公开路径：`/api/auth/login`、`register`、`check-auth`
- **配置中心**：蓝图 `before_request`，仅 super_admin
- **导出**：已登录用户均可导出自己可见范围内的用例、需求、聊天和统计；查询已按角色与部门过滤
- **数据范围**：列表/统计用 `apply_data_scope`；单条用 `can_access_record`；文档磁盘文件用 `can_access_document_filename`
- **向量检索**：SQLite 向量库不执行 `filter` 参数，部门隔离在结果层完成。知识库搜索用 `filter_knowledge_search_results`；聊天 RAG、回复建议、用例生成 RAG 和 `search_with_score_threshold` 注入提示词前统一经过 `filter_scoped_retrieval_items`（按 chunk metadata 的 `file_id`）。新增检索入口也必须走这一层，缺 `file_id` 的 chunk 会被丢弃
- **聊天回复建议**：按关键词补充的用例、需求上下文走 `scoped_cases_query` / `scoped_requirements_query`
- **知识库去重**：按文件哈希查重只在本人可见范围内查，不同部门可各自上传相同文件

主要 HTTP 前缀：`/api/auth/*`、`/api/cases`、`/api/documents`、`/api/knowledge`、`/api/chat`、`/api/export`、`/api/stats`、`/api/config`

## 用户名与密码策略

统一实现在 `services/auth_service.py` 的 `validate_username` / `validate_password`，并在 `create_user`、注册、管理员开户/重置、用户改密等路径调用。

| 规则 | 值 |
|------|-----|
| 用户名长度 | **3～64** 字符（trim 后） |
| 用户名字符 | 字母、数字、汉字及 `. _ - @`；用户名与邮箱查重**不区分大小写** |
| 邮箱 | 可选；填写时须为 `x@y.z` 格式，最长 255 |
| 密码长度 | **8～128** 字符 |
| 复杂度 | 默认 **开启**（`AUTH_PASSWORD_REQUIRE_COMPLEXITY=true`）：至少 1 字母、1 数字、1 非字母数字符号 |
| 登录失败锁定 | `AUTH_LOCK_ENABLED`：连续失败 `AUTH_LOCK_MAX_FAILURES` 次（默认 5）锁定 `AUTH_LOCK_DURATION_SECONDS`（默认 900s） |
| 操作审计 | `AUTH_AUDIT_ENABLED`：登录/登出/改密/用户管理等写入 `auth_audit_logs`；超管 `GET /api/auth/audit-logs`、前端用户管理「认证审计」Tab |
| 手动解锁 | 超管 `POST /api/auth/users/<id>/unlock`；用户管理页「解锁」按钮 |
| 向量 metadata | 失败标记 `rag_file_records.vector_meta_pending=1`；后台每 `VECTOR_METADATA_RETRY_INTERVAL_SECONDS` 秒重试（默认 300，0 关闭） |

前端注册、用户管理开户、改密/重置与上述规则对齐（`frontend/src/utils/authCredentials.ts`）；是否要求复杂度由 `check-auth` 返回的 `password_complexity_required` 决定。

## 自助注册与账号保护

- 注册写审计事件 `user_registered`（详情 `pending_approval` 或 `role=user`）。
- 待审核/停用账号：密码正确时返回 403 `auth.message.accountInactive` 并记 `login_inactive`；密码错误仍按普通失败处理，不暴露账号状态。
- 至少保留一个启用中的 super_admin：降级或停用最后一个时返回 400 `auth.message.lastSuperAdmin`。
- 用户管理可删除账号（`DELETE /api/auth/users/<id>`）。不能删除当前登录账号；不能删除最后一个超级管理员（400 `auth.message.cannotDeleteLastSuperAdmin`）。用例、需求、聊天记录不随账号删除。
- 管理员更新用户先校验全部字段再写库，任一字段不合法则整次不生效；参数类型不对返回 400。
- 已登录用户都可使用 `/api/export/*` 与统计导出。导出内容跟数据范围走：普通用户拿到本部门用例、需求和本人聊天，拿不到其他部门的记录。
- 前端任一非 `/auth/*` 接口返回 401 时清空登录态，跳回登录页并提示「登录已过期」，登录后回到原页面。

## 前端

- 登录页、`stores/auth.ts` 与 `/api/auth/check-auth` 同步
- 路由 `meta.roles`：`/admin/users` 为 super_admin + admin；配置相关仅 super_admin（与 `canSeeConfigCenter` 一致）

## 手动首次初始化

```bash
python scripts/init_first_run.py
```

`scripts/seed_demo_users.py` 只是兼容入口，调用同一套游标逻辑，不再另建 `dept_admin` / `demo_user`。游标已存在时两个脚本都不改数据。

## 测试

轻量 RBAC（不拉完整 LLM 栈）：

```bash
pytest tests/test_first_run_bootstrap.py tests/test_rbac_integration_light.py tests/test_auth_rbac.py tests/test_password_policy.py tests/test_register_flow.py -q
```

RAG 结果层过滤与文档分析路径限制：`pytest tests/test_scope_and_provider_guards.py -q`。

## 系统状态接口

`GET /api/stats/system-status` 对非 super_admin：`performance` 返回 `status=limited`、`limited_visibility=true`，CPU/内存/磁盘字段为 `null`（不再采样主机指标）；`knowledge.vectors` 为可见知识文件登记的 chunk 数，而不是全局向量库总数。总览页「系统性能」卡片显示「仅超管可见」。

## 生产检查清单

- [ ] `AUTH_REQUIRE_AUTH=true`
- [ ] 设置强随机 `AUTH_BOOTSTRAP_SUPER_PASSWORD` 后**空库首次启动**，或手动改超管密码
- [ ] `AUTH_REGISTER_ENABLED` 按策略关闭；开启时保持 `AUTH_REGISTER_REQUIRE_APPROVAL=true`
- [ ] 部署在反向代理之后才设置 `AUTH_TRUST_PROXY_HEADERS=true`
- [ ] 确认 `AUTH_LOCK_*`、`AUTH_AUDIT_ENABLED`、`AUTH_PASSWORD_REQUIRE_COMPLEXITY` 符合安全策略
- [ ] 多实例部署时登录锁定/限流为**进程内**状态，必要时前置 WAF/网关限流
- [ ] 确认 `scripts/init_db.py init` 或至少一次正常启动已完成 RBAC 列迁移
- [ ] 部门账号通过用户管理分配，勿依赖演示种子脚本
