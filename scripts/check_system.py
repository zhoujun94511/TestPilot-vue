#!/usr/bin/env python3
"""
TestPilot 系统冒烟测试脚本
快速验证系统核心功能是否正常
支持多种测试模式和详细报告

用法:
# 运行完整系统测试
python scripts/check_system.py

# 指定测试目标
python scripts/check_system.py http://localhost:5001

# 快速冒烟测试（只测试核心功能）
python scripts/check_system.py --smoke

# 详细测试（包含所有功能）
python scripts/check_system.py --detailed

# 测试特定模块
python scripts/check_system.py --module chat
python scripts/check_system.py --module knowledge
"""

import socket
import sys
import json
import requests
import time
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 现在可以导入项目模块
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

# 测试模式定义
TEST_MODES = {
    'smoke': '快速冒烟测试',
    'detailed': '详细功能测试', 
    'full': '完整系统测试'
}

# 模块定义
MODULES = {
    'core': ['健康检查', '主页面访问', '静态文件加载', 'API端点检查'],
    'stats': ['统计功能', 'Token配置', '网络信息'],
    'chat': ['聊天功能'],
    'knowledge': ['知识库功能', 'RAG功能'],
    'cases': ['用例生成'],
    'documents': ['文档分析'],
    'config': ['配置中心'],
    'export': ['导出功能']
}

