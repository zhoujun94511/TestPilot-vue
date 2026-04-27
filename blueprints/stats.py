#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from sqlalchemy import func
from datetime import datetime, timedelta
from werkzeug.exceptions import BadRequest
from utils.utils_core.logger import get_logger
from services.stats_service import StatsService
from flask import Blueprint, request, jsonify, current_app
from utils.utils_core.common_utils import get_network_info
from models.models import db, TestCase, Requirement, ChatHistory, PerformanceMetric, SystemLog, ChatSession

# 创建蓝图
stats_bp = Blueprint('stats', __name__)

# 初始化服务
stats_service = StatsService()

# 设置日志
logger = get_logger(__name__)


@stats_bp.route('/overview', methods=['GET'])
def get_overview_stats():
    """获取总体统计概览"""
    try:
        # 获取时间范围参数
        days = request.args.get('days', 7, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 基础统计
        total_cases = TestCase.query.count()
        total_requirements = Requirement.query.count()
        total_chat_sessions = ChatSession.query.filter(ChatSession.is_deleted == False).count()
        
        # 知识库文件统计
        from models.models import RagFileRecord
        total_knowledge_files = RagFileRecord.query.filter(RagFileRecord.status == 'active').count()

        # 最近活动统计
        recent_cases = TestCase.query.filter(TestCase.created_time >= start_date).count()
        recent_requirements = Requirement.query.filter(Requirement.created_time >= start_date).count()
        recent_chats = ChatHistory.query.filter(ChatHistory.created_time >= start_date).count()

        # 状态分布
        case_status_stats = db.session.query(
            TestCase.status,
            func.count(TestCase.id)
        ).group_by(TestCase.status).all()

        priority_stats = db.session.query(
            TestCase.priority,
            func.count(TestCase.id)
        ).group_by(TestCase.priority).all()

        return jsonify({
            'success': True,
            'overview': {
                'totals': {
                    'test_cases': total_cases,
                    'requirements': total_requirements,
                    'chat_sessions': total_chat_sessions,
                    'knowledge_files': total_knowledge_files
                },
                'recent_activity': {
                    'new_cases': recent_cases,
                    'new_requirements': recent_requirements,
                    'chat_messages': recent_chats,
                    'period_days': days
                },
                'distributions': {
                    'case_status': dict(case_status_stats),
                    'case_priority': dict(priority_stats)
                }
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取概览统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取统计概览失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/performance', methods=['GET'])
def get_performance_stats():
    """获取性能统计"""
    try:
        # 获取时间范围参数
        hours = request.args.get('hours', 24, type=int)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # 从性能指标表获取数据
        metrics = PerformanceMetric.query.filter(
            PerformanceMetric.created_time >= start_time
        ).order_by(PerformanceMetric.created_time.desc()).all()

        # 按类别整理指标
        performance_data = {}
        for metric in metrics:
            category = metric.category or 'general'
            if category not in performance_data:
                performance_data[category] = []

            performance_data[category].append({
                'name': metric.metric_name,
                'value': metric.metric_value,
                'unit': metric.metric_unit,
                'timestamp': metric.created_time.isoformat()
            })

        # 计算平均值和趋势
        summary = {}
        for category, metrics_list in performance_data.items():
            if metrics_list:
                values = [m['value'] for m in metrics_list]
                summary[category] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }

        return jsonify({
            'success': True,
            'performance': {
                'period_hours': hours,
                'metrics': performance_data,
                'summary': summary
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取性能统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取性能统计失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/usage', methods=['GET'])
def get_usage_stats():
    """获取使用统计"""
    try:
        # 获取时间范围参数
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 按日期统计用例生成数量
        daily_cases = db.session.query(
            func.date(TestCase.created_time).label('date'),
            func.count(TestCase.id).label('count')
        ).filter(
            TestCase.created_time >= start_date
        ).group_by(func.date(TestCase.created_time)).all()

        # 按日期统计需求分析数量
        daily_requirements = db.session.query(
            func.date(Requirement.created_time).label('date'),
            func.count(Requirement.id).label('count')
        ).filter(
            Requirement.created_time >= start_date
        ).group_by(func.date(Requirement.created_time)).all()

        # 按日期统计聊天消息数量
        daily_chats = db.session.query(
            func.date(ChatHistory.created_time).label('date'),
            func.count(ChatHistory.id).label('count')
        ).filter(
            ChatHistory.created_time >= start_date
        ).group_by(func.date(ChatHistory.created_time)).all()

        # 按分类统计用例数量
        category_stats = db.session.query(
            TestCase.category,
            func.count(TestCase.id)
        ).filter(
            TestCase.created_time >= start_date
        ).group_by(TestCase.category).all()

        return jsonify({
            'success': True,
            'usage': {
                'period_days': days,
                'daily_trends': {
                    'test_cases': [{'date': str(d), 'count': c} for d, c in daily_cases],
                    'requirements': [{'date': str(d), 'count': c} for d, c in daily_requirements],
                    'chat_messages': [{'date': str(d), 'count': c} for d, c in daily_chats]
                },
                'category_distribution': dict(category_stats)
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取使用统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取使用统计失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/tokens', methods=['GET'])
def get_token_stats():
    """获取Token使用统计"""
    try:
        # 获取时间范围参数
        days = request.args.get('days', 7, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Token使用统计
        token_stats = db.session.query(
            func.sum(ChatHistory.tokens_used).label('total_tokens'),
            func.avg(ChatHistory.tokens_used).label('avg_tokens'),
            func.count(ChatHistory.id).label('message_count')
        ).filter(
            ChatHistory.created_time >= start_date,
            ChatHistory.tokens_used > 0
        ).first()

        # 按模型统计Token使用
        model_stats = db.session.query(
            ChatHistory.model_name,
            func.sum(ChatHistory.tokens_used).label('total_tokens'),
            func.count(ChatHistory.id).label('message_count')
        ).filter(
            ChatHistory.created_time >= start_date,
            ChatHistory.tokens_used > 0
        ).group_by(ChatHistory.model_name).all()

        # 按日期统计Token使用
        daily_tokens = db.session.query(
            func.date(ChatHistory.created_time).label('date'),
            func.sum(ChatHistory.tokens_used).label('total_tokens')
        ).filter(
            ChatHistory.created_time >= start_date,
            ChatHistory.tokens_used > 0
        ).group_by(func.date(ChatHistory.created_time)).all()

        return jsonify({
            'success': True,
            'tokens': {
                'period_days': days,
                'summary': {
                    'total_tokens': int(token_stats.total_tokens or 0),
                    'avg_tokens_per_message': round(float(token_stats.avg_tokens or 0), 2),
                    'total_messages': int(token_stats.message_count or 0)
                },
                'by_model': [
                    {
                        'model': model,
                        'total_tokens': int(tokens),
                        'message_count': int(count)
                    }
                    for model, tokens, count in model_stats
                ],
                'daily_usage': [
                    {
                        'date': str(date),
                        'total_tokens': int(tokens or 0)
                    }
                    for date, tokens in daily_tokens
                ]
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取Token统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取Token统计失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/logs', methods=['GET'])
def get_log_stats():
    """获取日志统计"""
    try:
        # 获取时间范围参数
        hours = request.args.get('hours', 24, type=int)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # 按日志级别统计
        level_stats = db.session.query(
            SystemLog.level,
            func.count(SystemLog.id)
        ).filter(
            SystemLog.created_time >= start_time
        ).group_by(SystemLog.level).all()

        # 按模块统计
        module_stats = db.session.query(
            SystemLog.module,
            func.count(SystemLog.id)
        ).filter(
            SystemLog.created_time >= start_time,
            SystemLog.module.isnot(None)
        ).group_by(SystemLog.module).order_by(
            func.count(SystemLog.id).desc()
        ).limit(10).all()

        # 最近的错误日志
        recent_errors = SystemLog.query.filter(
            SystemLog.created_time >= start_time,
            SystemLog.level.in_(['ERROR', 'CRITICAL'])
        ).order_by(SystemLog.created_time.desc()).limit(20).all()

        return jsonify({
            'success': True,
            'logs': {
                'period_hours': hours,
                'level_distribution': dict(level_stats),
                'top_modules': [
                    {'module': module or 'unknown', 'count': count}
                    for module, count in module_stats
                ],
                'recent_errors': [
                    {
                        'id': log.id,
                        'level': log.level,
                        'message': log.message[:200] + '...' if len(log.message) > 200 else log.message,
                        'module': log.module,
                        'timestamp': log.created_time.isoformat()
                    }
                    for log in recent_errors
                ]
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取日志统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取日志统计失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/export', methods=['GET'])
def export_stats():
    """导出统计数据"""
    try:
        # 获取导出参数
        export_type = request.args.get('type', 'overview')
        format_type = request.args.get('format', 'json')
        days = request.args.get('days', 7, type=int)

        # 获取数据
        if export_type == 'overview':
            # 获取概览数据
            total_cases = TestCase.query.count()
            total_requirements = Requirement.query.count()
            total_chat_sessions = db.session.query(func.count(func.distinct(ChatHistory.session_id))) \
                .join(ChatSession, ChatHistory.session_id == ChatSession.session_id) \
                .filter(ChatSession.is_deleted == False) \
                .scalar()

            data = {
                'export_type': 'overview',
                'totals': {
                    'test_cases': total_cases,
                    'requirements': total_requirements,
                    'chat_sessions': total_chat_sessions
                },
                'export_time': datetime.now().isoformat(),
                'format': format_type,
                'period_days': days
            }
        elif export_type == 'performance':
            # 获取性能数据
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            metrics = PerformanceMetric.query.filter(
                PerformanceMetric.created_time >= start_time
            ).order_by(PerformanceMetric.created_time.desc()).all()

            data = {
                'export_type': 'performance',
                'period_days': days,
                'format': format_type,
                'metrics_count': len(metrics),
                'export_time': datetime.now().isoformat()
            }
        elif export_type == 'usage':
            # 获取使用数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            recent_cases = TestCase.query.filter(TestCase.created_time >= start_date).count()
            recent_requirements = Requirement.query.filter(Requirement.created_time >= start_date).count()
            recent_chats = ChatHistory.query.filter(ChatHistory.created_time >= start_date).count()

            data = {
                'export_type': 'usage',
                'period_days': days,
                'format': format_type,
                'usage_stats': {
                    'recent_cases': recent_cases,
                    'recent_requirements': recent_requirements,
                    'recent_chats': recent_chats
                },
                'export_time': datetime.now().isoformat()
            }
        elif export_type == 'tokens':
            # 获取Token使用数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            token_stats = db.session.query(
                func.sum(ChatHistory.tokens_used).label('total_tokens'),
                func.avg(ChatHistory.tokens_used).label('avg_tokens'),
                func.count(ChatHistory.id).label('message_count')
            ).filter(
                ChatHistory.created_time >= start_date,
                ChatHistory.tokens_used > 0
            ).first()

            data = {
                'export_type': 'tokens',
                'period_days': days,
                'format': format_type,
                'token_stats': {
                    'total_tokens': int(token_stats.total_tokens or 0),
                    'avg_tokens_per_message': round(float(token_stats.avg_tokens or 0), 2),
                    'total_messages': int(token_stats.message_count or 0)
                },
                'export_time': datetime.now().isoformat()
            }
        else:
            data = {
                'export_type': export_type,
                'message': f'{export_type} 导出功能暂未实现',
                'format': format_type,
                'period_days': days,
                'export_time': datetime.now().isoformat()
            }

        # 根据格式返回不同内容
        if format_type == 'excel':
            return _export_to_excel(data, export_type)
        elif format_type == 'csv':
            return _export_to_csv(data, export_type)
        else:  # json
            return jsonify({
                'success': True,
                'message': '统计数据导出成功',
                'data': data
            })

    except Exception as e:
        current_app.logger.error(f"统计数据导出失败: {e}")
        return jsonify({
            'success': False,
            'message': '统计数据导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


def _export_to_excel(data, export_type):
    """导出为Excel格式"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from flask import send_file
    import io

    # 创建工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "统计数据"

    # 设置样式
    title_font = Font(bold=True, size=16, color="FFFFFF")
    header_font = Font(bold=True, size=12)
    data_font = Font(size=11)

    title_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")

    center_alignment = Alignment(horizontal="center", vertical="center")
    left_alignment = Alignment(horizontal="left", vertical="center")

    # 边框样式
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 写入标题
    ws['A1'] = "TestPilot 统计数据导出"
    ws['A1'].font = title_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = center_alignment
    ws.merge_cells('A1:D1')

    ws['A2'] = f"导出时间: {data['export_time']}"
    ws['A2'].font = data_font
    ws['A2'].alignment = left_alignment

    ws['A3'] = f"导出类型: {data['export_type']}"
    ws['A3'].font = data_font
    ws['A3'].alignment = left_alignment

    ws['A4'] = f"统计周期: {data['period_days']} 天"
    ws['A4'].font = data_font
    ws['A4'].alignment = left_alignment

    # 根据导出类型写入具体数据
    if export_type == 'overview':
        # 数据概览
        ws['A6'] = "数据概览"
        ws['A6'].font = header_font
        ws['A6'].fill = header_fill
        ws['A6'].alignment = center_alignment
        ws.merge_cells('A6:D6')

        # 表头
        ws['A7'] = "指标名称"
        ws['B7'] = "数值"
        ws['C7'] = "单位"
        ws['D7'] = "说明"

        for cell in ['A7', 'B7', 'C7', 'D7']:
            ws[cell].font = header_font
            ws[cell].fill = header_fill
            ws[cell].alignment = center_alignment
            ws[cell].border = thin_border

        # 数据行
        data_rows = [
            ("测试用例总数", data['totals']['test_cases'], "个", "系统中所有测试用例数量"),
            ("需求总数", data['totals']['requirements'], "个", "系统中所有需求数量"),
            ("聊天会话总数", data['totals']['chat_sessions'], "个", "系统中所有聊天会话数量")
        ]

        for i, (name, value, unit, desc) in enumerate(data_rows, 8):
            ws[f'A{i}'] = name
            ws[f'B{i}'] = value
            ws[f'C{i}'] = unit
            ws[f'D{i}'] = desc

            for col in ['A', 'B', 'C', 'D']:
                ws[f'{col}{i}'].font = data_font
                ws[f'{col}{i}'].alignment = left_alignment
                ws[f'{col}{i}'].border = thin_border

    elif export_type == 'usage':
        # 使用统计
        ws['A6'] = "使用统计"
        ws['A6'].font = header_font
        ws['A6'].fill = header_fill
        ws['A6'].alignment = center_alignment
        ws.merge_cells('A6:D6')

        # 表头
        ws['A7'] = "指标名称"
        ws['B7'] = "数值"
        ws['C7'] = "单位"
        ws['D7'] = "说明"

        for cell in ['A7', 'B7', 'C7', 'D7']:
            ws[cell].font = header_font
            ws[cell].fill = header_fill
            ws[cell].alignment = center_alignment
            ws[cell].border = thin_border

        # 数据行
        data_rows = [
            ("近期测试用例", data['usage_stats']['recent_cases'], "个", f"最近{data['period_days']}天创建的测试用例"),
            ("近期需求", data['usage_stats']['recent_requirements'], "个", f"最近{data['period_days']}天创建的需求"),
            ("近期聊天", data['usage_stats']['recent_chats'], "条", f"最近{data['period_days']}天的聊天记录")
        ]

        for i, (name, value, unit, desc) in enumerate(data_rows, 8):
            ws[f'A{i}'] = name
            ws[f'B{i}'] = value
            ws[f'C{i}'] = unit
            ws[f'D{i}'] = desc

            for col in ['A', 'B', 'C', 'D']:
                ws[f'{col}{i}'].font = data_font
                ws[f'{col}{i}'].alignment = left_alignment
                ws[f'{col}{i}'].border = thin_border

    elif export_type == 'tokens':
        # Token使用统计
        ws['A6'] = "Token使用统计"
        ws['A6'].font = header_font
        ws['A6'].fill = header_fill
        ws['A6'].alignment = center_alignment
        ws.merge_cells('A6:D6')

        # 表头
        ws['A7'] = "指标名称"
        ws['B7'] = "数值"
        ws['C7'] = "单位"
        ws['D7'] = "说明"

        for cell in ['A7', 'B7', 'C7', 'D7']:
            ws[cell].font = header_font
            ws[cell].fill = header_fill
            ws[cell].alignment = center_alignment
            ws[cell].border = thin_border

        # 数据行
        data_rows = [
            ("总Token使用量", data['token_stats']['total_tokens'], "个", f"最近{data['period_days']}天使用的总Token数"),
            ("平均每条消息Token", data['token_stats']['avg_tokens_per_message'], "个", "每条消息平均使用的Token数"),
            ("总消息数", data['token_stats']['total_messages'], "条", f"最近{data['period_days']}天的总消息数")
        ]

        for i, (name, value, unit, desc) in enumerate(data_rows, 8):
            ws[f'A{i}'] = name
            ws[f'B{i}'] = value
            ws[f'C{i}'] = unit
            ws[f'D{i}'] = desc

            for col in ['A', 'B', 'C', 'D']:
                ws[f'{col}{i}'].font = data_font
                ws[f'{col}{i}'].alignment = left_alignment
                ws[f'{col}{i}'].border = thin_border

    # 设置列宽
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 30

    # 保存到BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # 返回Excel文件
    return send_file(
        output,
        as_attachment=True,
        download_name=f'export_{export_type}_{datetime.now().strftime("%Y-%m-%d")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'  # noqa: SPELLING - Excel MIME type (official Microsoft Office Open XML format)
    )


def _export_to_csv(data, export_type):
    """导出为CSV格式"""
    import csv
    from flask import Response
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # 写入标题
    writer.writerow(['TestPilot 统计数据导出'])
    writer.writerow([f'导出时间: {data["export_time"]}'])
    writer.writerow([f'导出类型: {data["export_type"]}'])
    writer.writerow([f'统计周期: {data["period_days"]} 天'])
    writer.writerow([])  # 空行

    # 根据导出类型写入数据
    if export_type == 'overview':
        writer.writerow(['数据概览'])
        writer.writerow(['指标名称', '数值', '单位', '说明'])
        writer.writerow(['测试用例总数', data['totals']['test_cases'], '个', '系统中所有测试用例数量'])
        writer.writerow(['需求总数', data['totals']['requirements'], '个', '系统中所有需求数量'])
        writer.writerow(['聊天会话总数', data['totals']['chat_sessions'], '个', '系统中所有聊天会话数量'])

    elif export_type == 'usage':
        writer.writerow(['使用统计'])
        writer.writerow(['指标名称', '数值', '单位', '说明'])
        writer.writerow(
            ['近期测试用例', data['usage_stats']['recent_cases'], '个', f'最近{data["period_days"]}天创建的测试用例'])
        writer.writerow(
            ['近期需求', data['usage_stats']['recent_requirements'], '个', f'最近{data["period_days"]}天创建的需求'])
        writer.writerow(
            ['近期聊天', data['usage_stats']['recent_chats'], '条', f'最近{data["period_days"]}天的聊天记录'])

    elif export_type == 'tokens':
        writer.writerow(['Token使用统计'])
        writer.writerow(['指标名称', '数值', '单位', '说明'])
        writer.writerow(
            ['总Token使用量', data['token_stats']['total_tokens'], '个', f'最近{data["period_days"]}天使用的总Token数'])
        writer.writerow(
            ['平均每条消息Token', data['token_stats']['avg_tokens_per_message'], '个', '每条消息平均使用的Token数'])
        writer.writerow(
            ['总消息数', data['token_stats']['total_messages'], '条', f'最近{data["period_days"]}天的总消息数'])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=export_{export_type}_{datetime.now().strftime("%Y-%m-%d")}.csv'}
    )


@stats_bp.route('/record', methods=['POST'])
def record_metric():
    """记录性能指标"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        metric_name = data.get('metric_name')
        metric_value = data.get('metric_value')

        if not metric_name or metric_value is None:
            raise BadRequest("指标名称和值不能为空")

        # 创建性能指标记录
        metric = PerformanceMetric(
            metric_name=metric_name,
            metric_value=float(metric_value),
            metric_unit=data.get('metric_unit'),
            category=data.get('category'),
            meta_data=data.get('metadata')
        )

        db.session.add(metric)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '性能指标记录成功',
            'metric_id': metric.id
        })

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"记录性能指标失败: {e}")
        return jsonify({
            'success': False,
            'message': '记录性能指标失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/health', methods=['GET'])
def get_system_health():
    """获取系统健康状态"""
    try:
        # 执行系统健康检查
        health_result = stats_service.get_system_health(db.session)

        # 如果健康检查本身失败，直接返回错误信息
        if not health_result.get('success', False):
            return jsonify({
                'success': False,
                'message': health_result.get('message', '获取系统健康状态失败'),
                'error': health_result.get('message', '未知错误')
            }), 500

        # 直接返回健康检查结果（已经包含success和health字段）
        return jsonify(health_result)

    except Exception as e:
        current_app.logger.error(f"获取系统健康状态失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取系统健康状态失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/network/info', methods=['GET'])
def get_network_info_api():
    """获取网络信息API"""
    try:
        network_info = get_network_info()
        return jsonify({
            'success': True,
            'network_info': network_info
        })
    except Exception as e:
        logger.error(f"获取网络信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取网络信息失败: {str(e)}'
        }), 500


@stats_bp.route('/recent-activities', methods=['GET'])
def get_recent_activities():
    """获取最近活动"""
    try:
        from models.models import TestCase, Requirement, ChatHistory, RagFileRecord
        from datetime import datetime, timedelta
        
        # 获取最近7天的活动
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        activities = []
        
        # 最近创建的测试用例
        recent_cases = TestCase.query.filter(
            TestCase.created_time >= start_date
        ).order_by(TestCase.created_time.desc()).limit(5).all()
        
        for case in recent_cases:
            activities.append({
                'type': 'case',
                'message': f'生成了测试用例: {case.title[:30]}...' if len(case.title) > 30 else f'生成了测试用例: {case.title}',
                'time': case.created_time,
                'icon': 'fas fa-flask',
                'color': 'text-primary'
            })
        
        # 最近创建的需求文档
        recent_requirements = Requirement.query.filter(
            Requirement.created_time >= start_date
        ).order_by(Requirement.created_time.desc()).limit(5).all()
        
        for req in recent_requirements:
            activities.append({
                'type': 'requirement',
                'message': f'分析了需求文档: {req.title[:30]}...' if len(req.title) > 30 else f'分析了需求文档: {req.title}',
                'time': req.created_time,
                'icon': 'fas fa-file-alt',
                'color': 'text-success'
            })
        
        # 最近的知识库文件上传
        recent_knowledge = RagFileRecord.query.filter(
            RagFileRecord.created_time >= start_date,
            RagFileRecord.status == 'active'
        ).order_by(RagFileRecord.created_time.desc()).limit(3).all()
        
        for file in recent_knowledge:
            activities.append({
                'type': 'knowledge',
                'message': f'上传了知识库文件: {file.file_name[:30]}...' if len(file.file_name) > 30 else f'上传了知识库文件: {file.file_name}',
                'time': file.created_time,
                'icon': 'fas fa-brain',
                'color': 'text-info'
            })
        
        # 最近的聊天会话
        recent_chats = ChatHistory.query.filter(
            ChatHistory.created_time >= start_date
        ).order_by(ChatHistory.created_time.desc()).limit(3).all()
        
        for chat in recent_chats:
            activities.append({
                'type': 'chat',
                'message': f'AI助手会话: {chat.content[:30]}...' if len(chat.content) > 30 else f'AI助手会话: {chat.content}',
                'time': chat.created_time,
                'icon': 'fas fa-comments',
                'color': 'text-warning'
            })
        
        # 按时间排序，取最近10条
        activities.sort(key=lambda x: x['time'], reverse=True)
        activities = activities[:10]
        
        return jsonify({
            'success': True,
            'activities': activities
        })
        
    except Exception as e:
        current_app.logger.error(f"获取最近活动失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取最近活动失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@stats_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """获取系统状态 - 完整的系统监控信息"""
    try:
        import psutil
        import time
        from datetime import datetime
        from models.models import RagFileRecord
        from utils.utils_ai_models.get_llm import get_llm
        
        # AI服务状态检测
        start_time = time.time()
        
        try:
            from config.settings import settings
            llm = get_llm(settings.DEFAULT_COMPANY)
            if llm:
                # 尝试获取模型名称
                if hasattr(llm, 'model_name'):
                    ai_model_name = llm.model_name
                elif hasattr(llm, 'model'):
                    ai_model_name = llm.model
                else:
                    # 根据DEFAULT_COMPANY获取默认模型名称（统一使用大写）
                    company_upper = settings.DEFAULT_COMPANY.upper() if settings.DEFAULT_COMPANY else 'OPENAI'
                    if company_upper == 'OPENAI':
                        ai_model_name = os.getenv('OPENAI_MODEL', 'gpt-5')
                    elif company_upper == 'DEEPSEEK':
                        ai_model_name = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
                    elif company_upper == 'OLLAMA':
                        ai_model_name = os.getenv('OLLAMA_MODEL', 'phi:2.7b')
                    elif company_upper == 'GEMINI':
                        ai_model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
                    elif company_upper == 'QWEN':
                        ai_model_name = os.getenv('QWEN_MODEL', 'qwen-flash')
                    else:
                        ai_model_name = '未知模型'
                
                # 检查LLM对象是否可用（不进行实际API调用）
                try:
                    # 只检查LLM对象的基本属性，不调用API
                    if hasattr(llm, 'invoke') and callable(getattr(llm, 'invoke')):
                        ai_service_status = "在线"
                        ai_response_time = 0  # 不进行实际测试，显示为0ms
                    else:
                        ai_service_status = "离线"
                        ai_response_time = 0
                except Exception as e:
                    ai_service_status = "离线"
                    ai_response_time = 0
                    current_app.logger.warning(f"AI服务检查失败: {e}")
            else:
                ai_service_status = "离线"
                ai_model_name = "服务不可用"
                ai_response_time = 0
        except (ImportError, ValueError, AttributeError):
            ai_service_status = "离线"
            ai_model_name = "配置错误"
            ai_response_time = int((time.time() - start_time) * 1000)
        except (ConnectionError, TimeoutError, OSError, RuntimeError):
            ai_service_status = "离线"
            ai_model_name = "连接失败"
            ai_response_time = int((time.time() - start_time) * 1000)
        
        # 知识库状态检测
        try:
            # 获取知识库文档数量
            knowledge_docs = RagFileRecord.query.filter(RagFileRecord.status == 'active').count()
            
            # 尝试连接向量数据库获取向量数量
            vector_db = getattr(current_app, 'vector_db', None)
            if vector_db:
                try:
                    # 优先尝试使用 count() 方法（SQLiteVectorStore 和 ThreadSafeVectorDB 都支持）
                    if hasattr(vector_db, 'count'):
                        try:
                            knowledge_vectors = vector_db.count()
                        except (AttributeError, Exception) as e:
                            # ChromaDB 不支持 count 方法，这是已知限制，使用 DEBUG 级别
                            current_app.logger.debug(f"向量数据库不支持 count 方法（ChromaDB 限制）: {e}")
                            # 降级到其他方法
                            knowledge_vectors = None
                    else:
                        knowledge_vectors = None
                    
                    # 如果 count() 不可用或失败，尝试 ChromaDB 路径
                    if knowledge_vectors is None:
                        # 如果是ThreadSafeVectorDB，获取底层对象（使用getattr避免直接访问protected成员）
                        actual_db = getattr(vector_db, '_vector_db', vector_db)
                        
                        # ChromaDB 路径：获取集合对象
                        collection = getattr(actual_db, '_collection', None) or getattr(actual_db, 'collection', None)
                        
                        if collection:
                            # 获取集合中的所有文档ID
                            result = collection.get()
                            knowledge_vectors = len(result.get('ids', []))
                        else:
                            # 如果无法访问集合，尝试使用 vector_db 的 get 方法
                            try:
                                all_data = vector_db.get()
                                if all_data and 'ids' in all_data:
                                    knowledge_vectors = len(all_data['ids'])
                                else:
                                    knowledge_vectors = 0
                            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
                                # 如果都失败，使用文档数量作为估算
                                current_app.logger.debug("向量数据库集合属性不可用，使用文档数量作为估算")
                                knowledge_vectors = knowledge_docs
                    
                    # 确保 knowledge_vectors 有值
                    if knowledge_vectors is None:
                        knowledge_vectors = knowledge_docs
                except (AttributeError, KeyError, TypeError) as e:
                    # 向量数据库结构问题，使用文档数量作为估算
                    current_app.logger.warning(f"向量数据库查询失败: {type(e).__name__}, 使用文档数量作为估算")
                    knowledge_vectors = knowledge_docs
                except (ConnectionError, OSError, RuntimeError, ValueError) as e:
                    # 其他向量数据库错误
                    current_app.logger.error(f"向量数据库连接失败: {type(e).__name__}")
                    knowledge_vectors = knowledge_docs
            else:
                knowledge_vectors = 0
                
            if knowledge_docs == 0:
                knowledge_status = "空"
            elif knowledge_docs > 0 and knowledge_vectors == 0:
                knowledge_status = "异常"
            else:
                knowledge_status = "正常"
        except (AttributeError, ImportError, OSError, RuntimeError, ValueError):
            # 数据库查询失败
            current_app.logger.error("知识库状态检测失败")
            knowledge_status = "异常"
            knowledge_docs = 0
            knowledge_vectors = 0
        
        # 系统性能监控
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_used_gb = round(memory.used / (1024**3), 2)
            memory_percent = memory.percent
            memory_total_gb = round(memory.total / (1024**3), 2)
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = round(disk.used / disk.total * 100, 1)
            
            # 判断系统性能状态
            if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                performance_status = "危险"
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 90:
                performance_status = "警告"
            else:
                performance_status = "良好"
        except (OSError, RuntimeError, AttributeError, ValueError, TypeError):
            # 系统调用失败或数据处理异常
            current_app.logger.error("系统性能监控失败")
            cpu_percent = 0
            memory_used_gb = 0
            memory_percent = 0
            memory_total_gb = 0
            disk_percent = 0
            performance_status = "检测失败"
        
        return jsonify({
            'success': True,
            'system': {
                'ai_service': {
                    'status': ai_service_status,
                    'model': ai_model_name,
                    'response_time': ai_response_time
                },
                'knowledge': {
                    'status': knowledge_status,
                    'docs': knowledge_docs,
                    'vectors': knowledge_vectors
                },
                'performance': {
                    'cpu': cpu_percent,
                    'memory': memory_used_gb,
                    'memory_percent': memory_percent,
                    'memory_total': memory_total_gb,
                    'disk': disk_percent,
                    'status': performance_status
                },
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except (ImportError, AttributeError, ModuleNotFoundError, NameError):
        # 模块导入或属性访问错误
        current_app.logger.error("系统状态检测模块错误")
        return jsonify({
            'success': False,
            'message': '系统状态检测模块错误',
            'system': {
                'ai_service': {'status': '检测失败', 'model': '未知', 'response_time': 0},
                'knowledge': {'status': '检测失败', 'docs': 0, 'vectors': 0},
                'performance': {'cpu': 0, 'memory': 0, 'disk': 0, 'status': '检测失败'}
            }
        }), 500
    except (OSError, RuntimeError, ValueError, TypeError, KeyError):
        # 其他运行时错误
        current_app.logger.error("获取系统状态失败")
        return jsonify({
            'success': False,
            'message': '获取系统状态失败',
            'system': {
                'ai_service': {'status': '检测失败', 'model': '未知', 'response_time': 0},
                'knowledge': {'status': '检测失败', 'docs': 0, 'vectors': 0},
                'performance': {'cpu': 0, 'memory': 0, 'disk': 0, 'status': '检测失败'}
            }
        }), 500