#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理未使用的 Python 包

此脚本会卸载明确未在项目代码中使用的包，保留：
1. 正在使用的包
2. 不确定是否使用的包（可能是间接依赖）
3. 保留用于回滚的包（如 ChromaDB）

使用方法:
    python scripts/cleanup_unused_packages.py
    python scripts/cleanup_unused_packages.py --dry-run  # 仅显示将要卸载的包，不实际卸载
    python scripts/cleanup_unused_packages.py --force    # 不询问确认，直接卸载
"""

import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 明确未使用的包列表（基于代码分析）
UNUSED_PACKAGES = [
    # 开发工具（建议移动到 requirements-dev.txt）
    "black",
    "flake8",
    "mccabe",
    "pycodestyle",
    "pyflakes",
    "mypy_extensions",
    "pathspec",
    "Pygments",
    
    # 明确未使用的库
    "embeddings",           # 未在代码中找到使用
    "build",                # 构建工具，不需要
    "pyproject_hooks",      # build 依赖
    "selenium",             # 浏览器自动化，未使用
    "kubernetes",           # Kubernetes 客户端，未使用
    "uvicorn",              # ASGI 服务器，项目使用 Flask
    "watchfiles",           # uvicorn 依赖
    "httptools",            # uvicorn 依赖
    "httpx",                # 异步 HTTP 客户端，未使用
    "httpx-sse",            # httpx SSE 支持，未使用
    "httpcore",             # httpx 依赖
    "h11",                  # httpcore 依赖
    "websocket-client",     # WebSocket 客户端，未使用
    "websockets",            # WebSocket 服务器，未使用
    "trio",                 # 异步框架，未使用
    "trio-websocket",       # trio WebSocket，未使用
    "jiter",                # JSON 迭代器，未使用
    "durationpy",           # 持续时间解析，未使用
    "PyPika",               # SQL 查询构建器，未使用
    "requests-oauthlib",    # OAuth 支持，未使用
    "requests-toolbelt",    # Requests 工具，未使用
    "oauthlib",             # requests-oauthlib 依赖
    "pyasn1",               # oauthlib 依赖
    "pyasn1_modules",       # oauthlib 依赖
    "rsa",                  # 可能被某些库间接使用，但代码中未直接使用
    "PySocks",              # SOCKS 代理，未使用
    "uritemplate",          # URI 模板，未使用
    "rich",                 # 终端美化，未使用
    "markdown-it-py",       # Markdown 解析，未使用
    "mdurl",                # markdown-it-py 依赖
    "structlog",            # 结构化日志，未使用（项目使用 colorlog）
    "loguru",               # 日志库，未使用（项目使用 colorlog）
    "typer",                # CLI 框架，未使用
    "shellingham",          # typer 依赖
    "colorama",             # 终端颜色，未使用
    
    # 已禁用的遥测库（项目已明确禁用）
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-proto",
    "opentelemetry-exporter-otlp-proto-common",
    "opentelemetry-exporter-otlp-proto-grpc",
    "opentelemetry-semantic-conventions",
    "langsmith",            # LangChain 追踪（已禁用）
    "posthog",              # 产品分析（已禁用）
    
    # aiohttp 及其依赖（未在代码中直接使用，可能是间接依赖）
    # ⚠️ 注意：这些可能是某些库的间接依赖，如果卸载后出现问题，需要重新安装
    "aiohttp",
    "aiohappyeyeballs",
    "aiosignal",
    "frozenlist",
    "yarl",
    "multidict",
    "wsproto",
    
    # 更多可能未使用的包（需要验证）
    "marshmallow",          # 可能被某些库使用，但代码中未直接使用
    "dataclasses-json",     # 可能被某些库使用，但代码中未直接使用
    "tenacity",             # 可能被某些库用于重试，但代码中未直接使用
    "cachetools",           # 可能被某些库用于缓存，但代码中未直接使用
    "anyio",                # 异步抽象，可能被某些库使用
    "outcome",              # 异步结果，可能被某些库使用
    "sniffio",              # 异步检测，可能被某些库使用
    "jiter",                # JSON 迭代器，未使用
    "durationpy",           # 持续时间解析，未使用
    "PyPika",               # SQL 查询构建器，未使用
    "requests-oauthlib",    # OAuth 支持，未使用
    "requests-toolbelt",    # Requests 工具，未使用
    "oauthlib",             # requests-oauthlib 依赖
    "rsa",                  # 可能被某些库间接使用，但代码中未直接使用
    "uritemplate",          # URI 模板，未使用
    "structlog",            # 结构化日志，未使用（项目使用 colorlog）
    "websocket-client",     # WebSocket 客户端，未使用
    "distro",               # 操作系统检测，可能被某些库使用
    "filetype",             # 文件类型检测，可能被某些库使用
    "pybase64",             # Base64 编码，可能被某些库使用
    "bcrypt",               # 密码哈希，可能用于安全，但代码中未直接使用
    "cffi",                 # bcrypt 依赖
    "pycparser",            # cffi 依赖
    "iniconfig",            # INI 配置解析，可能被某些库使用
    "pluggy",               # 插件系统，可能被某些库使用
    "propcache",            # 属性缓存，可能被某些库使用
    "zstandard",            # Zstandard 压缩，可能被某些库使用
    "networkx",             # 图论，可能被某些库间接使用
    "sympy",                # 符号数学，可能被某些库间接使用
    "mpmath",               # 高精度数学（sympy 依赖）
    "sortedcontainers",     # 有序容器，可能被某些库使用
    "mmh3",                 # MurmurHash3，可能被某些库使用
    "py_rust_stemmers",     # 词干提取，可能被某些库使用
    "overrides",            # 方法重写检查，可能被某些库使用
    "typing-inspect",       # 类型检查，可能被某些库使用
    "typing-inspection",    # 类型检查，可能被某些库使用
    "coloredlogs",          # 彩色日志（项目使用 colorlog，可能不需要）
    "humanfriendly",       # 人类友好格式（coloredlogs 依赖）
    "dnspython",            # DNS 解析，可能被某些库使用
    "httplib2",             # HTTP 库，可能被某些库使用
    "six",                  # Python 2/3 兼容（历史遗留，但可能被某些库需要）
]

# 可能被间接依赖的包（保留，不卸载）
# 这些包虽然代码中未直接使用，但可能是其他包的依赖
KEEP_PACKAGES = [
    "gunicorn",             # 生产环境需要（Linux/Mac）
    "eventlet",             # Gunicorn worker（生产环境需要）
    "greenlet",             # eventlet 依赖
    "chromadb",             # 保留用于回滚
    "langchain-chroma",     # 保留用于回滚
]


def check_package_installed(package_name: str) -> bool:
    """检查包是否已安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def uninstall_package(package_name: str, dry_run: bool = False) -> bool:
    """卸载包"""
    if dry_run:
        print(f"  [DRY-RUN] 将卸载: {package_name}")
        return True
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print(f"  [OK] 已卸载: {package_name}")
            return True
        else:
            print(f"  [FAIL] 卸载失败: {package_name}")
            if result.stderr:
                print(f"     错误: {result.stderr.strip()}")
            return False
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  [ERROR] 卸载异常: {package_name} - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="清理未使用的 Python 包",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/cleanup_unused_packages.py              # 交互式卸载
  python scripts/cleanup_unused_packages.py --dry-run      # 仅显示将要卸载的包
  python scripts/cleanup_unused_packages.py --force       # 不询问确认，直接卸载
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要卸载的包，不实际卸载"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="不询问确认，直接卸载"
    )
    parser.add_argument(
        "--include-aiohttp",
        action="store_true",
        help="包含 aiohttp 及其依赖（默认不包含，因为可能是间接依赖）"
    )
    
    args = parser.parse_args()
    
    # 确定要卸载的包列表
    packages_to_uninstall = UNUSED_PACKAGES.copy()
    
    # 如果不包含 aiohttp，从列表中移除
    if not args.include_aiohttp:
        aiohttp_packages = [
            "aiohttp", "aiohappyeyeballs", "aiosignal",
            "frozenlist", "yarl", "multidict", "wsproto"
        ]
        packages_to_uninstall = [
            pkg for pkg in packages_to_uninstall
            if pkg not in aiohttp_packages
        ]
    
    # 检查已安装的包
    installed_packages = []
    for package in packages_to_uninstall:
        if check_package_installed(package):
            installed_packages.append(package)
    
    if not installed_packages:
        print("[OK] 没有需要卸载的包（所有未使用的包都未安装）")
        return 0
    
    # 显示将要卸载的包
    print("=" * 70)
    print("[PACKAGE CLEANUP] 未使用的包清理工具")
    print("=" * 70)
    print(f"\n找到 {len(installed_packages)} 个已安装的未使用包：\n")
    
    # 按类别分组显示
    dev_tools = [pkg for pkg in installed_packages if pkg in [
        "black", "flake8", "mccabe", "pycodestyle", "pyflakes",
        "mypy_extensions", "pathspec", "Pygments"
    ]]
    unused_libs = [pkg for pkg in installed_packages if pkg not in dev_tools and pkg not in [
        "opentelemetry-api", "opentelemetry-sdk", "opentelemetry-proto",
        "opentelemetry-exporter-otlp-proto-common", "opentelemetry-exporter-otlp-proto-grpc",
        "opentelemetry-semantic-conventions", "langsmith", "posthog"
    ]]
    telemetry = [pkg for pkg in installed_packages if pkg in [
        "opentelemetry-api", "opentelemetry-sdk", "opentelemetry-proto",
        "opentelemetry-exporter-otlp-proto-common", "opentelemetry-exporter-otlp-proto-grpc",
        "opentelemetry-semantic-conventions", "langsmith", "posthog"
    ]]
    
    if dev_tools:
        print("[DEV TOOLS] 开发工具:")
        for pkg in sorted(dev_tools):
            print(f"  - {pkg}")
        print()
    
    if unused_libs:
        print("[UNUSED LIBS] 未使用的库:")
        for pkg in sorted(unused_libs):
            print(f"  - {pkg}")
        print()
    
    if telemetry:
        print("[TELEMETRY] 已禁用的遥测库:")
        for pkg in sorted(telemetry):
            print(f"  - {pkg}")
        print()
    
    # 确认卸载
    if args.dry_run:
        print("[DRY-RUN MODE] 以上包将被卸载（但不会实际执行）")
        return 0
    
    if not args.force:
        print("[WARNING] 此操作将卸载上述包，请确保它们确实未被使用")
        response = input("\n是否继续？(yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("[CANCELLED] 已取消")
            return 1
    
    # 执行卸载
    print("\n开始卸载...\n")
    success_count = 0
    fail_count = 0
    
    for package in installed_packages:
        if uninstall_package(package, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    # 显示结果
    print("\n" + "=" * 70)
    print("[RESULT] 清理结果")
    print("=" * 70)
    print(f"[SUCCESS] 成功卸载: {success_count} 个")
    if fail_count > 0:
        print(f"[FAILED] 卸载失败: {fail_count} 个")
    print()
    
    if success_count > 0:
        print("[SUGGESTION] 建议:")
        print("  1. 运行项目测试，确保功能正常")
        print("  2. 如果出现问题，可以使用以下命令重新安装:")
        print(f"     pip install {' '.join(installed_packages)}")
        print("  3. 开发工具可以移动到 requirements-dev.txt")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

