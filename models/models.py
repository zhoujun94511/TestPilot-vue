#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import sys
from datetime import datetime, timezone
from typing import List, Literal, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from config.settings import settings
from pydantic import BaseModel, Field
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean

# 初始化SQLAlchemy
db = SQLAlchemy()
Base = declarative_base()


class RagFileRecord(db.Model):
    """RAG知识库文件记录"""
    __tablename__ = 'rag_file_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False, comment='文件名')
    file_path = Column(String(500), nullable=True, comment='文件路径')
    file_size = Column(Integer, nullable=True, comment='文件大小(bytes)')
    file_type = Column(String(50), nullable=True, comment='文件类型')
    file_hash = Column(String(64), nullable=True, index=True, comment='文件哈希值(MD5/SHA256)用于去重')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    ids = Column(Text, nullable=True, comment='向量数据库中的文档ID列表')
    status = Column(String(20), default='active', comment='状态: active, deleted')
    description = Column(Text, nullable=True, comment='文件描述')
    category = Column(String(50), default='other', comment='文件分类: requirements, test_cases, business_rules, best_practices, other')

    def __repr__(self):
        return f'<RagFileRecord {self.file_name}>'

    def to_dict(self):
        """转换为字典格式"""
        # SQLite存储的datetime没有时区信息，需要手动添加UTC时区
        created_time_iso = None
        if self.created_time:
            created_time_iso = self.created_time.replace(tzinfo=timezone.utc).isoformat()
        
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'created_time': created_time_iso,
            'ids': self.ids,
            'status': self.status,
            'description': self.description,
            'category': self.category or 'other'
        }


class TestCase(db.Model):

    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(200), unique=True, nullable=False, comment='用例ID（内部ID，带时间戳）')
    display_id = Column(String(100), nullable=True, comment='显示ID（简洁格式）')
    title = Column(String(500), nullable=False, comment='用例标题')
    description = Column(Text, nullable=True, comment='用例描述')
    precondition = Column(Text, nullable=True, comment='前置条件')
    steps = Column(Text, nullable=False, comment='测试步骤(JSON格式)')
    expected_result = Column(Text, nullable=True, comment='预期结果')
    priority = Column(String(20), default='medium', comment='优先级: high, medium, low')
    category = Column(String(100), nullable=True, comment='用例分类')
    tags = Column(String(500), nullable=True, comment='标签(逗号分隔)')
    status = Column(String(20), default='draft', comment='状态: draft, active, deprecated')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    updated_time = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), comment='更新时间')
    created_by = Column(String(100), default='system', comment='创建者')
    requirement_id = Column(String(100), nullable=True, comment='关联需求ID')
    module = Column(String(100), nullable=True, comment='功能模块')
    test_method = Column(String(100), nullable=True, comment='测试方法')

    def to_dict(self):
        """转换为字典格式"""

        def safe_json_loads(value):
            try:
                return json.loads(value) if value else []
            except (json.JSONDecodeError, TypeError, AttributeError):
                return []

        def safe_split(value):
            try:
                return value.split(',') if value else []
            except (AttributeError, TypeError):
                return []

        # SQLite存储的datetime没有时区信息，需要手动添加UTC时区
        created_time_iso = None
        updated_time_iso = None
        if self.created_time:
            created_time_iso = self.created_time.replace(tzinfo=timezone.utc).isoformat()
        if self.updated_time:
            updated_time_iso = self.updated_time.replace(tzinfo=timezone.utc).isoformat()
        
        return {
            'case_id': self.case_id,
            'display_id': self.display_id,
            'title': self.title,
            'description': self.description,
            'precondition': self.precondition,
            'steps': safe_json_loads(self.steps),
            'expected_result': safe_json_loads(self.expected_result),
            'priority': self.priority,
            'category': self.category,
            'tags': safe_split(self.tags),
            'status': self.status,
            'created_time': created_time_iso,
            'updated_time': updated_time_iso,
            'created_by': self.created_by,
            'requirement_id': self.requirement_id,
            'module': self.module,
            'test_method': self.test_method
        }


