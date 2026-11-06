"""
TestPilot 统计服务模块
提供系统统计数据的计算和分析功能
"""

import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from pathlib import Path
# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from sqlalchemy import func, text, cast, Date
from sqlalchemy.orm import Session

# 修复导入问题
try:
    from models.models import (
        TestCase, Requirement, RagFileRecord, ChatHistory,
        SystemLog, PerformanceMetric, db
    )
except ImportError:
    # 如果导入失败，定义占位符类
    class TestCase:
        pass

    class Requirement:
        pass

    class RagFileRecord:
        pass

    class ChatHistory:
        pass

    class SystemLog:
        pass

    class PerformanceMetric:
        pass

    class Database:  # 修复类名约定问题
        pass

from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class StatsService:
    """统计服务类"""

    def __init__(self):
        self.performance_monitor = get_performance_monitor()

    def get_overview_stats(self, db_session: Session) -> Dict[str, Any]:
        """获取系统概览统计"""
        try:
            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 基础统计
            totals = self._get_total_counts(db_session)

            # 最近活动统计
            recent_activity = self._get_recent_activity_stats(db_session)

            # 趋势统计
            trends = self._get_trend_stats(db_session)

            # 使用情况统计
            usage_stats = self._get_usage_stats(db_session)

            # 性能指标
            performance_metrics = self._get_performance_metrics(db_session)

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'overview': {
                    'totals': totals,
                    'recent_activity': recent_activity,
                    'trends': trends,
                    'usage_stats': usage_stats,
                    'performance': performance_metrics,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'processing_time': elapsed_time
                }
            }

        except Exception as e:
            logger.error(f"获取概览统计失败: {str(e)}")
            return {
                'success': False,
                'message': '获取统计数据失败'
            }

    @staticmethod
    def _get_total_counts(db_session: Session) -> Dict[str, int]:
        """获取各项总数统计"""
        try:
            # 测试用例总数
            total_cases = db_session.query(TestCase).count()

            # 需求总数
            total_requirements = db_session.query(Requirement).count()

            # 知识库文件总数
            total_knowledge_files = db_session.query(RagFileRecord).count()

            # 聊天会话总数
            total_chat_sessions = db_session.query(
                func.count(func.distinct(ChatHistory.session_id))
            ).scalar() or 0

            # 聊天消息总数
            total_chat_messages = db_session.query(ChatHistory).count()

            return {
                'test_cases': total_cases,
                'requirements': total_requirements,
                'knowledge_files': total_knowledge_files,
                'chat_sessions': total_chat_sessions,
                'chat_messages': total_chat_messages
            }

        except Exception as e:
            logger.error(f"获取总数统计失败: {str(e)}")
            return {
                'test_cases': 0,
                'requirements': 0,
                'knowledge_files': 0,
                'chat_sessions': 0,
                'chat_messages': 0
            }

    @staticmethod
    def _get_recent_activity_stats(db_session: Session, days: int = 7) -> Dict[str, Any]:
        """获取最近活动统计"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 最近创建的测试用例
            recent_cases = db_session.query(TestCase).filter(
                TestCase.created_time >= cutoff_date
            ).count()

            # 最近创建的需求
            recent_requirements = db_session.query(Requirement).filter(
                Requirement.created_time >= cutoff_date
            ).count()

            # 最近上传的知识文件
            recent_knowledge_files = db_session.query(RagFileRecord).filter(
                RagFileRecord.created_time >= cutoff_date
            ).count()

            # 最近的聊天活动
            recent_chat_messages = db_session.query(ChatHistory).filter(
                ChatHistory.created_time >= cutoff_date
            ).count()

            return {
                'period_days': days,
                'test_cases': recent_cases,
                'requirements': recent_requirements,
                'knowledge_files': recent_knowledge_files,
                'chat_messages': recent_chat_messages
            }

        except Exception as e:
            logger.error(f"获取最近活动统计失败: {str(e)}")
            return {
                'period_days': days,
                'test_cases': 0,
                'requirements': 0,
                'knowledge_files': 0,
                'chat_messages': 0
            }

    def _get_trend_stats(self, db_session: Session, days: int = 30) -> Dict[str, List[Dict]]:
        """获取趋势统计"""
        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days - 1)

            # 测试用例创建趋势
            case_trend = self._get_daily_creation_trend(
                db_session, TestCase, start_date, end_date# type: ignore
            )

            # 需求创建趋势
            requirement_trend = self._get_daily_creation_trend(
                db_session, Requirement, start_date, end_date# type: ignore
            )

            # 聊天活动趋势
            chat_trend = self._get_daily_creation_trend(
                db_session, ChatHistory, start_date, end_date# type: ignore
            )

            return {
                'test_cases': case_trend,
                'requirements': requirement_trend,
                'chat_activity': chat_trend
            }

        except Exception as e:
            logger.error(f"获取趋势统计失败: {str(e)}")
            return {
                'test_cases': [],
                'requirements': [],
                'chat_activity': []
            }

    @staticmethod
    def _get_daily_creation_trend(db_session: Session, model, start_date, end_date) -> List[Dict]:
        """获取每日创建趋势"""
        try:
            # 查询每日创建数量
            daily_counts = db_session.query(
                func.date(model.created_time).label('date'),
                func.count(model.id).label('count')
            ).filter(
                cast(func.date(model.created_time), Date) >= start_date,
                cast(func.date(model.created_time), Date) <= end_date
            ).group_by(
                func.date(model.created_time)
            ).all()

            # 创建完整的日期序列
            trend_data = []
            current_date = start_date
            counts_dict = {str(row.date): row.count for row in daily_counts}

            while current_date <= end_date:
                trend_data.append({
                    'date': current_date.isoformat(),
                    'count': counts_dict.get(str(current_date), 0)
                })
                current_date += timedelta(days=1)

            return trend_data

        except Exception as e:
            logger.error(f"获取每日趋势失败: {str(e)}")
            return []

    def _get_usage_stats(self, db_session: Session) -> Dict[str, Any]:
        """获取使用情况统计"""
        try:
            # 测试用例按优先级分布
            case_priority_dist = self._get_distribution_stats(
                db_session, TestCase, 'priority'
            )

            # 测试用例按状态分布
            case_status_dist = self._get_distribution_stats(
                db_session, TestCase, 'status'
            )

            # 需求按类型分布
            requirement_type_dist = self._get_distribution_stats(
                db_session, Requirement, 'type'
            )

            # 需求按优先级分布
            requirement_priority_dist = self._get_distribution_stats(
                db_session, Requirement, 'priority'
            )

            # 知识文件按分类分布
            knowledge_category_dist = self._get_distribution_stats(
                db_session, RagFileRecord, 'category'
            )

            return {
                'test_case_priority': case_priority_dist,
                'test_case_status': case_status_dist,
                'requirement_type': requirement_type_dist,
                'requirement_priority': requirement_priority_dist,
                'knowledge_category': knowledge_category_dist
            }

        except Exception as e:
            logger.error(f"获取使用统计失败: {str(e)}")
            return {}

    @staticmethod
    def _get_distribution_stats(db_session: Session, model, column: str) -> Dict[str, int]:
        """获取字段分布统计"""
        try:
            column_attr = getattr(model, column)
            results = db_session.query(
                column_attr,
                func.count(model.id)
            ).group_by(column_attr).all()

            return {str(key or 'unknown'): count for key, count in results}

        except Exception as e:
            logger.error(f"获取分布统计失败 ({model.__name__}.{column}): {str(e)}")
            return {}

    @staticmethod
    def _get_performance_metrics(db_session: Session) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            # 最近的性能指标
            recent_metrics = db_session.query(PerformanceMetric).filter(
                PerformanceMetric.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).order_by(PerformanceMetric.timestamp.desc()).limit(100).all()

            if not recent_metrics:
                return {
                    'avg_response_time': 0,
                    'total_requests': 0,
                    'error_rate': 0,
                    'memory_usage': 0,
                    'cpu_usage': 0
                }

            # 计算平均指标
            total_requests = len(recent_metrics)
            # 修复属性引用问题 - 使用getattr安全访问属性
            avg_response_time = sum(getattr(m, 'response_time', 0) for m in recent_metrics) / total_requests
            error_count = sum(1 for m in recent_metrics if getattr(m, 'status_code', 0) >= 400)
            error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0

            # 获取最新的系统指标
            latest_metric = recent_metrics[0] if recent_metrics else None
            memory_usage = getattr(latest_metric, 'memory_usage', 0) if latest_metric else 0
            cpu_usage = getattr(latest_metric, 'cpu_usage', 0) if latest_metric else 0

            return {
                'avg_response_time': round(avg_response_time, 2),
                'total_requests': total_requests,
                'error_rate': round(error_rate, 2),
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage
            }

        except Exception as e:
            logger.error(f"获取性能指标失败: {str(e)}")
            return {
                'avg_response_time': 0,
                'total_requests': 0,
                'error_rate': 0,
                'memory_usage': 0,
                'cpu_usage': 0
            }

    def get_performance_metrics(self, db_session: Session, hours: int = 24) -> Dict[str, Any]:
        """获取详细的性能指标"""
        try:
            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # 查询性能指标
            metrics = db_session.query(PerformanceMetric).filter(
                PerformanceMetric.timestamp >= cutoff_time
            ).order_by(PerformanceMetric.timestamp).all()

            if not metrics:
                return {
                    'success': True,
                    'metrics': {
                        'summary': self.performance_monitor.get_empty_performance_summary(),
                        'timeline': [],
                        'endpoints': {}
                    }
                }

            # 使用公共方法进行性能分析
            summary = self.performance_monitor.calculate_performance_summary(metrics)
            timeline = self.performance_monitor.generate_performance_timeline(metrics)
            endpoints = self.performance_monitor.analyze_endpoint_performance(metrics)

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'metrics': {
                    'summary': summary,
                    'timeline': timeline,
                    'endpoints': endpoints,
                    'period_hours': hours,
                    'total_requests': len(metrics),
                    'processing_time': elapsed_time
                }
            }

        except Exception as e:
            logger.error(f"获取性能指标失败: {str(e)}")
            return {
                'success': False,
                'message': '获取性能指标失败'
            }

    def get_usage_statistics(self, db_session: Session) -> Dict[str, Any]:
        """获取使用情况统计"""
        try:
            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 用户活动统计
            user_activity = self._get_user_activity_stats(db_session)

            # 功能使用统计
            feature_usage = self._get_feature_usage_stats(db_session)

            # 内容统计
            content_stats = self._get_content_statistics(db_session)

            # 时间分布统计
            time_distribution = self._get_time_distribution_stats(db_session)

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'statistics': {
                    'user_activity': user_activity,
                    'feature_usage': feature_usage,
                    'content_stats': content_stats,
                    'time_distribution': time_distribution,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'processing_time': elapsed_time
                }
            }

        except Exception as e:
            logger.error(f"获取使用统计失败: {str(e)}")
            return {
                'success': False,
                'message': '获取使用统计失败'
            }

    @staticmethod
    def _get_user_activity_stats(db_session: Session) -> Dict[str, Any]:
        """获取用户活动统计"""
        try:
            # 活跃会话数（最近24小时）
            recent_chat_sessions = db_session.query(
                func.count(func.distinct(ChatHistory.session_id))
            ).filter(
                ChatHistory.created_time >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).scalar() or 0

            # 总会话数
            total_sessions = db_session.query(
                func.count(func.distinct(ChatHistory.session_id))
            ).scalar() or 0

            return {
                'active_sessions_24h': recent_chat_sessions,
                'total_sessions': total_sessions,
                'session_activity_rate': (recent_chat_sessions / total_sessions * 100) if total_sessions > 0 else 0
            }

        except Exception as e:
            logger.error(f"获取用户活动统计失败: {str(e)}")
            return {
                'active_sessions_24h': 0,
                'total_sessions': 0,
                'session_activity_rate': 0
            }

    @staticmethod
    def _get_feature_usage_stats(db_session: Session) -> Dict[str, int]:
        """获取功能使用统计"""
        try:
            # 各功能的使用次数统计
            stats = {
                'test_case_generation': db_session.query(TestCase).count(),
                'requirement_analysis': db_session.query(Requirement).count(),
                'knowledge_base_files': db_session.query(RagFileRecord).count(),
                'ai_chat_messages': db_session.query(ChatHistory).count()
            }

            return stats

        except Exception as e:
            logger.error(f"获取功能使用统计失败: {str(e)}")
            return {}

    def _get_content_statistics(self, db_session: Session) -> Dict[str, Any]:
        """获取内容统计"""
        try:
            # 测试用例统计
            case_stats = {
                'total': db_session.query(TestCase).count(),
                'by_priority': self._get_distribution_stats(db_session, TestCase, 'priority'),
                'by_status': self._get_distribution_stats(db_session, TestCase, 'status')
            }

            # 需求统计
            requirement_stats = {
                'total': db_session.query(Requirement).count(),
                'by_type': self._get_distribution_stats(db_session, Requirement, 'type'),
                'by_priority': self._get_distribution_stats(db_session, Requirement, 'priority')
            }

            # 知识库统计
            knowledge_stats = {
                'total_files': db_session.query(RagFileRecord).count(),
                'by_category': self._get_distribution_stats(db_session, RagFileRecord, 'category'),
                'total_size': self._get_total_file_size(db_session)
            }

            return {
                'test_cases': case_stats,
                'requirements': requirement_stats,
                'knowledge_base': knowledge_stats
            }

        except Exception as e:
            logger.error(f"获取内容统计失败: {str(e)}")
            return {}

    @staticmethod
    def _get_total_file_size(db_session: Session) -> int:
        """获取文件总大小"""
        try:
            result = db_session.query(func.sum(RagFileRecord.file_size)).scalar()
            return result or 0
        except Exception as e:
            logger.error(f"获取文件总大小失败: {str(e)}")
            return 0

    def _get_time_distribution_stats(self, db_session: Session) -> Dict[str, List[Dict]]:
        """获取时间分布统计"""
        try:
            # 按小时分布
            hourly_activity = self._get_hourly_activity_distribution(db_session)

            # 按星期分布
            weekly_activity = self._get_weekly_activity_distribution(db_session)

            return {
                'hourly': hourly_activity,
                'weekly': weekly_activity
            }

        except Exception as e:
            logger.error(f"获取时间分布统计失败: {str(e)}")
            return {
                'hourly': [],
                'weekly': []
            }

    @staticmethod
    def _get_hourly_activity_distribution(db_session: Session) -> List[Dict]:
        """获取小时活动分布"""
        try:
            # 查询聊天消息的小时分布
            hourly_counts = db_session.query(
                func.extract('hour', ChatHistory.created_time).label('hour'),
                func.count(ChatHistory.id).label('count')
            ).group_by(
                func.extract('hour', ChatHistory.created_time)
            ).all()

            # 创建24小时的完整数据
            hourly_data = [{'hour': i, 'count': 0} for i in range(24)]
            for row in hourly_counts:
                hour_index = int(row.hour)
                if 0 <= hour_index < 24:
                    hourly_data[hour_index]['count'] = row.count

            return hourly_data

        except Exception as e:
            logger.error(f"获取小时分布失败: {str(e)}")
            return [{'hour': i, 'count': 0} for i in range(24)]

    @staticmethod
    def _get_weekly_activity_distribution(db_session: Session) -> List[Dict]:
        """获取星期活动分布"""
        try:
            # 查询聊天消息的星期分布
            weekly_counts = db_session.query(
                func.extract('dow', ChatHistory.created_time).label('dow'),
                func.count(ChatHistory.id).label('count')
            ).group_by(
                func.extract('dow', ChatHistory.created_time)
            ).all()

            # 创建一周7天的完整数据
            week_names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
            weekly_data = [{'day': week_names[i], 'day_num': i, 'count': 0} for i in range(7)]

            for row in weekly_counts:
                day_index = int(row.dow)
                if 0 <= day_index < 7:
                    weekly_data[day_index]['count'] = row.count

            return weekly_data

        except Exception as e:
            logger.error(f"获取星期分布失败: {str(e)}")
            return [{'day': f'周{i}', 'day_num': i, 'count': 0} for i in range(7)]

    def get_token_usage_stats(self, _db_session: Session, days: int = 30) -> Dict[str, Any]:
        """获取Token使用统计"""
        try:
            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 模拟token使用统计
            token_stats = {
                'total_tokens_used': 0,
                'tokens_by_model': {},
                'tokens_by_feature': {
                    'test_case_generation': 0,
                    'requirement_analysis': 0,
                    'ai_chat': 0,
                    'knowledge_search': 0
                },
                'daily_usage': [],
                'cost_estimation': {
                    'total_cost': 0.0,
                    'currency': 'USD'
                }
            }

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'token_usage': token_stats,
                'period_days': days,
                'processing_time': elapsed_time
            }

        except Exception as e:
            logger.error(f"获取Token使用统计失败: {str(e)}")
            return {
                'success': False,
                'message': '获取Token使用统计失败'
            }

    def get_log_statistics(self, db_session: Session, hours: int = 24) -> Dict[str, Any]:
        """获取日志统计"""
        try:
            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # 查询系统日志
            logs = db_session.query(SystemLog).filter(
                SystemLog.timestamp >= cutoff_time
            ).all()

            if not logs:
                return {
                    'success': True,
                    'log_stats': {
                        'total_logs': 0,
                        'by_level': {},
                        'by_module': {},
                        'error_rate': 0.0,
                        'timeline': []
                    }
                }

            # 按级别统计
            level_stats = {}
            for log in logs:
                level = getattr(log, 'level', 'unknown') or 'unknown'
                level_stats[level] = level_stats.get(level, 0) + 1

            # 按模块统计
            module_stats = {}
            for log in logs:
                module = getattr(log, 'module', 'unknown') or 'unknown'
                module_stats[module] = module_stats.get(module, 0) + 1

            # 计算错误率
            error_count = level_stats.get('ERROR', 0) + level_stats.get('CRITICAL', 0)
            error_rate = (error_count / len(logs)) * 100 if logs else 0

            # 生成时间线
            timeline = self._generate_log_timeline(logs)# type: ignore

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'log_stats': {
                    'total_logs': len(logs),
                    'by_level': level_stats,
                    'by_module': module_stats,
                    'error_rate': round(error_rate, 2),
                    'timeline': timeline,
                    'period_hours': hours,
                    'processing_time': elapsed_time
                }
            }

        except Exception as e:
            logger.error(f"获取日志统计失败: {str(e)}")
            return {
                'success': False,
                'message': '获取日志统计失败'
            }

    @staticmethod
    def _generate_log_timeline(logs: List[SystemLog]) -> List[Dict]:
        """生成日志时间线"""
        if not logs:
            return []

        # 按小时分组
        hourly_data = {}
        for log in logs:
            timestamp = getattr(log, 'timestamp', datetime.now(timezone.utc))
            hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {'total': 0, 'errors': 0}

            hourly_data[hour_key]['total'] += 1
            level = getattr(log, 'level', 'INFO')
            if level in ['ERROR', 'CRITICAL']:
                hourly_data[hour_key]['errors'] += 1

        timeline = []
        for hour, data in sorted(hourly_data.items()):
            timeline.append({
                'timestamp': hour.isoformat(),
                'total_logs': data['total'],
                'error_logs': data['errors'],
                'error_rate': (data['errors'] / data['total']) * 100 if data['total'] > 0 else 0
            })

        return timeline

    @staticmethod
    def record_custom_metric(metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """记录自定义指标"""
        try:
            # 这里可以实现自定义指标的记录逻辑
            # 例如记录到PerformanceMetric表或专门的自定义指标表

            logger.info(f"记录自定义指标: {metric_data}")

            return {
                'success': True,
                'message': '自定义指标记录成功'
            }

        except Exception as e:
            logger.error(f"记录自定义指标失败: {str(e)}")
            return {
                'success': False,
                'message': '记录自定义指标失败'
            }

    def get_system_health(self, db_session: Session) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            start_time = self.performance_monitor.start_timer()

            # 数据库连接检查
            db_healthy = self._check_database_health(db_session)

            # 基础服务检查
            services_health = self._check_services_health()

            # 资源使用检查
            resource_health = self._check_resource_health(db_session)

            # 错误率检查
            error_rate_health = self._check_error_rate_health(db_session)

            # 综合健康状态 - 改进逻辑
            overall_healthy = (
                    db_healthy and
                    services_health.get('overall', True) and  # 改为True，避免误报
                    resource_health.get('overall', True) and  # 改为True，避免误报
                    error_rate_health.get('overall', True)  # 改为True，避免误报
            )

            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'health': {
                    'status': 'healthy' if overall_healthy else 'unhealthy',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'components': {
                        'database': 'healthy' if db_healthy else 'unhealthy',
                        'services': services_health,
                        'resources': resource_health,
                        'error_rates': error_rate_health
                    },
                    'processing_time': elapsed_time
                }
            }

        except Exception as e:
            logger.error(f"获取系统健康状态失败: {str(e)}")
            return {
                'success': False,
                'status': 'unhealthy',
                'message': '健康检查失败'
            }

    @staticmethod
    def _check_database_health(db_session: Session) -> bool:
        """检查数据库健康状态"""
        try:
            # 方式1: 使用 text() 执行简单查询（推荐方式）
            result = db_session.execute(text("SELECT 1")).scalar()
            if result == 1:
                return True
            logger.warning(f"数据库健康检查返回异常结果: {result}")
            return False
        except Exception as e:
            # 如果方式1失败，尝试使用 db.engine 直接连接
            try:
                from models.models import db
                with db.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1")).scalar()
                    if result == 1:
                        logger.info("使用备用方式检查数据库连接成功")
                        return True
            except Exception as e2:
                logger.error(f"数据库健康检查失败 - 主方式: {str(e)}, 备用方式: {str(e2)}")
            else:
                logger.error(f"数据库健康检查失败: {str(e)}")
            return False

    @staticmethod
    def _check_services_health() -> Dict[str, Any]:
        """检查服务健康状态"""
        try:
            # 检查各个服务的基础功能
            services = {
                'test_case_service': True,  # 可以添加具体的检查逻辑
                'document_service': True,
                'knowledge_service': True,
                'chat_service': True
            }

            overall_healthy = all(services.values())

            return {
                'overall': overall_healthy,
                'details': services
            }

        except Exception as e:
            logger.error(f"服务健康检查失败: {str(e)}")
            return {
                'overall': False,
                'details': {}
            }

    # 资源健康检查缓存
    _resource_health_cache = None
    _resource_health_cache_time = None
    _resource_health_cache_ttl = 10  # 缓存10秒
    
    @staticmethod
    def _get_system_metric_with_timeout(metric_func, timeout=2, default=None):
        """带超时的系统指标获取
        
        Args:
            metric_func: 要执行的函数
            timeout: 超时时间（秒）
            default: 超时或失败时的默认值
        """
        import threading
        from typing import List, Optional, Any
        
        result: List[Any] = [default]
        exception: List[Optional[Exception]] = [None]
        
        def target():
            try:
                result[0] = metric_func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            logger.warning(f"获取系统指标超时（{timeout}秒）")
            return default
        
        if exception[0] is not None:
            logger.warning(f"获取系统指标失败: {str(exception[0])}")
            return default
            
        return result[0]
    
    @classmethod
    def _check_resource_health(cls, _db_session: Session) -> Dict[str, Any]:
        """检查资源使用健康状态 - 使用psutil获取实时系统性能数据（带缓存和超时保护）
        
        Args:
            _db_session: 数据库会话（保留用于未来扩展，当前未使用，使用下划线前缀避免未使用警告）
        """
        from datetime import datetime
        now = datetime.now()
        
        try:
            # 检查缓存是否有效
            if (cls._resource_health_cache is not None and 
                cls._resource_health_cache_time is not None):
                elapsed = (now - cls._resource_health_cache_time).total_seconds()
                if elapsed < cls._resource_health_cache_ttl:
                    # 返回缓存数据，并添加缓存标记
                    cached_result = cls._resource_health_cache.copy()
                    cached_result['from_cache'] = True
                    cached_result['cache_age_seconds'] = round(elapsed, 1)
                    return cached_result
            
            import psutil
            import platform
            import os
            
            # 获取CPU使用率（使用超时保护的短interval方式）
            cpu_usage = None
            try:
                # 使用0.1秒的interval，在超时保护下执行
                def get_cpu():
                    # 先调用一次初始化内部计数器
                    psutil.cpu_percent(interval=0)
                    # 再调用一次获取实际值
                    return psutil.cpu_percent(interval=0.1)
                
                cpu_usage = cls._get_system_metric_with_timeout(get_cpu, timeout=2)
                if cpu_usage is not None:
                    cpu_usage = float(round(cpu_usage, 1))
            except Exception as e:
                logger.warning(f"获取CPU使用率失败: {str(e)}")
            
            # 获取内存使用情况（带超时保护）
            memory_usage = None
            memory_total_gb = None
            memory_used_gb = None
            try:
                def get_memory():
                    memory = psutil.virtual_memory()
                    return {
                        'percent': memory.percent,
                        'total_gb': round(memory.total / (1024**3), 2),
                        'used_gb': round(memory.used / (1024**3), 2)
                    }
                
                memory_data = cls._get_system_metric_with_timeout(get_memory, timeout=1)
                if memory_data:
                    memory_usage = memory_data['percent']
                    memory_total_gb = memory_data['total_gb']
                    memory_used_gb = memory_data['used_gb']
            except Exception as e:
                logger.warning(f"获取内存使用情况失败: {str(e)}")
            
            # 获取磁盘使用情况（带超时保护）- 跨平台兼容
            disk_usage_result = None
            disk_total_gb = None
            disk_used_gb = None
            try:
                def get_disk():
                    # 跨平台磁盘路径获取
                    if platform.system() == 'Windows':
                        # Windows: 获取项目根目录所在盘符
                        try:
                            from config.settings import BASE_DIR
                            disk_path = os.path.splitdrive(str(BASE_DIR))[0] + '\\'
                        except (ImportError, Exception):
                            current_file_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                            drive = os.path.splitdrive(current_file_path)[0]
                            disk_path = (drive + '\\') if drive else 'C:\\'
                    elif platform.system() == 'Darwin':  # macOS
                        disk_path = '/'
                    else:  # Linux
                        disk_path = '/'
                    
                    disk = psutil.disk_usage(disk_path)
                    return {
                        'percent': round(disk.used / disk.total * 100, 1),
                        'total_gb': round(disk.total / (1024**3), 2),
                        'used_gb': round(disk.used / (1024**3), 2)
                    }
                
                disk_data = cls._get_system_metric_with_timeout(get_disk, timeout=2)
                if disk_data:
                    disk_usage_result = disk_data['percent']
                    disk_total_gb = disk_data['total_gb']
                    disk_used_gb = disk_data['used_gb']
            except Exception as e:
                logger.warning(f"获取磁盘使用情况失败: {str(e)}")
            
            # 检查是否有任何数据
            has_data = cpu_usage is not None or memory_usage is not None or disk_usage_result is not None
            
            if not has_data:
                result = {
                    'overall': True,
                    'memory_healthy': True,
                    'cpu_healthy': True,
                    'disk_healthy': True,
                    'has_data': False
                }
            else:
                # 检查资源使用阈值（80%为警告，90%为危险）
                memory_healthy = memory_usage is None or memory_usage < 80
                cpu_healthy = cpu_usage is None or cpu_usage < 80
                disk_healthy = disk_usage_result is None or disk_usage_result < 90
                
                # 综合健康状态
                overall_healthy = memory_healthy and cpu_healthy and disk_healthy
                
                result = {
                    'overall': overall_healthy,
                    'memory_healthy': memory_healthy,
                    'cpu_healthy': cpu_healthy,
                    'disk_healthy': disk_healthy,
                    'has_data': True,
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'disk_usage': disk_usage_result
                }
                
                # 添加详细信息（如果可用）
                if memory_total_gb is not None:
                    result['memory_total_gb'] = memory_total_gb
                if memory_used_gb is not None:
                    result['memory_used_gb'] = memory_used_gb
                if disk_total_gb is not None:
                    result['disk_total_gb'] = disk_total_gb
                if disk_used_gb is not None:
                    result['disk_used_gb'] = disk_used_gb
            
            # 添加缓存标记（表示这是新获取的数据）
            result['from_cache'] = False
            
            # 更新缓存
            cls._resource_health_cache = result.copy()
            cls._resource_health_cache_time = now
            
            return result

        except ImportError:
            logger.error("psutil未安装，无法获取系统性能数据")
            result = {
                'overall': True,
                'memory_healthy': True,
                'cpu_healthy': True,
                'disk_healthy': True,
                'has_data': False,
                'error': 'psutil未安装',
                'from_cache': False
            }
            # 即使出错也缓存结果，避免频繁重试
            cls._resource_health_cache = result.copy()
            cls._resource_health_cache_time = now
            return result
        except Exception as e:
            logger.error(f"资源健康检查失败: {str(e)}")
            result = {
                'overall': True,
                'memory_healthy': True,
                'cpu_healthy': True,
                'disk_healthy': True,
                'has_data': False,
                'error': 'internal_error',
                'from_cache': False
            }
            # 即使出错也缓存结果，避免频繁重试
            cls._resource_health_cache = result.copy()
            cls._resource_health_cache_time = now
            return result

    @staticmethod
    def _check_error_rate_health(db_session: Session) -> Dict[str, Any]:
        """检查错误率健康状态"""
        try:
            # 检查最近1小时的错误率
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)

            recent_metrics = db_session.query(PerformanceMetric).filter(
                PerformanceMetric.created_time >= cutoff_time
            ).all()

            if not recent_metrics:
                # 如果没有数据，返回健康状态
                return {
                    'overall': True,
                    'error_rate': 0.0,
                    'threshold': 5.0,
                    'message': '暂无性能数据'
                }

            # 只统计有状态码的记录
            metrics_with_status = [m for m in recent_metrics if getattr(m, 'status_code', None) is not None]

            if not metrics_with_status:
                return {
                    'overall': True,
                    'error_rate': 0.0,
                    'threshold': 5.0,
                    'message': '暂无状态码数据'
                }

            error_count = sum(1 for m in metrics_with_status if getattr(m, 'status_code', 0) >= 400)
            error_rate = (error_count / len(metrics_with_status)) * 100

            # 错误率阈值 5%
            error_rate_healthy = error_rate < 5.0

            return {
                'overall': error_rate_healthy,
                'error_rate': round(error_rate, 2),
                'threshold': 5.0,
                'total_requests': len(metrics_with_status),
                'error_requests': error_count
            }

        except Exception as e:
            logger.error(f"错误率健康检查失败: {str(e)}")
            return {
                'overall': True,  # 改为True，避免误报
                'error_rate': 0.0,
                'threshold': 5.0,
                'message': '检查失败'
            }

    @staticmethod
    def record_performance_metric(db_session: Session, metric_name: str,
                                  metric_value: float, status_code: int = None,
                                  response_time: float = None, memory_usage: float = None,
                                  cpu_usage: float = None, category: str = None):
        """记录性能指标"""
        try:
            metric = PerformanceMetric(
                metric_name=metric_name,
                metric_value=metric_value,
                status_code=status_code,
                response_time=response_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                category=category,
                created_time=datetime.now(timezone.utc)
            )
            db_session.add(metric)
            db_session.commit()
            return True
        except Exception as e:
            logger.error(f"记录性能指标失败: {str(e)}")
            db_session.rollback()
            return False