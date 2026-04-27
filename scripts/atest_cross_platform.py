#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TestPilot 跨平台功能测试脚本
验证项目在不同平台上的兼容性
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径，并切换工作目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))  # 切换到项目根目录

from utils.utils_core.platform_utils import (
    get_platform, is_windows, is_linux, is_mac,
    get_wsgi_server, get_platform_info
)


class CrossPlatformTester:
    """跨平台功能测试器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.project_root = Path(__file__).parent.parent
    
    @staticmethod
    def print_header(text):
        """打印测试标题"""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)
    
    def print_test(self, test_name, result, message=""):
        """打印测试结果"""
        if result:
            print(f"✅ {test_name}")
            self.passed += 1
        else:
            print(f"❌ {test_name}")
            if message:
                print(f"   原因: {message}")
            self.failed += 1
    
    def print_warning(self, message):
        """打印警告"""
        print(f"⚠️  {message}")
        self.warnings += 1
    
    def test_platform_detection(self):
        """测试平台检测"""
        self.print_header("测试1: 平台检测")
        
        platform = get_platform()
        print(f"检测到的平台: {platform}")
        
        self.print_test(
            "平台检测功能",
            platform in ["Windows", "Linux", "Darwin"],
            f"未知平台: {platform}"
        )
        
        # 测试平台判断函数
        windows = is_windows()
        linux = is_linux()
        mac = is_mac()
        
        self.print_test(
            "平台判断函数",
            (windows + linux + mac) == 1,
            "应该只有一个平台返回True"
        )
        
        # 显示平台详细信息
        print("\n平台详细信息:")
        info = get_platform_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    def test_path_handling(self):
        """测试路径处理"""
        self.print_header("测试2: 路径处理")
        
        # 测试pathlib路径创建
        try:
            test_path = Path("uploads") / "documents" / "test.txt"
            self.print_test("pathlib路径创建", True)
        except Exception as e:
            self.print_test("pathlib路径创建", False, str(e))
            return
        
        # 测试路径转换
        try:
            posix_path = test_path.as_posix()
            expected = "uploads/documents/test.txt"
            self.print_test(
                "路径转POSIX格式",
                posix_path == expected,
                f"期望 {expected}, 实际 {posix_path}"
            )
        except Exception as e:
            self.print_test("路径转POSIX格式", False, str(e))
        
        # 测试路径存在性检查
        try:
            uploads_path = self.project_root / "uploads"
            # 确保目录存在用于测试
            uploads_path.mkdir(exist_ok=True)
            self.print_test("路径存在性检查", uploads_path.exists())
        except Exception as e:
            self.print_test("路径存在性检查", False, str(e))
    
    def test_wsgi_server_selection(self):
        """测试WSGI服务器选择"""
        self.print_header("测试3: WSGI服务器选择")
        
        wsgi_server = get_wsgi_server()
        print(f"推荐的WSGI服务器: {wsgi_server}")
        
        platform = get_platform()
        expected = "waitress" if platform == "Windows" else "gunicorn"
        
        self.print_test(
            "WSGI服务器选择正确",
            wsgi_server == expected,
            f"期望 {expected}, 实际 {wsgi_server}"
        )
    
    def test_dependencies(self):
        """测试依赖包"""
        self.print_header("测试4: 依赖包检查")
        
        # 测试核心依赖
        core_deps = [
            "flask",
            "sqlalchemy",
            "pathlib",
            "platform"
        ]
        
        for dep in core_deps:
            try:
                __import__(dep)
                self.print_test(f"核心依赖 {dep}", True)
            except ImportError:
                self.print_test(f"核心依赖 {dep}", False, "未安装")
        
        # 测试平台特定依赖
        platform = get_platform()
        if platform == "Windows":
            try:
                __import__("waitress")
                self.print_test("Windows WSGI服务器 (waitress)", True)
            except ImportError:
                self.print_warning("Waitress未安装，生产环境将使用Flask内置服务器")
        else:
            try:
                __import__("gunicorn")
                self.print_test("Unix WSGI服务器 (gunicorn)", True)
            except ImportError:
                self.print_warning("Gunicorn未安装，生产环境将使用Flask内置服务器")
    
    def test_file_operations(self):
        """测试文件操作"""
        self.print_header("测试5: 文件操作")
        
        # 创建测试目录
        test_dir = self.project_root / "test_cross_platform_temp"
        try:
            test_dir.mkdir(exist_ok=True)
            self.print_test("创建目录", True)
        except Exception as e:
            self.print_test("创建目录", False, str(e))
            return
        
        # 创建测试文件
        test_file = test_dir / "test.txt"
        try:
            test_file.write_text("测试内容", encoding="utf-8")
            self.print_test("写入文件", True)
        except Exception as e:
            self.print_test("写入文件", False, str(e))
        
        # 读取测试文件
        try:
            content = test_file.read_text(encoding="utf-8")
            self.print_test("读取文件", content == "测试内容")
        except Exception as e:
            self.print_test("读取文件", False, str(e))
        
        # 删除测试文件
        try:
            test_file.unlink()
            test_dir.rmdir()
            self.print_test("删除文件和目录", True)
        except Exception as e:
            self.print_test("删除文件和目录", False, str(e))
    
    def test_requirements_files(self):
        """测试requirements文件存在性"""
        self.print_header("测试6: Requirements文件")
        
        platform = get_platform().lower()
        if platform == "darwin":
            platform = "macos"
        
        # 检查基础文件
        base_req = self.project_root / "requirements-base.txt"
        self.print_test(
            "requirements-base.txt 存在",
            base_req.exists(),
            f"文件路径: {base_req}"
        )
        
        # 检查平台特定文件
        platform_req = self.project_root / f"requirements-{platform}.txt"
        self.print_test(
            f"requirements-{platform}.txt 存在",
            platform_req.exists(),
            f"文件路径: {platform_req}"
        )
        
        # 检查原有文件（向后兼容）
        old_req = self.project_root / "requirements.txt"
        if old_req.exists():
            self.print_test("requirements.txt 存在（向后兼容）", True)
    
    def test_startup_scripts(self):
        """测试启动脚本"""
        self.print_header("测试7: 启动脚本")
        
        platform = get_platform()
        
        if platform == "Windows":
            script = self.project_root / "start.bat"
            self.print_test("start.bat 存在", script.exists(), f"文件路径: {script}")
        else:
            script = self.project_root / "start.sh"
            exists = script.exists()
            self.print_test("start.sh 存在", exists, f"文件路径: {script}")
            
            if exists:
                # 检查是否可执行
                is_executable = os.access(script, os.X_OK)
                if not is_executable:
                    self.print_warning("start.sh 不可执行，请运行: chmod +x start.sh")
        
        # 检查安装脚本
        install_script = self.project_root / "install.py"
        self.print_test("install.py 存在", install_script.exists(), f"文件路径: {install_script}")
    
    def test_project_structure(self):
        """测试项目结构"""
        self.print_header("测试8: 项目结构")
        
        required_dirs = [
            "utils",
            "utils/utils_core",
            "blueprints",
            "models",
            "services",
            "static",
            "templates",
            "config",
            "scripts"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            self.print_test(
                f"目录 {dir_name} 存在",
                dir_path.exists() and dir_path.is_dir(),
                f"路径: {dir_path}"
            )
        
        # 检查关键文件
        required_files = [
            "app.py",
            "run.py",
            "config/settings.py",
            "utils/utils_core/platform_utils.py"
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            self.print_test(
                f"文件 {file_name} 存在",
                file_path.exists() and file_path.is_file(),
                f"路径: {file_path}"
            )
    
    def print_summary(self):
        """打印测试摘要"""
        self.print_header("测试摘要")
        
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"⚠️  警告: {self.warnings}")
        print(f"📊 通过率: {pass_rate:.1f}%")
        
        print(f"\n当前工作目录: {os.getcwd()}")
        print(f"项目根目录: {self.project_root}")
        
        if self.failed == 0:
            print("\n🎉 所有测试通过！项目已准备好在此平台运行。")
            return True
        else:
            print("\n⚠️  存在失败的测试项，请检查上述错误信息。")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*70)
        print("  TestPilot 跨平台功能测试")
        print("="*70)
        print(f"工作目录: {os.getcwd()}")
        print(f"项目根目录: {self.project_root}")
        
        self.test_platform_detection()
        self.test_path_handling()
        self.test_wsgi_server_selection()
        self.test_dependencies()
        self.test_file_operations()
        self.test_requirements_files()
        self.test_startup_scripts()
        self.test_project_structure()
        
        success = self.print_summary()
        return success


def main():
    """主函数"""
    try:
        tester = CrossPlatformTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
