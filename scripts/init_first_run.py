#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手动首次初始化。

串联业务库建表、三类初始账号、配置中心缺省项，并随应用启动创建向量库文件。
游标 app_bootstrap_markers.first_run 已存在时直接退出，不覆盖账号、配置或向量数据。

不会执行：
  python scripts/init_db.py clear
  python scripts/init_db.py reset
  python scripts/init_vectordb.py --init-vector-db
  python scripts/init_config_center.py --force

用法：
  python scripts/init_first_run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def main() -> int:
    from app import create_app

    app = create_app()
    status = app.config.get('FIRST_RUN_STATUS', 'unknown')
    if status == 'skipped':
        print('已完成过首次初始化，本次未修改账号、配置中心或已有向量数据。')
        return 0
    if status == 'completed':
        print('首次初始化完成。请阅读 README 的「首次登录」，自行选择账号登录。界面不会提示默认账号。')
        return 0
    print(f'首次初始化未完成（{status}）。已有数据不会被清空，可修正错误后重新运行本脚本。')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