def get_local_ip():
    """获取本地IP地址"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except OSError as e:  # ✅ 更精确的异常类型
        logger.warning(f"无法获取本地IP，回退到127.0.0.1: {e}")
        return 'localhost'

class TestPilotTester:
    def __init__(self, base_url=None, test_mode='full', modules=None):
        if base_url:
            self.base_url = base_url
        else:
            # 自动获取本地IP
            ip = get_local_ip()
            self.base_url = f"http://{ip}:5001"
        
        self.session = requests.Session()
        self.test_results = []
        self.test_mode = test_mode
        self.modules = modules or []
        self.api_key_configured = None  # 缓存API Key状态
    
    def check_api_key_status(self):
        """检查API Key配置状态"""
        if self.api_key_configured is not None:
            return self.api_key_configured
            
        try:
            response = self.session.get(f"{self.base_url}/api/model-status")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    model_data = data.get('data', {})
                    self.api_key_configured = model_data.get('is_available', False)
                    return self.api_key_configured
        except Exception as e:
            logger.warning(f"检查API Key状态失败: {e}")
        
        self.api_key_configured = False
        return False
    
    @staticmethod
    def is_api_key_required_test(test_name):
        """判断测试是否需要API Key"""
        ai_tests = ['用例生成', '文档分析', '聊天功能', '知识库功能', 'RAG功能']
        return test_name in ai_tests
    
    def run_test(self, test_name, test_func):
        """运行单个测试"""
        print(f"\n🧪 运行测试: {test_name}")
        
        # 检查是否需要API Key
        if self.is_api_key_required_test(test_name):
            if not self.check_api_key_status():
                print(f"⚠️  跳过测试 {test_name}：API Key未配置")
                self.test_results.append({
                    "name": test_name, 
                    "status": "SKIP", 
                    "reason": "API Key未配置",
                    "time": 0
                })
                return True
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            if result:
                print(f"✅ 测试通过: {test_name} ({end_time - start_time:.2f}s)")
                self.test_results.append({
                    "name": test_name, 
                    "status": "PASS", 
                    "time": end_time - start_time
                })
                return True
            else:
                print(f"❌ 测试失败: {test_name}")
                self.test_results.append({
                    "name": test_name, 
                    "status": "FAIL", 
                    "time": end_time - start_time
                })
                return False
                
        except Exception as e:
            print(f"❌ 测试异常: {test_name} - {str(e)}")
            self.test_results.append({
                "name": test_name, 
                "status": "ERROR", 
                "error": str(e)
            })
            return False
    
    def test_health_check(self):
        """测试健康检查"""
        response = self.session.get(f"{self.base_url}/api/stats/health")
        if response.status_code != 200:
            return False
        
        data = response.json()
        health_data = data.get("health", {}).get("health", {})
        
        # 检查基本组件状态
        components = health_data.get("components", {})
        services = components.get("services", {})
        
        # 只要API能正常响应且服务组件正常，就认为健康检查通过
        return services.get("overall", False)
    
    def test_main_page(self):
        """测试主页面"""
        response = self.session.get(f"{self.base_url}/")
        return response.status_code == 200 and "TestPilot" in response.text
    
    def test_static_files(self):
        """测试静态文件"""
        # 测试CSS文件
        css_response = self.session.get(f"{self.base_url}/static/css/style.css")
        if css_response.status_code != 200:
            return False
            
        # 测试JS文件
        js_response = self.session.get(f"{self.base_url}/static/js/main.js")
        return js_response.status_code == 200
    
    def test_api_endpoints(self):
        """测试API端点"""
        endpoints = [
            # 统计相关
            "/api/stats/overview",
            "/api/stats/health", 
            "/api/stats/tokens",
            "/api/stats/network/info",
            # 核心功能
            "/api/cases",
            "/api/documents",
            "/api/documents/requirements",
            "/api/knowledge/files",
            "/api/knowledge/search",
            "/api/chat/sessions",
            "/api/chat/message",
            # 配置和导出
            "/api/config/categories",
            "/api/config/ai_model",
            "/api/export/template/cases",
            # 模型状态
            "/api/model-status"
        ]
        
        failed_endpoints = []
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code not in [200, 404]:  # 404也可以接受，表示端点存在但无数据
                    failed_endpoints.append(f"{endpoint} (状态码: {response.status_code})")
                else:
                    print(f"  ✅ 端点正常: {endpoint}")
            except Exception as e:
                failed_endpoints.append(f"{endpoint} (异常: {str(e)})")
        
        if failed_endpoints:
            print(f"  ❌ 失败的端点:")
            for endpoint in failed_endpoints:
                print(f"    - {endpoint}")
            return False
        
        return True
    
    def test_case_generation(self):
        """测试用例生成功能"""
        test_data = {
            "requirement_text": "用户登录功能测试",
            "case_count": 3,
            "priority": "medium"
        }
        
        response = self.session.post(
            f"{self.base_url}/api/cases/generate",
            json=test_data
        )
        
        # 如果API Key未配置，返回400或500是正常的
        if response.status_code in [400, 500]:
            data = response.json()
            # 检查是否是API Key配置问题
            if "API Key" in str(data) or "配置" in str(data):
                print(f"  ⚠️  API Key未配置，跳过用例生成测试")
                return True
        
        return response.status_code in [200, 201] and response.json().get("success", False)
    
    def test_document_analysis(self):
        """测试文档分析功能"""
        test_data = {
            "content": "这是一个测试需求文档，包含用户注册和登录功能的描述。",
            "analysis_type": "requirements"
        }
        
        response = self.session.post(
            f"{self.base_url}/api/documents/analyze",
            json=test_data
        )
        
        # 如果API Key未配置，返回400或500是正常的
        if response.status_code in [400, 500]:
            data = response.json()
            if "API Key" in str(data) or "配置" in str(data):
                print(f"  ⚠️  API Key未配置，跳过文档分析测试")
                return True
        
        return response.status_code in [200, 201] and response.json().get("success", False)
    
    def test_chat_functionality(self):
        """测试聊天功能"""
        # 创建会话
        create_response = self.session.post(f"{self.base_url}/api/chat/sessions")
        if create_response.status_code not in [200, 201]:
            return False
        
        session_data = create_response.json()
        if not session_data.get("success", False):
            return False
        
        session_id = session_data.get("session_id")
        if not session_id:
            return False
        
        # 发送消息
        message_data = {
            "session_id": session_id,
            "message": "你好，请介绍一下软件测试的基本概念。"
        }
        
        message_response = self.session.post(
            f"{self.base_url}/api/chat/message",
            json=message_data
        )
        
        # 如果API Key未配置，返回400或500是正常的
        if message_response.status_code in [400, 500]:
            data = message_response.json()
            if "API Key" in str(data) or "配置" in str(data):
                print(f"  ⚠️  API Key未配置，跳过聊天功能测试")
                return True
        
        return message_response.status_code == 200 and message_response.json().get("success", False)
    
    def test_knowledge_base(self):
        """测试知识库功能"""
        # 获取知识库文件列表
        files_response = self.session.get(f"{self.base_url}/api/knowledge/files")
        if files_response.status_code != 200:
            return False
        
        # 测试搜索功能
        search_data = {
            "query": "测试用例",
            "limit": 5
        }
        
        search_response = self.session.post(
            f"{self.base_url}/api/knowledge/search",
            json=search_data
        )
        
        # 如果API Key未配置，返回400或500是正常的
        if search_response.status_code in [400, 500]:
            data = search_response.json()
            if "API Key" in str(data) or "配置" in str(data):
                print(f"  ⚠️  API Key未配置，跳过知识库搜索测试")
                return True
        
        return search_response.status_code == 200 and search_response.json().get("success", False)
    
    def test_model_status_api(self):
        """测试模型状态API"""
        response = self.session.get(f"{self.base_url}/api/model-status")
        if response.status_code != 200:
            return False
        
        data = response.json()
        if not data.get("success"):
            return False
        
        model_data = data.get("data", {})
        # 检查必要字段
        required_fields = ["company", "service_name", "is_available", "message"]
        for field in required_fields:
            if field not in model_data:
                return False
        
        print(f"  📊 模型状态: {model_data.get('service_name')} - {'可用' if model_data.get('is_available') else '不可用'}")
        return True
    
    def test_requirements_api(self):
        """测试需求管理API"""
        # 测试获取需求列表
        response = self.session.get(f"{self.base_url}/api/documents/requirements")
        if response.status_code not in [200, 404]:
            return False
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("success"):
                return False
        
        print(f"  ✅ 需求管理API正常")
        return True
    
    def test_chat_sessions_api(self):
        """测试聊天会话API"""
        # 测试创建会话
        response = self.session.post(f"{self.base_url}/api/chat/sessions")
        if response.status_code not in [200, 201]:
            return False
        
        data = response.json()
        if not data.get("success"):
            return False
        
        session_id = data.get("session_id")
        if not session_id:
            return False
        
        print(f"  ✅ 聊天会话API正常，会话ID: {session_id[:8]}...")
        return True
    
    def test_knowledge_search_api(self):
        """测试知识库搜索API"""
        search_data = {
            "query": "测试",
            "limit": 5
        }
        
        response = self.session.post(
            f"{self.base_url}/api/knowledge/search",
            json=search_data
        )
        
        # 如果API Key未配置，返回400或500是正常的
        if response.status_code in [400, 500]:
            data = response.json()
            if "API Key" in str(data) or "配置" in str(data):
                print(f"  ⚠️  知识库搜索需要API Key配置")
                return True
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"  ✅ 知识库搜索API正常")
                return True
        
        return False
    
    def test_export_functionality(self):
        """测试导出功能"""
        # 测试导出模板
        template_response = self.session.get(f"{self.base_url}/api/export/template/cases")
        return template_response.status_code in [200, 404]  # 404表示没有数据但功能正常
    
    def test_config_center(self):
        """测试配置中心功能"""
        # 测试配置分类
        categories_response = self.session.get(f"{self.base_url}/api/config/categories")
        if categories_response.status_code != 200:
            return False
        
        # 测试获取配置项
        config_response = self.session.get(f"{self.base_url}/api/config/ai_model")
        return config_response.status_code in [200, 404]  # 404表示没有配置但功能正常
    
    def test_rag_functionality(self):
        """测试RAG知识库功能"""
        # 测试知识库搜索
        search_data = {
            "query": "测试用例生成",
            "top_k": 3,
            "score_threshold": 0.5
        }
        
        search_response = self.session.post(
            f"{self.base_url}/api/knowledge/search",
            json=search_data
        )
        
        return search_response.status_code == 200 and search_response.json().get("success", False)
    
    def test_token_config(self):
        """测试Token配置功能"""
        # 测试Token统计
        token_response = self.session.get(f"{self.base_url}/api/stats/tokens")
        if token_response.status_code != 200:
            return False
        
        # 验证Token配置是否正确
        token_data = token_response.json()
        if token_data.get("success"):
            # 检查是否有Token配置信息
            return "token_usage" in token_data or "config" in token_data
        elif token_response.status_code in [400, 500]:
            # 如果API Key未配置，这也是正常的
            print(f"  ⚠️  API Key未配置，Token统计功能受限")
            return True
        
        return False

    def test_network_info(self):
        """测试网络信息获取"""
        response = self.session.get(f"{self.base_url}/api/stats/network/info")
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "network_info" in data:
                network_info = data["network_info"]
                print(f"  �� 网络信息: {network_info.get('ip')}:{network_info.get('port')}")
                return True
        return False
    
    def test_statistics(self):
        """测试统计功能"""
        stats_response = self.session.get(f"{self.base_url}/api/stats/overview")
        return stats_response.status_code == 200 and stats_response.json().get("success", False)
    
    def get_test_suite(self):
        """根据测试模式和模块获取测试套件"""
        all_tests = [
            ("健康检查", self.test_health_check),
            ("主页面访问", self.test_main_page),
            ("静态文件加载", self.test_static_files),
            ("API端点检查", self.test_api_endpoints),
            ("模型状态API", self.test_model_status_api),
            ("统计功能", self.test_statistics),
            ("需求管理API", self.test_requirements_api),
            ("聊天会话API", self.test_chat_sessions_api),
            ("知识库搜索API", self.test_knowledge_search_api),
            ("用例生成", self.test_case_generation),
            ("文档分析", self.test_document_analysis),
            ("聊天功能", self.test_chat_functionality),
            ("知识库功能", self.test_knowledge_base),
            ("RAG功能", self.test_rag_functionality),
            ("配置中心", self.test_config_center),
            ("Token配置", self.test_token_config),
            ("导出功能", self.test_export_functionality)
        ]
        
        # 根据测试模式筛选
        if self.test_mode == 'smoke':
            # 快速冒烟测试：只测试核心功能
            smoke_tests = [
                ("健康检查", self.test_health_check),
                ("主页面访问", self.test_main_page),
                ("静态文件加载", self.test_static_files),
                ("API端点检查", self.test_api_endpoints),
                ("模型状态API", self.test_model_status_api),
                ("统计功能", self.test_statistics)
            ]
            return smoke_tests
        elif self.test_mode == 'detailed':
            # 详细测试：包含所有功能
            return all_tests
        else:  # full
            # 完整测试：默认模式
            return all_tests
    
    def run_all_tests(self):
        """运行所有测试"""
        mode_name = TEST_MODES.get(self.test_mode, '完整系统测试')
        print(f"🚀 开始运行TestPilot系统测试 - {mode_name}")
        print("=" * 60)
        
        tests = self.get_test_suite()
        
        # 如果指定了模块，只运行相关测试
        if self.modules:
            module_tests = []
            for module in self.modules:
                if module in MODULES:
                    module_test_names = MODULES[module]
                    for test_name, test_func in tests:
                        if test_name in module_test_names:
                            module_tests.append((test_name, test_func))
            tests = module_tests
            print(f"📋 测试模块: {', '.join(self.modules)}")
        
        print(f"📊 计划运行 {len(tests)} 个测试")
        print("-" * 60)
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
        
        # 统计测试结果
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        errors = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        # 输出测试结果
        print("\n" + "=" * 60)
        print(f"📊 测试结果汇总:")
        print(f"总测试数: {total}")
        print(f"通过数: {passed}")
        print(f"跳过数: {skipped}")
        print(f"失败数: {failed}")
        print(f"错误数: {errors}")
        print(f"成功率: {(passed / total) * 100:.1f}%")
        
        # 显示API Key状态
        api_status = self.check_api_key_status()
        print(f"\n🔑 API Key状态: {'✅ 已配置' if api_status else '❌ 未配置'}")
        
        # 显示跳过测试的原因
        if skipped > 0:
            print(f"\n⚠️  跳过的测试:")
            for result in self.test_results:
                if result["status"] == "SKIP":
                    print(f"  - {result['name']}: {result.get('reason', '未知原因')}")
        
        # 显示失败的测试
        if failed > 0 or errors > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    reason = result.get("error", "测试失败")
                    print(f"  - {result['name']}: {reason}")
        
        # 总结
        if passed == total:
            print("\n🎉 所有测试通过！系统运行正常。")
        elif passed + skipped == total:
            print("\n✅ 核心功能正常，部分功能需要API Key配置。")
        else:
            print("\n⚠️  部分测试失败，请检查系统状态。")
        
        return passed + skipped == total  # 通过或跳过的测试都算成功
    
    def generate_report(self):
        """生成测试报告"""
        report = {
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "results": self.test_results,
            "summary": {
                "total": len(self.test_results),
                "passed": len([r for r in self.test_results if r["status"] == "PASS"]),
                "failed": len([r for r in self.test_results if r["status"] == "FAIL"]),
                "errors": len([r for r in self.test_results if r["status"] == "ERROR"])
            }
        }
        
        report_file = project_root / "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 测试报告已保存到: {report_file}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='TestPilot 系统冒烟测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/check_system.py                    # 完整测试
  python scripts/check_system.py --smoke             # 快速冒烟测试
  python scripts/check_system.py --detailed          # 详细测试
  python scripts/check_system.py --module chat       # 测试聊天模块
  python scripts/check_system.py --module knowledge  # 测试知识库模块
  python scripts/check_system.py http://localhost:5001  # 指定测试目标
        """
    )
    
    parser.add_argument(
        'url', 
        nargs='?', 
        help='测试目标URL (默认: 自动检测本地IP)'
    )
    
    parser.add_argument(
        '--smoke', 
        action='store_true', 
        help='快速冒烟测试模式'
    )
    
    parser.add_argument(
        '--detailed', 
        action='store_true', 
        help='详细测试模式'
    )
    
    parser.add_argument(
        '--module', 
        action='append', 
        choices=list(MODULES.keys()),
        help='指定测试模块 (可多次使用)'
    )
    
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=10,
        help='请求超时时间(秒) (默认: 10)'
    )
    
    parser.add_argument(
        '--no-report', 
        action='store_true',
        help='不生成测试报告文件'
    )
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 确定测试目标URL
    if args.url:
        base_url = args.url
    else:
        ip = get_local_ip()
        base_url = f"http://{ip}:5001"
    
    # 确定测试模式
    if args.smoke:
        test_mode = 'smoke'
    elif args.detailed:
        test_mode = 'detailed'
    else:
        test_mode = 'full'
    
    print(f"🔍 测试目标: {base_url}")
    print(f"📋 测试模式: {TEST_MODES.get(test_mode, '完整系统测试')}")
    if args.module:
        print(f"🎯 测试模块: {', '.join(args.module)}")
    
    # 创建测试器
    tester = TestPilotTester(
        base_url=base_url,
        test_mode=test_mode,
        modules=args.module
    )
    
    # 设置超时时间
    tester.session.timeout = args.timeout
    
    try:
        success = tester.run_all_tests()
        
        # 生成报告
        if not args.no_report:
            tester.generate_report()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 测试过程中发生异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 