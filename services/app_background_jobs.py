#!/usr/bin/python
# -*- coding: utf-8 -*-
"""应用后台定时任务（daemon 线程，单进程内有效）。"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

_started = False
_start_lock = threading.Lock()


def _vector_metadata_retry_loop(app: Any, interval_seconds: float) -> None:
    while True:
        time.sleep(interval_seconds)
        try:
            with app.app_context():
                vector_db = getattr(app, 'vector_db', None)
                if vector_db is None:
                    continue
                from services.knowledge_vector_scope import retry_pending_vector_metadata

                remaining = retry_pending_vector_metadata(vector_db)
                if remaining:
                    logger.info('向量 metadata 定时重试后仍待处理: %s 条', remaining)
        except Exception as exc:
            logger.warning('向量 metadata 定时重试异常: %s', exc)


def start_background_jobs(app: Any) -> None:
    """启动后台任务（幂等，仅首次生效）。"""
    global _started
    with _start_lock:
        if _started:
            return
        _started = True

    interval = int(getattr(settings, 'VECTOR_METADATA_RETRY_INTERVAL_SECONDS', 0) or 0)
    if interval <= 0:
        logger.debug('VECTOR_METADATA_RETRY_INTERVAL_SECONDS<=0，跳过向量 metadata 定时重试')
        return
    if not getattr(settings, 'ENABLE_VECTOR_STORE', True):
        return

    thread = threading.Thread(
        target=_vector_metadata_retry_loop,
        args=(app, float(interval)),
        name='vector-metadata-retry',
        daemon=True,
    )
    thread.start()
    logger.info('已启动向量 metadata 定时重试，间隔 %s 秒', interval)