class FunctionCase(BaseModel):
    module: str = Field(..., description="功能模块")
    case_id: str = Field(..., description="用例编号")
    title: str = Field(..., description="测试用例标题")
    # 用 Literal 来约束 P0~P4
    priority: Literal["P0", "P1", "P2", "P3", "P4"] = Field(..., description="优先级")
    preconditions: str = Field(..., description="前置条件")
    steps: List[str] = Field(..., description="测试步骤")
    expected: List[str] = Field(..., description="预期结果")
    # 新增字段
    test_type: Optional[str] = Field(None, description="测试类型")
    test_method: Optional[str] = Field(None, description="测试方法")
    tags: Optional[List[str]] = Field(default=[], description="标签列表")

class AgentFunctionCase(BaseModel):
    module: str = Field(..., description="功能模块")
    case_id: str = Field(..., description="用例编号")
    title: str = Field(..., description="测试用例标题")
    priority: Literal["P0", "P1", "P2", "P3", "P4"] = Field(..., description="优先级")
    preconditions: str = Field(..., description="前置条件")
    steps: str = Field(..., description="测试步骤")
    expected: str = Field(..., description="预期结果")
    # 新增字段
    test_type: Optional[str] = Field(None, description="测试类型")
    test_method: Optional[str] = Field(None, description="测试方法")
    tags: Optional[List[str]] = Field(default=[], description="标签列表")

class AgentFunctionCaseList(BaseModel):
    cases: List[AgentFunctionCase] = Field(..., description="AI 生成的测试用例列表")

class FunctionCaseList(BaseModel):
    cases: List[FunctionCase] = Field(..., description="测试用例列表")

class RequirementAnalysis(BaseModel):
    """需求分析Pydantic模型"""
    title: str = Field(..., description="需求标题")
    content: str = Field(..., description="需求内容")
    type: Literal["functional", "non-functional", "business", "technical"] = Field(..., description="需求类型")
    priority: Literal["high", "medium", "low"] = Field(..., description="优先级")

class RequirementAnalysisList(BaseModel):
    """需求分析列表Pydantic模型"""
    requirements: List[RequirementAnalysis] = Field(..., description="需求列表")

class Requirement(db.Model):
    """需求表"""
    __tablename__ = 'requirements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    req_id = Column(String(100), unique=True, nullable=False, comment='需求ID')
    title = Column(String(500), nullable=False, comment='需求标题')
    content = Column(Text, nullable=False, comment='需求内容')
    type = Column(String(50), nullable=True, comment='需求类型')
    priority = Column(String(20), default='medium', comment='优先级')
    status = Column(String(20), default='active', comment='状态')
    source_file = Column(String(500), nullable=True, comment='来源文件')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    updated_time = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), comment='更新时间')

    def __repr__(self):
        return f'<Requirement {self.req_id}: {self.title}>'

    def to_dict(self):
        """转换为字典格式"""
        # SQLite存储的datetime没有时区信息，需要手动添加UTC时区
        created_time_iso = None
        updated_time_iso = None
        if self.created_time:
            created_time_iso = self.created_time.replace(tzinfo=timezone.utc).isoformat()
        if self.updated_time:
            updated_time_iso = self.updated_time.replace(tzinfo=timezone.utc).isoformat()
        
        return {
            'req_id': self.req_id,
            'title': self.title,
            'content': self.content,
            'type': self.type,
            'priority': self.priority,
            'status': self.status,
            'source_file': self.source_file,
            'created_time': created_time_iso,
            'updated_time': updated_time_iso
        }


class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, unique=True, comment='会话ID')
    title = Column(String(200), nullable=False, comment='会话标题')
    user_id = Column(String(100), nullable=True, comment='用户ID')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    updated_time = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), comment='更新时间')
    is_deleted = Column(Boolean, default=False, comment='是否已删除')

    def __repr__(self):
        return f'<ChatSession {self.session_id}:{self.title}>'

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, comment='会话ID')
    user_id = Column(String(100), nullable=True, comment='用户ID')
    role = Column(String(50), nullable=False, comment='消息角色: system, user, assistant')
    content = Column(Text, nullable=False, comment='消息内容')
    message_type = Column(String(50), default='chat', comment='消息类型')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    tokens_used = Column(Integer, default=0, comment='使用的token数量')
    model_name = Column(String(100), nullable=True, comment='使用的模型名称')

    def __repr__(self):
        return f'<ChatHistory {self.session_id}:{self.role}>'

    def to_dict(self):
        # 返回ISO格式的UTC时间字符串，让前端统一处理格式化
        # 重要：SQLite存储的datetime没有时区信息，需要手动添加UTC时区并转为ISO格式
        created_time_iso = None
        if self.created_time:
            # 为datetime对象添加UTC时区信息，然后转为ISO格式（会自动添加+00:00后缀）
            created_time_iso = self.created_time.replace(tzinfo=timezone.utc).isoformat()
        
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'message_type': self.message_type,
            'created_time': created_time_iso,
            'tokens_used': self.tokens_used,
            'model_name': self.model_name
        }


