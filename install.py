#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TestPilot 跨平台安装脚本
自动检测平台并安装对应依赖
"""

import sys
import subprocess
import platform
from pathlib import Path


def get_platform():
    """获取当前平台"""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Linux":
        return "linux"
    elif system == "Darwin":
        return "macos"
    else:
        return "unknown"


def print_banner():
    """打印欢迎信息"""
    banner = """
    ╔══════════════════════════════════════════════╗
    ║                                              ║
    ║          TestPilot 安装向导                   ║
    ║                                              ║
    ║     自动化测试用例生成与管理平台                  ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)


def check_python_version():
    """检查Python版本"""
    print("正在检查Python版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("   需要Python 3.10或更高版本")
        print("   请访问 https://www.python.org/downloads/ 下载安装")
        return False
    
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True


def check_pip():
    """检查pip是否可用"""
    print("\n正在检查pip...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip不可用")
        return False


def upgrade_pip():
    """升级pip"""
    print("\n正在升级pip...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("✅ pip升级完成")
        return True
    except subprocess.CalledProcessError as errea:
        print(f"❌ pip升级失败: {errea}")
        return False


def create_venv():
    """创建虚拟环境"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("\n虚拟环境已存在，跳过创建")
        return True
    
    print("\n正在创建虚拟环境...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", "venv"],
            check=True
        )
        print("✅ 虚拟环境创建完成")
        return True
    except subprocess.CalledProcessError as erreb:
        print(f"❌ 虚拟环境创建失败: {erreb}")
        return False


def get_venv_python():
    """获取虚拟环境中的Python路径"""
    platform_name = get_platform()
    if platform_name == "windows":
        return Path("venv") / "Scripts" / "python.exe"
    else:
        return Path("venv") / "bin" / "python"


def install_dependencies(platform_name):
    """安装依赖"""
    requirements_file = f"requirements-{platform_name}.txt"
    
    if not Path(requirements_file).exists():
        print(f"❌ 未找到依赖文件: {requirements_file}")
        return False
    
    print(f"\n正在安装{platform_name}平台依赖...")
    print(f"使用依赖文件: {requirements_file}")
    print("这可能需要几分钟时间，请耐心等待...\n")
    
    venv_python = get_venv_python()
    
    try:
        # 首先升级虚拟环境中的pip
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        
        # 安装依赖（排除 PyTorch，使用 FastEmbed/ONNX）
        # 注意：项目已去 PyTorch，使用 FastEmbed (ONNX/CPU)
        # 如果某个依赖包尝试安装 PyTorch，pip 会安装，但不影响项目运行
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", requirements_file],
            check=True
        )
        
        # 验证 PyTorch 是否被安装（不应该被安装）
        try:
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "show", "torch"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("\n⚠️  警告: 检测到 PyTorch 被安装（可能是某个依赖的间接依赖）")
                print("   项目使用 FastEmbed (ONNX)，不需要 PyTorch")
                print("   如果不需要 PyTorch，可以运行: pip uninstall torch")
        except (subprocess.SubprocessError, OSError, FileNotFoundError):
            pass  # 忽略检查错误
        print("\n✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as errec:
        print(f"\n❌ 依赖安装失败: {errec}")
        print("\n提示: 可以尝试使用国内镜像源:")
        print(f"   {venv_python} -m pip install -r {requirements_file} -i https://pypi.tuna.tsinghua.edu.cn/simple")
        return False


def init_database():
    """初始化数据库"""
    db_path = Path("testpilot.db")
    
    if db_path.exists():
        print("\n数据库已存在，跳过初始化")
        return True
    
    print("\n正在初始化数据库...")
    venv_python = get_venv_python()
    
    try:
        subprocess.run(
            [str(venv_python), "scripts/init_db.py"],
            check=True
        )
        print("✅ 数据库初始化完成")
        return True
    except subprocess.CalledProcessError as erred:
        print(f"⚠️  数据库初始化失败: {erred}")
        print("   数据库将在首次启动时自动创建")
        return True  # 不阻止安装继续


def create_env_file():
    """创建.env文件"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if env_path.exists():
        print("\n.env文件已存在，跳过创建")
        return True
    
    if not env_example_path.exists():
        print("\n⚠️  未找到.env.example文件")
        return True
    
    print("\n正在创建.env配置文件...")
    try:
        import shutil
        shutil.copy(env_example_path, env_path)
        print("✅ .env文件创建完成")
        print("\n⚠️  重要提示:")
        print("   请编辑 .env 文件，配置您的API密钥")
        print("   至少需要配置以下其中一项:")
        print("   - OPENAI_API_KEY")
        print("   - DEEPSEEK_API_KEY")
        print("   - OLLAMA_BASE_URL (本地模型)")
        return True
    except Exception as erree:
        print(f"❌ .env文件创建失败: {erree}")
        return False


def create_directories():
    """创建必要的目录"""
    print("\n正在创建必要的目录...")
    directories = ["logs", "uploads", "uploads/documents", "uploads/knowledge", "sessions", "vector_store"]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ 目录创建完成")
    return True


def print_next_steps(platform_name):
    """打印后续步骤"""
    print("\n" + "="*60)
    print("🎉 安装完成!")
    print("="*60)
    
    print("\n📝 后续步骤:")
    print("\n1. 配置环境变量:")
    if platform_name == "windows":
        print("   编辑 .env 文件，配置API密钥")
    else:
        print("   使用文本编辑器编辑 .env 文件:")
        print("   nano .env  或  vim .env")
    
    print("\n2. 启动应用:")
    if platform_name == "windows":
        print("   双击运行: start.bat")
        print("   或在命令行运行: start.bat")
    else:
        print("   ./start.sh")
    
    print("\n3. 访问应用:")
    print("   浏览器打开: http://localhost:5001")
    
    print("\n4. 查看文档:")
    print("   docs/跨平台部署指南.md")
    
    print("\n" + "="*60)
    print("需要帮助? 查看项目文档或提交Issue")
    print("="*60 + "\n")


def main():
    """主函数"""
    print_banner()
    
    # 检测平台
    platform_name = get_platform()
    print(f"检测到的平台: {platform_name.upper()}")
    
    if platform_name == "unknown":
        print("❌ 不支持的操作系统")
        sys.exit(1)
    
    print("\n开始安装过程...\n")
    print("="*60)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查pip
    if not check_pip():
        sys.exit(1)
    
    # 升级pip
    if not upgrade_pip():
        print("⚠️  pip升级失败，但可以继续安装")
    
    # 创建虚拟环境
    if not create_venv():
        sys.exit(1)
    
    # 安装依赖
    if not install_dependencies(platform_name):
        sys.exit(1)
    
    # 创建目录
    if not create_directories():
        sys.exit(1)
    
    # 创建.env文件
    if not create_env_file():
        print("⚠️  .env文件创建失败，请手动创建")
    
    # 初始化数据库
    init_database()
    
    # 打印后续步骤
    print_next_steps(platform_name)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 安装过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





