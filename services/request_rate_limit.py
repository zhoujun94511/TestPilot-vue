#!/usr/bin/python
# -*- coding: utf-8 -*-
"""进程内滑动窗口限流（登录等敏感接口）。"""

from __future__ import annotations

import time
from typing import MutableMapping

_buckets: MutableMapping[str, list[float]] = {}


def reset_rate_limits() -> None:
    """清空进程内计数。测试用来隔离用例，避免窗口残留。"""
    _buckets.clear()


def sliding_window_allow(
    key: str,
    *,
    max_calls: int,
    window_seconds: float,
) -> bool:
    now = time.time()
    bucket = _buckets.get(key, [])
    bucket = [ts for ts in bucket if now - ts <= window_seconds]
    if len(bucket) >= max_calls:
        _buckets[key] = bucket
        return False
    bucket.append(now)
    _buckets[key] = bucket
    return True