class ToolExecutionLog(db.Model):
    """实验动作执行审计日志（可拆卸模块使用）"""
    __tablename__ = 'tool_execution_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), nullable=False, unique=True, index=True, comment='执行ID')
    session_id = Column(String(100), nullable=True, comment='会话ID')
    user_id = Column(String(100), nullable=True, comment='用户ID')
    query_text = Column(Text, nullable=False, comment='用户原始请求')
    intent = Column(String(100), nullable=True, comment='识别意图')
    tool_name = Column(String(100), nullable=True, comment='工具名称')
    risk_level = Column(String(20), nullable=True, comment='风险等级')
    status = Column(String(32), nullable=False, default='done', comment='执行状态')
    success = Column(Boolean, nullable=False, default=True, comment='是否成功')
    tool_args = Column(Text, nullable=True, comment='执行参数(JSON)')
    tool_output = Column(Text, nullable=True, comment='执行结果(JSON)')
    error_message = Column(Text, nullable=True, comment='错误信息')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')

    def to_dict(self):
        created_time_iso = None
        if self.created_time:
            created_time_iso = self.created_time.replace(tzinfo=timezone.utc).isoformat()

        def _safe_json_loads(raw):
            try:
                return json.loads(raw) if raw else None
            except (TypeError, json.JSONDecodeError, ValueError):
                return raw

        return {
            'execution_id': self.execution_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'query_text': self.query_text,
            'intent': self.intent,
            'tool_name': self.tool_name,
            'risk_level': self.risk_level,
            'status': self.status,
            'success': self.success,
            'tool_args': _safe_json_loads(self.tool_args),
            'tool_output': _safe_json_loads(self.tool_output),
            'error_message': self.error_message,
            'created_time': created_time_iso
        }

class SystemLog(db.Model):
    """系统日志表"""
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, comment='日志级别')
    message = Column(Text, nullable=False, comment='日志消息')
    module = Column(String(100), nullable=True, comment='模块名称')
    function = Column(String(100), nullable=True, comment='函数名称')
    line_number = Column(Integer, nullable=True, comment='行号')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    extra_data = Column(Text, nullable=True, comment='额外数据(JSON格式)')

    def __repr__(self):
        return f'<SystemLog {self.level}: {self.message[:50]}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'function': self.function,
            'line_number': self.line_number,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'extra_data': self.extra_data
        }


class PerformanceMetric(db.Model):
    """性能指标表"""
    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False, comment='指标名称')
    metric_value = Column(Float, nullable=False, comment='指标值')
    metric_unit = Column(String(20), nullable=True, comment='单位')
    category = Column(String(50), nullable=True, comment='分类')
    # 添加新字段
    status_code = Column(Integer, nullable=True, comment='HTTP状态码')
    response_time = Column(Float, nullable=True, comment='响应时间(ms)')
    memory_usage = Column(Float, nullable=True, comment='内存使用率(%)')
    cpu_usage = Column(Float, nullable=True, comment='CPU使用率(%)')
    created_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    meta_data = Column(Text, nullable=True, comment='元数据(JSON格式)')

    def __repr__(self):
        return f'<PerformanceMetric {self.metric_name}: {self.metric_value}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'category': self.category,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'metadata': self.meta_data
        }


def get_db_session(database_url: Optional[str] = None):
    """获取数据库会话"""
    if database_url is None:
        database_url = settings.SQLALCHEMY_DATABASE_URI

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # 修复变量名：SessionLocal -> session_local
    return session_local()


def init_database(app):
    """初始化数据库"""
    with app.app_context():
        # 导入配置中心模型以确保表被创建
        # 必须显式导入，否则 SQLAlchemy 不会识别这些模型
        try:
            from models.config_models import ConfigItem, ConfigAuditLog, ConfigValidationRule
        except ImportError as import_error:
            # 如果导入失败，记录警告但不阻止启动
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"无法导入配置中心模型: {import_error}")
        
        # 创建所有表（包括配置中心相关表）
        db.create_all()
        print("数据库表创建成功！")