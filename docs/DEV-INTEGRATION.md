# 前后端联调指南

## 虚拟环境

本项目虚拟环境在仓库根目录 **`.venv/`**。勿在全局 Python 装依赖，也**不要重复创建**第二个虚拟环境。

```powershell
# 已有 .venv 时只更新依赖：
powershell -ExecutionPolicy Bypass -File scripts/setup-venv.ps1

# 激活
.\.venv\Scripts\Activate.ps1
```

- 脚本**优先**使用 `.venv\Scripts\python.exe`；若无则回退 `venv/`（与旧 README 一致）。
- 仅当两者都不存在时才 `python -m venv .venv`。
- 勿在**全局** Python 零散安装；Chroma 误装可用 `scripts/audit-uninstall-global-chroma.ps1`（默认 sqlite 向量，不需要 chromadb）。

Chroma 回滚包见 `requirements-optional-chroma-rollback.txt`（默认勿装）。

## 启动

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-integration.ps1
```

或激活 `.venv` 后：

```powershell
$env:DEBUG = "true"
$env:PORT = "5001"
python run.py
```

- **界面（热更新）**：http://127.0.0.1:5173  
- **API**：http://127.0.0.1:5001/api/...  

`run.py`（DEBUG）会写入 `frontend/.env.development.local` → `VITE_FLASK_TARGET=http://127.0.0.1:5001`，并拉起 Vite。

## 向量库

默认 **`VECTOR_BACKEND=sqlite`**（`sqlite_vector_store.py`），正常联调**不需要** chromadb / langchain-chroma。

## 首次初始化

不要按 `init_db.py` → `init_vectordb.py --init-vector-db` → `init_config_center.py` 这条顺序做新环境。后两个带清空语义。

```powershell
.\.venv\Scripts\Activate.ps1
copy .env.example .env
python scripts/init_first_run.py
```

或直接 `python run.py`。第一次会建表、写三类账号、写配置中心缺省项、创建向量库文件，并写入游标 `first_run`。再启动不会重做。`init_vectordb.py --init-vector-db` 和 `init_config_center.py --force` 只用于确认要清空的时候。

配置中心说明见 [CONFIG-CENTER.md](./CONFIG-CENTER.md)；词元键见 [../frontend/docs/TOKEN-CONFIG.md](../frontend/docs/TOKEN-CONFIG.md)。

### 登录与 RBAC（多用户联调）

- 完整说明：[AUTH-RBAC.md](./AUTH-RBAC.md)
- 默认 `AUTH_REQUIRE_AUTH=true`。首次初始化账号为 `admin` / `manager` / `member`，密码未设置时都是 `TestPilot@2026`。登录页不提示。
- 白盒：`pytest tests/test_first_run_bootstrap.py tests/test_auth_rbac.py tests/test_password_policy.py -q`

## 常见问题

| 现象 | 处理 |
|------|------|
| 前端全 500 | 用 `run.py` 起 Flask，不要只 `npm run dev` |
| 代理错误 IP | 重新 DEBUG 下运行 `run.py`，或改 `.env.development.local` 为 `127.0.0.1:5001` |
| 5173 占用 | 结束多余 node/Vite，只保留 `run.py` 拉起的一个 |
| 控制台出现 Tailwind `JIT TOTAL` / `Source path: main.css` | 勿把 `DEBUG=true` 传给 Vite；`run.py` 已隔离，单独 `npm run dev` 时不要设 `DEBUG=true` |
| 刚启动几秒 Vite `ECONNREFUSED 127.0.0.1:5001` | 旧版先起 Vite、后 `create_app` 会竞态；新版 `run.py` 先监听 5001 再起 Vite。仍报错则确认 5001 未被占用 |

满数据 UI 手检：`frontend/docs/STAGING-UI-CHECKLIST.md`。

## 联调冒烟（自动化）

后端需已用 `.venv` + `DEBUG=true` 跑起 `run.py`（Flask **5001** + Vite **5173**）。

```powershell
$env:FLASK_BASE_URL = "http://127.0.0.1:5001"
.\.venv\Scripts\python.exe -m pytest tests/test_api_get_snapshots.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_token_config.py -q
.\.venv\Scripts\python.exe scripts/check_api_contract.py
cd frontend; npm run quality:api-contract
cd frontend; node scripts/test-config-infer.mjs
```

PowerShell 抽查（注意文档列表路径为 **`/api/documents/list`**，不是 `/api/documents`）：

```powershell
$base = "http://127.0.0.1:5001"
"/api/stats/health", "/api/config/categories", "/api/documents/list" | ForEach-Object {
  (Invoke-WebRequest -Uri ($base + $_) -UseBasicParsing).StatusCode
}
Invoke-WebRequest -Uri "http://127.0.0.1:5173/api/stats/health" -UseBasicParsing  # Vite 代理
```

### 2026-11-03 本地结果（`.venv`，`VECTOR_BACKEND=sqlite`）

| 项 | 结果 |
|----|------|
| `create_app()` / sqlite 向量 | 通过 |
| 总览 `/api/stats/*`、Vite 代理 `/api/stats/health` | **200** |
| `pytest tests/test_api_get_snapshots.py` | **6 passed** |
| `check_api_contract` / `quality:api-contract` | 无 path/method 不一致 |
| 浏览器：Dashboard、Documents、Config、Chat | 正常渲染，无全页 500 |
| LLM（Qwen Key 未配） | 启动告警；**不影响** REST/壳层联调；Chat 发消息需 Key 或改 Provider |

未在本轮覆盖：上传→分析、流式 Chat、满表 UI — 见 `frontend/docs/STAGING-UI-CHECKLIST.md`。
