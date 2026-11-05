# Authentication and RBAC (department data isolation)

Chinese version: [AUTH-RBAC.md](AUTH-RBAC.md).

This page matches the current login, roles, department isolation, and database migrations in `services/auth_*`, `services/data_scope.py`, and `blueprints/auth.py`.

## Goals

- **Login is required by default.** First-time setup creates one super admin, one admin, and one regular user. People choose which account to sign in with. The UI does not show the default accounts. Cases, requirements, the knowledge base, chat, export, and stats are isolated by **role + department**.
- **Single-user anonymous mode.** `AUTH_REQUIRE_AUTH=false` skips the login requirement, and data-scope filters do not apply.
- **Config Center.** Only **super_admin** can change runtime secrets and model settings.

## Environment variables (`.env`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `AUTH_REQUIRE_AUTH` | `true` | When `true`, every `/api/*` route except the public auth routes requires a signed-in user |
| `AUTH_REGISTER_ENABLED` | `false` | When `true`, `POST /api/auth/register` is open (new accounts are **user** in the default department) |
| `AUTH_REGISTER_REQUIRE_APPROVAL` | `true` | Self-registered accounts start **inactive** until an admin enables them. `false` lets them sign in immediately and read/write the default department, including older rows |
| `AUTH_TRUST_PROXY_HEADERS` | `false` | When `true`, the client IP is the first `X-Forwarded-For` hop (login/register rate limit and audit IP). Turn this on only behind a trusted reverse proxy |
| `AUTH_BOOTSTRAP_SUPER_USERNAME` | `admin` | Super-admin username created on first run |
| `AUTH_BOOTSTRAP_SUPER_PASSWORD` | (empty) | Super-admin password. Empty uses the built-in `TestPilot@2026`. Logs warn, and do not print the password |
| `AUTH_BOOTSTRAP_SUPER_EMAIL` | (empty) | Optional email |
| `AUTH_BOOTSTRAP_ADMIN_USERNAME` | `manager` | Admin username created on first run |
| `AUTH_BOOTSTRAP_ADMIN_PASSWORD` | (empty) | Falls back to the super-admin password, then to the built-in password |
| `AUTH_BOOTSTRAP_USER_USERNAME` | `member` | Regular-user username created on first run |
| `AUTH_BOOTSTRAP_USER_PASSWORD` | (empty) | Same fallback as the admin password |

Copy the template with `cp .env.example .env`.

## Roles (summary)

| Role | Data scope | Typical access |
|------|------------|----------------|
| **super_admin** | Whole site | Config Center, every department, knowledge rebuild `clear_all`, platform stats health/logs |
| **admin** | Own department | User management (department **user** accounts), export, department business data |
| **user** | Own department / own chats | Read and write visible business data and export it. **No** Config Center |

Chat: `admin` sees department sessions. `user` mainly sees sessions whose `owner_user_id` / `user_id` matches them.

## Default accounts

| Account | Created automatically | Password |
|---------|----------------------|----------|
| **super_admin** (default `admin`) | Once, on first run | `AUTH_BOOTSTRAP_SUPER_PASSWORD`, otherwise `TestPilot@2026` |
| **admin** (default `manager`) | Once, on first run | `AUTH_BOOTSTRAP_ADMIN_PASSWORD`, otherwise the super-admin password |
| **user** (default `member`) | Once, on first run | `AUTH_BOOTSTRAP_USER_PASSWORD`, otherwise the super-admin password |

After the `app_bootstrap_markers.first_run` marker is written, later starts do not recreate deleted accounts and do not reset passwords. The login page does not prefill or mention these accounts. An existing username is skipped: role and password stay as they are.

## Database and migrations

### Tables

- **Auth:** `departments`, `users`, `user_sessions` (`models/auth_models.py`)
- **Scope columns:** `dept_id` / `owner_user_id` on `test_cases`, `requirements`, `rag_file_records`, `chat_sessions`, `llm_usage_logs`, plus `user_id` on LLM usage logs

### Migration entry points

1. **App start:** `create_app()` → `init_database()` → `run_auth_migrations()`, then `run_first_run_bootstrap()` only when the marker is missing.
   - `ensure_scope_columns()` adds missing SQLite columns on every start. It only adds columns.
   - No marker: create the three accounts (skip existing usernames, do not change them), fill missing Config Center keys (do not overwrite), then write `first_run`.
   - Marker present: skip account and config seeds.
   - `backfill_legacy_dept_id()` / LLM usage backfill.

2. **CLI:** `python scripts/init_first_run.py` uses the same marker. It does not start the server and does not wipe the vector store.

3. **Legacy:** `scripts/init_db.py migrate` / `full-migrate` maintain older business-table shapes. RBAC columns follow **`run_auth_migrations`**. If both exist, run both, or start the app once through `create_app`.

### Ownership on write

Business writes call `stamp_ownership()` when a user is signed in and auth is required. That fills `dept_id`, `owner_user_id`, and related fields. Document upload also writes `dept_id` / `owner_user_id` into `.meta.json`.

## API gates

