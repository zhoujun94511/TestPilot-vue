# Config Center

TestPilot manages runtime settings through the web **Config Center**. Priority: **Config Center > `.env` > defaults in `config/settings.py`**. Most saved values apply immediately without restarting Flask.

## Initialization

You do not need to run a script for a new install. The first `python run.py` (or `python scripts/init_first_run.py`) writes the missing config items and validation rules, and records the first-run marker. Later starts do not overwrite values you changed.

Only run `python scripts/init_config_center.py --force` to restore factory defaults. It wipes config rows and writes built-in defaults, including `DEFAULT_COMPANY=OPENAI`, which overrides the provider in `.env`. The Chinese page [CONFIG-CENTER.md](CONFIG-CENTER.md) has the same content.

## Frontend structure

| Capability | Description |
|------------|-------------|
| Category sidebar | Matches `GET /api/config/categories`. The current item is highlighted; there is no separate "current category" label |
| Category forms | Edit by category. Sensitive values are masked and can be shown or hidden |
| Export / import | Top bar (hidden on the **Recent config changes** page) |
| Recent config changes | Sidebar item (internal id `audit_trail`), read-only list with its own refresh |

Page implementation: `frontend/src/views/ConfigCenterView.vue`. Navigation and audit constants: `frontend/src/lib/config-ui.ts`.

## REST API (prefix `/api/config`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/categories` | List config categories |
| GET | `/<category>` | All items in a category |
| POST | `/<category>` | Batch update a category |
| GET | `/item/<key>` | Single item |
| PUT | `/item/<key>` | Update one item |
| DELETE | `/item/<key>` | Delete an item |
| GET | `/export` | Export |
| POST | `/import` | Import |
| GET | `/audit-logs` | Audit log (query params `limit` / `offset`) |
| POST | `/validate/<key>` | Validate one item |

Implementation: `blueprints/config_center.py`. Business logic: `services/config_center_service.py`.

## Token limits and session caps (summary)

Chat, case/requirement generation, and session cap keys are maintained under **AI model settings**. For UI and runtime behavior, see [TOKEN-CONFIG.md](../frontend/docs/TOKEN-CONFIG.md) (Chinese).

- Near the limit (default 80%): `GET /api/stats/token-session` and a front-end toast warning
- Over the limit: the API returns 429 with a `message_key` (for example `common.tokenSession.exceededTokens`). The text is maintained in i18n

## Integration and release checks

- Integration smoke tests: [DEV-INTEGRATION.md](DEV-INTEGRATION.md) (Chinese), including `/api/config/categories` and token pytest
- Manual checks: [RELEASE-CHECKLIST.md](../frontend/docs/RELEASE-CHECKLIST.md) (Chinese), including the config matrix for the audit page and token section
- API contract: `scripts/check_api_contract.py` and `npm run quality:api-contract` in `frontend/`
