"""
集成白盒：对关键 GET 在 Flask test_client 下校验 HTTP 200 与 data 层 key 快照。
依赖 create_app + 本地 sqlite（与开发配置一致）；CI 在 pip install 后运行。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "api_get_snapshots.json"


def _load_spec() -> list[dict[str, Any]]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(raw.get("endpoints") or [])


@pytest.fixture(scope="module")
def api_client():
    pytest.importorskip("flask_session")
    from app import create_app
    from config.settings import settings

    # 快照只校验响应结构，不随本机 .env 的 AUTH_REQUIRE_AUTH 变化
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "AUTH_REQUIRE_AUTH", False)
        app = create_app()
        app.config["TESTING"] = True
        yield app.test_client()


def _unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if payload.get("success") is False:
        return {}
    for key in ("data", "feature_flags", "config", "categories", "health"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            return nested
    skip = {"success", "code", "message", "message_key", "error", "error_code", "retryable"}
    return {k: v for k, v in payload.items() if k not in skip and not k.startswith("_")}


@pytest.mark.parametrize("entry", _load_spec(), ids=lambda e: e["path"])
def test_get_response_data_keys(api_client, entry: dict[str, Any]):
    path = entry["path"]
    expected_keys = sorted(entry.get("data_keys") or [])

    response = api_client.get(path)
    assert response.status_code == 200, f"{path} status {response.status_code}"

    payload = response.get_json()
    assert isinstance(payload, dict), f"{path} non-json body"
    assert payload.get("success") is not False, f"{path} success=false: {payload.get('message')}"

    data = _unwrap_data(payload)
    actual_keys = sorted(data.keys())

    if os.environ.get("UPDATE_API_GET_SNAPSHOTS") == "1":
        entry["data_keys"] = actual_keys
        spec = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for i, item in enumerate(spec["endpoints"]):
            if item["path"] == path:
                spec["endpoints"][i]["data_keys"] = actual_keys
                break
        FIXTURE.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pytest.skip(f"updated snapshot keys for {path}")

    for key in expected_keys:
        assert key in data, f"{path}: missing data key {key!r} (have {actual_keys})"
