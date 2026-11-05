#!/usr/bin/python
# -*- coding: utf-8 -*-
"""首次初始化。

只在 app_bootstrap_markers.first_run 不存在时写入三类账号和配置中心缺省项。
已有同名账号不改密码，已有配置项不覆盖。不调用向量库清空或配置中心 --force。
"""

from __future__ import annotations

import importlib.util
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from models.auth_models import BootstrapMarker
from models.models import db
from services.auth_migrations import ensure_bootstrap_accounts

logger = logging.getLogger(__name__)

FIRST_RUN_MARKER = 'first_run'


def first_run_completed() -> bool:
    return BootstrapMarker.query.filter_by(marker_key=FIRST_RUN_MARKER).first() is not None


def _load_config_seed():
    seed_path = Path(__file__).resolve().parents[1] / 'scripts' / 'init_config_center.py'
    spec = importlib.util.spec_from_file_location('testpilot_config_center_seed', seed_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'无法加载配置中心种子脚本: {seed_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_first_run_bootstrap() -> str:
    """返回 completed 或 skipped。调用方必须已处于 Flask app context，且已 create_all。"""
    if first_run_completed():
        logger.info('首次初始化游标已存在，跳过账号与配置中心种子')
        return 'skipped'

    ensure_bootstrap_accounts()
    seed = _load_config_seed()
    configs_ok = bool(seed.seed_default_configs())
    rules_ok = bool(seed.seed_validation_rules())
    if not configs_ok or not rules_ok:
        logger.warning('配置中心缺省项未写完，本次不记游标，下次启动会再试（不会覆盖已有值）')
        return 'incomplete'

    db.session.add(
        BootstrapMarker(
            marker_key=FIRST_RUN_MARKER,
            completed_at=datetime.now(timezone.utc),
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logger.info('首次初始化游标已由其他进程写入，本次不改已有数据')
        return 'skipped'
    logger.info('首次初始化完成，已写入游标 %s', FIRST_RUN_MARKER)
    return 'completed'
