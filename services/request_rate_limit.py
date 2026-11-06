#!/usr/bin/python
# -*- coding: utf-8 -*-
"""进程内滑动窗口限流（登录等敏感接口）。"""

from __future__ import annotations

import threading
import time
from typing import MutableMapping

_buckets: MutableMapping[str, list[float]] = {}
_lock = threading.Lock()
_PRUNE_THRESHOLD = 2048
# 大于所有调用方的窗口，超过这个时长没有请求的键一定已经出窗
_IDLE_SECONDS = 3600


def reset_rate_limits() -> None:
    """清空进程内计数。测试用来隔离用例，避免窗口残留。"""
    with _lock:
        _buckets.clear()


def _prune_idle(now: float) -> None:
    for key in [k for k, ts in _buckets.items() if not ts or now - ts[-1] > _IDLE_SECONDS]:
        del _buckets[key]


def sliding_window_allow(
    key: str,
    *,
    max_calls: int,
    window_seconds: float,
) -> bool:
    now = time.time()
    with _lock:
        if len(_buckets) > _PRUNE_THRESHOLD:
            _prune_idle(now)
        bucket = [ts for ts in _buckets.get(key, []) if now - ts <= window_seconds]
        if len(bucket) >= max_calls:
            _buckets[key] = bucket
            return False
        bucket.append(now)
        _buckets[key] = bucket
        return True