- **Global:** `install_auth_gate` (`services/auth_gate.py`). Public paths: `/api/auth/login`, `register`, `check-auth`.
- **Config Center:** blueprint `before_request`, super_admin only.
- **Export:** any signed-in user can export cases, requirements, chats, and stats they can already see. Queries are filtered by role and department.
- **Record scope:** lists and stats use `apply_data_scope`. A single row uses `can_access_record`. Files on disk use `can_access_document_filename`.
- **Vector search:** the SQLite vector store does not apply a `filter` argument. Department isolation happens on the result set. Knowledge search uses `filter_knowledge_search_results`. Chat RAG, reply suggestions, case-generation RAG, and `search_with_score_threshold` pass through `filter_scoped_retrieval_items` before the prompt (matched by chunk metadata `file_id`). New retrieval entry points must use that filter. Chunks without `file_id` are dropped.
- **Chat reply suggestions:** keyword-added case and requirement context uses `scoped_cases_query` / `scoped_requirements_query`.
- **Knowledge dedup:** hash lookup stays inside the caller's visible files. Different departments may upload the same file.

Main HTTP prefixes: `/api/auth/*`, `/api/cases`, `/api/documents`, `/api/knowledge`, `/api/chat`, `/api/export`, `/api/stats`, `/api/config`.

## Username and password policy

`validate_username` / `validate_password` in `services/auth_service.py` are used by `create_user`, registration, admin create/reset, and the user's own password change.

| Rule | Value |
|------|-------|
| Username length | **3–64** characters after trim |
| Username characters | Letters, digits, Han characters, and `. _ - @`. Username and email uniqueness is case-insensitive |
| Email | Optional. When set, it must look like `x@y.z` and be at most 255 characters |
| Password length | **8–128** characters |
| Complexity | On by default (`AUTH_PASSWORD_REQUIRE_COMPLEXITY=true`): at least one letter, one digit, and one non-alphanumeric symbol |
| Lockout | `AUTH_LOCK_ENABLED`: after `AUTH_LOCK_MAX_FAILURES` failures (default 5), lock for `AUTH_LOCK_DURATION_SECONDS` (default 900) |
| Audit | `AUTH_AUDIT_ENABLED` writes login, logout, password changes, and user-admin actions to `auth_audit_logs`. Super admins read them with `GET /api/auth/audit-logs` and the User management audit tab |
| Manual unlock | Super admin `POST /api/auth/users/<id>/unlock`, and the Unlock button in User management |
| Vector metadata | Failures set `rag_file_records.vector_meta_pending=1`. A background job retries every `VECTOR_METADATA_RETRY_INTERVAL_SECONDS` seconds (default 300, `0` disables it) |

Registration, user-admin create, and password change/reset follow the same rules (`frontend/src/utils/authCredentials.ts`). Whether complexity is required comes from `password_complexity_required` on `check-auth`.

## Self-registration and account protection

- Registration writes audit event `user_registered` (`pending_approval` or `role=user`).
- Inactive or pending accounts: a correct password returns 403 `auth.message.accountInactive` and records `login_inactive`. A wrong password stays a normal failure and does not reveal account state.
- At least one active super_admin must remain. Demoting or disabling the last one returns 400 `auth.message.lastSuperAdmin`.
- User management can delete an account (`DELETE /api/auth/users/<id>`). You cannot delete the account you are signed in with, or the last super admin (400 `auth.message.cannotDeleteLastSuperAdmin`). Cases, requirements, and chats stay after the account is deleted.
- An admin update validates every field before writing. One invalid field rejects the whole update. A wrong parameter type returns 400.
- Signed-in users can call `/api/export/*` and stats export. Export follows data scope: a regular user gets their department's cases and requirements and their own chats, not another department's rows.
- A 401 from any non-`/auth/*` API clears the client session, returns to the login page with "session expired", and sends the user back to the original page after sign-in.

## Frontend

- The login page and `stores/auth.ts` stay in sync with `/api/auth/check-auth`.
- Route `meta.roles`: `/admin/users` is super_admin + admin. Config routes are super_admin only (same as `canSeeConfigCenter`).

## Manual first run

```bash
python scripts/init_first_run.py
```

`scripts/seed_demo_users.py` is a compatibility entry point for the same marker logic. It no longer creates `dept_admin` / `demo_user`. If the marker already exists, neither script changes data.

## Tests

Lightweight RBAC (no full LLM stack):

```bash
pytest tests/test_first_run_bootstrap.py tests/test_rbac_integration_light.py tests/test_auth_rbac.py tests/test_password_policy.py tests/test_register_flow.py -q
```

RAG result filtering and document-analysis path limits: `pytest tests/test_scope_and_provider_guards.py -q`.

## System status API

For anyone who is not super_admin, `GET /api/stats/system-status` returns `performance.status=limited` and `limited_visibility=true`. CPU, memory, and disk fields are `null` (the host is not sampled). `knowledge.vectors` is the chunk count of knowledge files that user can see, not the global vector total. The dashboard "system performance" card says it is visible to super admins only.

## Production checklist

- [ ] `AUTH_REQUIRE_AUTH=true`
- [ ] Set a strong random `AUTH_BOOTSTRAP_SUPER_PASSWORD` before the first empty-database start, or change the super-admin password afterward
- [ ] Leave `AUTH_REGISTER_ENABLED` off unless you intend to open registration. If it is on, keep `AUTH_REGISTER_REQUIRE_APPROVAL=true`
- [ ] Set `AUTH_TRUST_PROXY_HEADERS=true` only behind a reverse proxy
- [ ] Confirm `AUTH_LOCK_*`, `AUTH_AUDIT_ENABLED`, and `AUTH_PASSWORD_REQUIRE_COMPLEXITY` match the security policy
- [ ] Login lock and rate limit are in-process. For more than one instance, put a WAF or gateway limit in front
- [ ] Confirm `scripts/init_db.py init`, or at least one normal start, has applied the RBAC column migrations
- [ ] Create department accounts in User management. Do not rely on a demo seed script
