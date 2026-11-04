#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发环境：确保「超管 + 部门管理员 + 普通用户」三个演示账号（已存在则跳过）。

1. run_auth_migrations：空库时自动创建引导 super_admin（见 AUTH_BOOTSTRAP_*）
2. 若无任何 super_admin，按 SEED_DEMO_SUPER_* 补建
3. 创建部门 admin / user（默认 dept_admin、demo_user）

生产环境请勿使用默认密码。

环境变量（可选）：
  AUTH_BOOTSTRAP_SUPER_USERNAME / AUTH_BOOTSTRAP_SUPER_PASSWORD  空库引导超管
  SEED_DEMO_SUPER_USERNAME   补建超管时的用户名，默认同 AUTH_BOOTSTRAP_SUPER_USERNAME
  SEED_DEMO_SUPER_PASSWORD   补建超管密码，默认同引导逻辑或 TestPilot@2026
  SEED_DEMO_ADMIN_USERNAME   默认 dept_admin
  SEED_DEMO_ADMIN_PASSWORD   默认 DemoAdmin@2026
  SEED_DEMO_USER_USERNAME    默认 demo_user
  SEED_DEMO_USER_PASSWORD    默认 DemoUser@2026

用法：
  python scripts/seed_demo_users.py
"""

from __future__ import annotations

import os
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


def _bootstrap_super_credentials() -> tuple[str, str]:
    username = os.getenv('AUTH_BOOTSTRAP_SUPER_USERNAME', 'admin').strip() or 'admin'
    password = os.getenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', '').strip()
    if not password:
        password = 'TestPilot@2026'
    return username, password


def _print_account_table(
    *,
    super_name: str,
    super_pass_hint: str,
    admin_name: str,
    admin_pass: str,
    user_name: str,
    user_pass: str,
) -> None:
    print()
    print('开发演示账号（请仅在本地/测试环境使用）')
    print('-' * 60)
    print(f'{"角色":<14} {"用户名":<16} {"密码"}')
    print(f'{"super_admin":<14} {super_name:<16} {super_pass_hint}')
    print(f'{"admin":<14} {admin_name:<16} {admin_pass}')
    print(f'{"user":<14} {user_name:<16} {user_pass}')
    print('-' * 60)
    print('开启登录：.env 中设置 AUTH_REQUIRE_AUTH=true 后重启应用。')


def main() -> int:
    from models.auth_models import User
    from models.models import db
    from services.auth_migrations import get_default_department_id, run_auth_migrations
    from services.auth_service import create_user

    bootstrap_super_name, bootstrap_super_pass = _bootstrap_super_credentials()

    super_name = (
        os.getenv('SEED_DEMO_SUPER_USERNAME', '').strip() or bootstrap_super_name
    )
    super_pass = (
        os.getenv('SEED_DEMO_SUPER_PASSWORD', '').strip()
        or os.getenv('AUTH_BOOTSTRAP_SUPER_PASSWORD', '').strip()
        or 'TestPilot@2026'
    )
    admin_name = os.getenv('SEED_DEMO_ADMIN_USERNAME', 'dept_admin').strip() or 'dept_admin'
    admin_pass = os.getenv('SEED_DEMO_ADMIN_PASSWORD', 'DemoAdmin@2026').strip() or 'DemoAdmin@2026'
    user_name = os.getenv('SEED_DEMO_USER_USERNAME', 'demo_user').strip() or 'demo_user'
    user_pass = os.getenv('SEED_DEMO_USER_PASSWORD', 'DemoUser@2026').strip() or 'DemoUser@2026'

    app = _minimal_app()
    created: list[str] = []
    with app.app_context():
        db.create_all()
        run_auth_migrations()
        dept_id = get_default_department_id()

        super_user = User.query.filter_by(role='super_admin').first()
        if super_user:
            super_name = super_user.username
            super_pass_hint = (
                bootstrap_super_pass
                if super_name == bootstrap_super_name
                else '（已存在，密码未在此脚本中重置）'
            )
        else:
            if not User.query.filter_by(username=super_name).first():
                create_user(
                    username=super_name,
                    password=super_pass,
                    role='super_admin',
                    dept_id=dept_id,
                )
                created.append(f'super_admin:{super_name}')
            else:
                print(
                    f'错误：用户名 {super_name} 已存在但不是 super_admin，请改 SEED_DEMO_SUPER_USERNAME。',
                    file=sys.stderr,
                )
                return 1
            super_pass_hint = super_pass

        if not User.query.filter_by(username=admin_name).first():
            create_user(
                username=admin_name,
                password=admin_pass,
                role='admin',
                dept_id=dept_id,
            )
            created.append(f'admin:{admin_name}')
        else:
            print(f'跳过（已存在）: {admin_name}')

        if not User.query.filter_by(username=user_name).first():
            create_user(
                username=user_name,
                password=user_pass,
                role='user',
                dept_id=dept_id,
            )
            created.append(f'user:{user_name}')
        else:
            print(f'跳过（已存在）: {user_name}')

    if created:
        print('本次新建:', ', '.join(created))
    else:
        print('三个角色账号均已存在，未新建。')

    _print_account_table(
        super_name=super_name,
        super_pass_hint=super_pass_hint,
        admin_name=admin_name,
        admin_pass=admin_pass,
        user_name=user_name,
        user_pass=user_pass,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
