#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
配置中心数据模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from models.models import db

Base = declarative_base()


class ConfigItem(db.Model):
    """配置项模型"""
    __tablename__ = 'config_items'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # ai_model, case_generation, performance, knowledge, file_processing
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)  # 是否为敏感信息（如API密钥）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'value_type': self.value_type,
            'category': self.category,
            'description': self.description,
            'label_key': f'configCenter.itemLabel.{self.key}',
            'description_key': f'configCenter.itemDescription.{self.key}',
            'is_sensitive': self.is_sensitive,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ConfigAuditLog(db.Model):
    """配置审计日志模型"""
    __tablename__ = 'config_audit_logs'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), nullable=False, index=True)
    old_value = Column(Text)
    new_value = Column(Text)
    operation_type = Column(String(20), nullable=False)  # create, update, delete, import, export
    operator = Column(String(50), nullable=False)  # 操作者（可以是用户ID或系统）
    operator_ip = Column(String(45))  # 操作者IP
    change_reason = Column(Text)  # 变更原因
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'operation_type': self.operation_type,
            'operator': self.operator,
            'operator_ip': self.operator_ip,
            'change_reason': self.change_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ConfigValidationRule(db.Model):
    """配置验证规则模型"""
    __tablename__ = 'config_validation_rules'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), nullable=False, index=True)
    validation_type = Column(String(20), nullable=False)  # range, enum, regex, custom
    validation_config = Column(JSON)  # 验证配置（如范围、枚举值等）
    error_message = Column(Text)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'validation_type': self.validation_type,
            'validation_config': self.validation_config,
            'error_message': self.error_message,
            'is_required': self.is_required,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
