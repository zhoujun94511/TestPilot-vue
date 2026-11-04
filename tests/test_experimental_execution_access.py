#!/usr/bin/python
# -*- coding: utf-8 -*-
"""实验动作执行记录的访问判定。"""

from types import SimpleNamespace

import pytest

from blueprints import experimental_actions


@pytest.fixture
def as_user(monkeypatch):
    monkeypatch.setattr(experimental_actions, "auth_required", lambda: True)

    def _set(user):
        monkeypatch.setattr(experimental_actions, "current_user", lambda: user)

    return _set


@pytest.mark.parametrize(
    ("user", "record_user_id", "expected"),
    [
        ({"id": 1, "role": "super_admin", "dept_id": 1}, None, True),
        ({"id": 2, "role": "admin", "dept_id": 1}, None, False),
        ({"id": 3, "role": "user", "dept_id": 1}, "", False),
        ({"id": 3, "role": "user", "dept_id": 1}, "3", True),
        ({"id": 2, "role": "admin", "dept_id": 1}, "3", False),
        (None, "3", False),
    ],
)
def test_can_access_execution(as_user, user, record_user_id, expected):
    as_user(user)
    record = SimpleNamespace(user_id=record_user_id)
    assert experimental_actions.can_access_execution(record) is expected
