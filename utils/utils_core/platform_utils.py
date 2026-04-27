#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台工具模块
提供平台检测和适配功能，确保代码在Windows、Linux、Mac上都能正常运行
"""

import os
import platform
from typing import Literal

# 平台类型
PlatformType = Literal["Windows", "Linux", "Darwin", "Unknown"]


def get_platform() -> PlatformType:
    system = platform.system()
    if system in ["Windows", "Linux", "Darwin"]:
        return system  # type: ignore
    return "Unknown"


def is_windows() -> bool:
    """判断是否为Windows平台"""
    return get_platform() == "Windows"


def is_linux() -> bool:
    """判断是否为Linux平台"""
    return get_platform() == "Linux"


def is_mac() -> bool:
    """判断是否为Mac平台"""
    return get_platform() == "Darwin"


def is_unix_like() -> bool:
    """判断是否为Unix-like系统（Linux或Mac）"""
    return is_linux() or is_mac()


def get_platform_info() -> dict:
    """
    获取详细的平台信息
    
    Returns:
        dict: 包含平台详细信息的字典
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }


def get_wsgi_server() -> str:
    """
    根据平台返回推荐的WSGI服务器
    
    Returns:
        str: WSGI服务器名称 - 'gunicorn' (Linux/Mac) 或 'waitress' (Windows)
    """
    if is_windows():
        return "waitress"
    else:
        return "gunicorn"


def set_file_executable(file_path: str) -> bool:
    """
    设置文件为可执行（仅在Unix-like系统上）
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否设置成功
    """
    if is_unix_like():
        try:
            import stat
            current_permissions = os.stat(file_path).st_mode
            os.chmod(file_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return True
        except (OSError, PermissionError, FileNotFoundError):
            return False
    # Windows系统不需要显式设置可执行权限
    return True


def get_platform_specific_path_separator() -> str:
    """
    获取平台特定的路径分隔符
    
    Returns:
        str: 路径分隔符 - Windows为'\\'，Unix-like为'/'
    """
    return os.sep


def normalize_path(path: str) -> str:
    """
    标准化路径为当前平台格式
    
    Args:
        path: 输入路径
        
    Returns:
        str: 标准化后的路径
    """
    return os.path.normpath(path)


def get_line_ending() -> str:
    """
    获取平台特定的行结束符
    
    Returns:
        str: 行结束符 - Windows为'\\r\\n'，Unix-like为'\\n'
    """
    if is_windows():
        return "\r\n"
    else:
        return "\n"


def get_null_device() -> str:
    """
    获取平台特定的空设备
    
    Returns:
        str: 空设备路径 - Windows为'nul'，Unix-like为'/dev/null'
    """
    return os.devnull


def supports_ansi_colors() -> bool:
    """
    检查终端是否支持ANSI颜色代码
    
    Returns:
        bool: 是否支持ANSI颜色
    """
    # Windows 10及以上版本支持ANSI颜色
    if is_windows():
        # 检查Windows版本
        try:
            version = platform.version()
            # Windows 10的版本号是10.0.*
            major_version = int(version.split('.')[0])
            return major_version >= 10
        except (ValueError, IndexError, AttributeError):
            return False
    else:
        # Unix-like系统通常都支持
        return True


def get_home_directory() -> str:
    """
    获取用户主目录
    
    Returns:
        str: 用户主目录路径
    """
    return os.path.expanduser("~")


def get_temp_directory() -> str:
    """
    获取临时目录
    
    Returns:
        str: 临时目录路径
    """
    import tempfile
    return tempfile.gettempdir()


def is_admin() -> bool:
    """
    检查当前用户是否具有管理员权限
    
    Returns:
        bool: 是否为管理员
    """
    try:
        if is_windows():
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except (OSError, AttributeError, PermissionError):
        return False


if __name__ == "__main__":
    """测试平台工具函数"""
    print("=" * 60)
    print("平台信息:")
    print("=" * 60)
    info = get_platform_info()
    for key, value in info.items():
        print(f"{key:25s}: {value}")
    print()
    
    print("=" * 60)
    print("平台检测:")
    print("=" * 60)
    print(f"当前平台: {get_platform()}")
    print(f"是否为Windows: {is_windows()}")
    print(f"是否为Linux: {is_linux()}")
    print(f"是否为Mac: {is_mac()}")
    print(f"是否为Unix-like: {is_unix_like()}")
    print()
    
    print("=" * 60)
    print("平台配置:")
    print("=" * 60)
    print(f"推荐的WSGI服务器: {get_wsgi_server()}")
    print(f"路径分隔符: {repr(get_platform_specific_path_separator())}")
    print(f"行结束符: {repr(get_line_ending())}")
    print(f"空设备: {get_null_device()}")
    print(f"支持ANSI颜色: {supports_ansi_colors()}")
    print(f"用户主目录: {get_home_directory()}")
    print(f"临时目录: {get_temp_directory()}")
    print(f"是否为管理员: {is_admin()}")
    print()




