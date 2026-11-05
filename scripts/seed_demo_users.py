#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容入口：转到首次初始化。

三类账号由首次初始化写入（admin / manager / member）。
游标已存在时直接退出，不补建、不重置密码。

用法：
  python scripts/init_first_run.py
  python scripts/seed_demo_users.py
"""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def _minimal_app():
    """仅 DB + 认证迁移，避免 create_app() 拉取 LLM/chat 等重依赖。"""
    from flask import Flask

    from config.settings import settings
    from models.models import db

    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=settings.SQLALCHEMY_DATABASE_URI,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=getattr(settings, 'SECRET_KEY', 'seed-demo-users'),
    )
    db.init_app(app)
    return app


def main() -> int:
    from models.config_models import ConfigAuditLog, ConfigItem, ConfigValidationRule  # noqa: F401
    from models.models import db
    from services.auth_migrations import run_auth_migrations
    from services.first_run_bootstrap import run_first_run_bootstrap

    app = _minimal_app()
    with app.app_context():
        db.create_all()
        run_auth_migrations()
        status = run_first_run_bootstrap()
    if status == 'skipped':
        print('已完成过首次初始化，未修改账号或配置。')
        return 0
    if status == 'completed':
        print('首次初始化完成。账号和密码见 README「首次登录」，界面不会提示。')
        return 0
    print('首次初始化未完成。已有数据不会被清空。')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
