#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
配置中心服务
"""
import json
import re
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from flask import has_request_context, request
from models.models import db
from models.config_models import ConfigItem, ConfigAuditLog, ConfigValidationRule
from utils.utils_core.logger import get_logger
from utils.utils_core.common_utils import get_local_ip

logger = get_logger(__name__)

SENSITIVE_VALUE_MASK = "********"
_SENSITIVE_KEY_PATTERN = re.compile(r"(API_KEY|SECRET|PASSWORD|ACCESS_KEY|CREDENTIAL)$", re.IGNORECASE)


def is_sensitive_config_key(key: str, flagged: bool = False) -> bool:
    """密钥类配置对外不能返回原文。"""
    if flagged:
        return True
    return bool(_SENSITIVE_KEY_PATTERN.search(key or ""))


def masked_secret_text(value: Any) -> str:
    """已配置的密钥对外只显示固定掩码。"""
    text = "" if value is None else str(value)
    return SENSITIVE_VALUE_MASK if text.strip() else ""


class ConfigCenterService:
    """配置中心服务类"""
    
    def __init__(self):
        self.session = db.session
    
    def get_config_value(self, key: str, default_value: Any = None) -> Any:
        """获取配置值"""
        try:
            config_item = self.session.query(ConfigItem).filter_by(key=key).first()
            if not config_item:
                return default_value
            
            # 根据类型转换值
            value = self._convert_value(config_item.value, config_item.value_type)
            
            # 特殊处理：DEFAULT_COMPANY 统一转换为大写
            if key == 'DEFAULT_COMPANY' and isinstance(value, str):
                value = value.upper()
                # 如果数据库中的值不是大写，更新数据库
                if config_item.value != value:
                    config_item.value = value
                    self.session.commit()
                    logger.info(f"已将 DEFAULT_COMPANY 从 '{config_item.value}' 更新为 '{value}'")
            
            return value
        except Exception as e:
            logger.error(f"获取配置值失败: {key}, 错误: {e}")
            return default_value
    
    def set_config_value(self, key: str, value: Any, value_type: str, 
                        category: str, description: str = "", 
                        is_sensitive: bool = False, operator: str = "system") -> Tuple[bool, str]:
        """设置配置值。已存在的配置项沿用库里的类型和分类，请求里的 value_type / category 只用于新建。"""
        try:
            # 特殊处理：DEFAULT_COMPANY 统一转换为大写
            if key == 'DEFAULT_COMPANY' and isinstance(value, str):
                value = value.upper()
                logger.info(f"DEFAULT_COMPANY 值已自动转换为大写: {value}")

            old_config = self.session.query(ConfigItem).filter_by(key=key).first()
            old_value = old_config.value if old_config else None
            if old_config:
                value_type = old_config.value_type or value_type
                category = old_config.category or category
            sensitive = is_sensitive_config_key(
                key,
                bool(is_sensitive) or bool(old_config and old_config.is_sensitive),
            )
            if sensitive:
                is_sensitive = True
                incoming = "" if value is None else str(value).strip()
                if incoming == SENSITIVE_VALUE_MASK:
                    value = old_value if old_value and str(old_value).strip() else ""

            # 验证配置
            validation_result = self._validate_config(key, value, value_type)
            if not validation_result[0]:
                return False, validation_result[1]

            # 转换值为字符串存储
            str_value = self._convert_to_string(value, value_type)
            
            # 更新或创建配置
            if old_config:
                old_config.value = str_value
                old_config.value_type = value_type
                old_config.category = category
                if description is not None:
                    old_config.description = description
                old_config.is_sensitive = is_sensitive
                old_config.updated_at = datetime.now(timezone.utc)
                operation_type = "update"
            else:
                new_config = ConfigItem(
                    key=key,
                    value=str_value,
                    value_type=value_type,
                    category=category,
                    description=description,
                    is_sensitive=is_sensitive
                )
                self.session.add(new_config)
                operation_type = "create"
            
            # 记录审计日志
            self._log_config_change(
                key=key,
                old_value=old_value or "",
                new_value=str_value,
                operation_type=operation_type,
                operator=operator,
                sensitive=sensitive,
            )
            
            self.session.commit()
            return True, "配置更新成功"
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"设置配置值失败: {key}, 错误: {e}")
            return False, "设置配置值失败"
    
    def get_configs_by_category(self, category: str) -> List[Dict]:
        """根据分类获取配置"""
        try:
            configs = self.session.query(ConfigItem).filter_by(category=category).all()
            return [self._public_config_dict(config) for config in configs]
        except Exception as e:
            logger.error(f"获取分类配置失败: {category}, 错误: {e}")
            return []
    
    def get_all_configs(self) -> List[Dict]:
        """获取所有配置"""
        try:
            configs = self.session.query(ConfigItem).all()
            return [self._public_config_dict(config) for config in configs]
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return []
    
    def delete_config(self, key: str, operator: str = "system") -> Tuple[bool, str]:
        """删除配置"""
        try:
            config = self.session.query(ConfigItem).filter_by(key=key).first()
            if not config:
                return False, "配置不存在"
            
            # 记录审计日志
            self._log_config_change(
                key=key,
                old_value=config.value,
                new_value="",
                operation_type="delete",
                operator=operator,
                sensitive=is_sensitive_config_key(key, bool(config.is_sensitive)),
            )
            
            self.session.delete(config)
            self.session.commit()
            logger.info(f"配置删除成功: {key}")
            return True, "配置删除成功"
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"删除配置失败: {key}, 错误: {e}")
            return False, "删除配置失败"
    
    def export_configs(self, format_type: str = "json", operator: str = "system") -> Tuple[bool, str, str]:
        """导出配置"""
        try:
            configs = self.get_all_configs()
            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "configs": configs
            }
            
            if format_type == "json":
                content = json.dumps(export_data, ensure_ascii=False, indent=2)
                filename = f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            elif format_type == "yaml":
                content = yaml.dump(export_data, default_flow_style=False, allow_unicode=True)
                filename = f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            else:
                return False, "不支持的导出格式", ""
            
            # 记录审计日志
            self._log_config_change(
                key="export",
                old_value="",
                new_value=f"导出{len(configs)}个配置",
                operation_type="export",
                operator=operator
            )
            self.session.commit()
            
            return True, content, filename
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False, "导出配置失败", ""
    
    def import_configs(self, content: str, format_type: str = "json", 
                      operator: str = "system") -> Tuple[bool, str, int]:
        """导入配置"""
        try:
            # 解析导入数据
            if format_type == "json":
                import_data = json.loads(content)
            elif format_type == "yaml":
                import_data = yaml.safe_load(content)
            else:
                return False, "不支持的导入格式", 0
            
            if not isinstance(import_data, dict) or not isinstance(import_data.get("configs"), list):
                return False, "导入文件格式错误", 0

            # 只更新系统里已有的配置项，导入文件不能新增配置或改动类型、分类
            known_keys = {row[0] for row in self.session.query(ConfigItem.key).all()}
            imported_count = 0
            for config_data in import_data["configs"]:
                try:
                    if not isinstance(config_data, dict) or "key" not in config_data or "value" not in config_data:
                        continue
                    if config_data["key"] not in known_keys:
                        logger.warning(f"导入时跳过未知配置项: {config_data['key']}")
                        continue

                    success, message = self.set_config_value(
                        key=config_data["key"],
                        value=config_data["value"],
                        value_type=config_data.get("value_type") or "string",
                        category=config_data.get("category") or "general",
                        description=config_data.get("description"),
                        is_sensitive=config_data.get("is_sensitive", False),
                        operator=operator
                    )
                    
                    if success:
                        imported_count += 1
                        
                except Exception as e:
                    logger.warning(f"导入配置项失败: {config_data.get('key', 'unknown')}, 错误: {e}")
                    continue
            
            # 记录审计日志
            self._log_config_change(
                key="import",
                old_value="",
                new_value=f"导入{imported_count}个配置",
                operation_type="import",
                operator=operator
            )
            self.session.commit()
            
            return True, f"成功导入{imported_count}个配置", imported_count
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False, "导入配置失败", 0
    
    def get_audit_logs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取审计日志"""
        try:
            logs = self.session.query(ConfigAuditLog).order_by(
                ConfigAuditLog.created_at.desc()
            ).offset(offset).limit(limit).all()
            sensitive_keys = {
                item.key
                for item in self.session.query(ConfigItem).filter(ConfigItem.is_sensitive.is_(True)).all()
            }
            return [self._public_audit_dict(log, sensitive_keys) for log in logs]
        except Exception as e:
            logger.error(f"获取审计日志失败: {e}")
            return []
    
    def validate_config_value(self, key: str, value: Any) -> Tuple[bool, str]:
        """按配置项类型和校验规则检查单个值。"""
        item = self.session.query(ConfigItem).filter_by(key=key).first()
        value_type = item.value_type if item and item.value_type else 'string'
        if self._is_unchanged_secret(key, value, item):
            value = item.value if item else ""
        return self._validate_config(key, value, value_type)

    def _validate_config(self, key: str, value: Any, value_type: str) -> Tuple[bool, str]:
        """验证配置"""
        try:
            # 基本类型验证
            if not self._validate_basic_type(value, value_type):
                return False, f"配置值类型不匹配，期望: {value_type}"

            # 表单提交的数字是字符串，按声明类型转换后再比较范围和枚举
            value = self._convert_value(self._convert_to_string(value, value_type), value_type)

            # 获取验证规则
            rules = self.session.query(ConfigValidationRule).filter_by(config_key=key).all()
            
            for rule in rules:
                if rule.validation_type == "range":
                    if not self._validate_range(value, rule.validation_config):
                        return False, rule.error_message or f"配置值超出范围"
                elif rule.validation_type == "enum":
                    if not self._validate_enum(value, rule.validation_config):
                        return False, rule.error_message or f"配置值不在允许的枚举中"
                elif rule.validation_type == "regex":
                    if not self._validate_regex(value, rule.validation_config):
                        return False, rule.error_message or f"配置值格式不正确"
            
            return True, "验证通过"
            
        except Exception as e:
            logger.error(f"验证配置失败: {key}, 错误: {e}")
            return False, "验证配置失败"
    
    @staticmethod
    def _validate_basic_type(value: Any, value_type: str) -> bool:
        """验证基本类型"""
        try:
            if value_type == "int":
                int(value)
                return True
            elif value_type == "float":
                float(value)
                return True
            elif value_type == "bool":
                return isinstance(value, bool) or str(value).lower() in ("true", "false", "1", "0", "yes", "no", "on", "off")
            elif value_type == "json":
                if isinstance(value, (dict, list)):
                    return True
                else:
                    json.loads(str(value))
                    return True
            else:  # string
                return True
        except (ValueError, TypeError, json.JSONDecodeError):
            return False
    
    @staticmethod
    def _validate_range(value: Any, config: Dict) -> bool:
        """验证范围"""
        try:
            if "min" in config and value < config["min"]:
                return False
            if "max" in config and value > config["max"]:
                return False
            return True
        except (TypeError, ValueError, KeyError):
            return False
    
    @staticmethod
    def _validate_enum(value: Any, config: Dict) -> bool:
        """验证枚举"""
        try:
            allowed_values = config.get("values", [])
            return value in allowed_values
        except (TypeError, KeyError):
            return False
    
    @staticmethod
    def _validate_regex(value: Any, config: Dict) -> bool:
        """验证正则表达式"""
        try:
            pattern = config.get("pattern", "")
            if not pattern:
                return True  # 如果没有模式，认为验证通过
            return bool(re.match(pattern, str(value)))
        except (TypeError, AttributeError, ValueError, re.error):
            return False
    
    @staticmethod
    def _convert_value(str_value: str, value_type: str) -> Any:
        """转换配置值"""
        try:
            if value_type == "int":
                return int(str_value)
            elif value_type == "float":
                return float(str_value)
            elif value_type == "bool":
                return str_value.lower() in ("true", "1", "yes", "on")
            elif value_type == "json":
                parsed = json.loads(str_value)
                # 兼容旧数据：之前保存时会把 JSON 字符串再编码一层
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed)
                    except (ValueError, TypeError):
                        pass
                return parsed
            else:
                return str_value
        except (ValueError, TypeError, json.JSONDecodeError):
            return str_value
    
    @staticmethod
    def _convert_to_string(value: Any, value_type: str) -> str:
        """转换值为字符串"""
        try:
            if value_type == "json":
                # 表单和导出文件里的 JSON 已经是文本，先解析再序列化，避免存成带引号的字符串
                if isinstance(value, str):
                    value = json.loads(value)
                return json.dumps(value, ensure_ascii=False)
            if value_type == "bool":
                return 'true' if str(value).strip().lower() in ("true", "1", "yes", "on") else 'false'
            return str(value)
        except (TypeError, ValueError):
            return str(value)
    
    @staticmethod
    def _public_config_dict(config: ConfigItem) -> Dict:
        """列表、单条读取和导出使用的视图，密钥只保留是否已配置。"""
        data = config.to_dict()
        sensitive = is_sensitive_config_key(config.key, bool(config.is_sensitive))
        raw_value = (config.value or "").strip()
        configured = bool(raw_value)
        if sensitive:
            from utils.utils_core.api_error_handler import is_placeholder_secret
            configured = configured and not is_placeholder_secret(raw_value)
        data["configured"] = configured
        if sensitive:
            data["is_sensitive"] = True
            data["value"] = SENSITIVE_VALUE_MASK if configured else ""
        return data

    def get_public_config_item(self, key: str) -> Dict:
        """读取单个配置的对外视图。"""
        item = self.session.query(ConfigItem).filter_by(key=key).first()
        if not item:
            return {
                "key": key,
                "value": None,
                "configured": False,
                "is_sensitive": is_sensitive_config_key(key),
            }
        return self._public_config_dict(item)

    @staticmethod
    def _is_unchanged_secret(key: str, value: Any, item: ConfigItem = None) -> bool:
        flagged = bool(item and item.is_sensitive)
        if not is_sensitive_config_key(key, flagged):
            return False
        incoming = "" if value is None else str(value).strip()
        return incoming == SENSITIVE_VALUE_MASK

    @staticmethod
    def _public_audit_dict(log: ConfigAuditLog, sensitive_keys: set) -> Dict:
        data = log.to_dict()
        if is_sensitive_config_key(log.config_key) or log.config_key in sensitive_keys:
            data["old_value"] = masked_secret_text(data.get("old_value"))
            data["new_value"] = masked_secret_text(data.get("new_value"))
        return data

    def _log_config_change(self, key: str, old_value: str, new_value: str,
                          operation_type: str, operator: str, sensitive: bool = False):
        """记录配置变更日志"""
        try:
            if sensitive or is_sensitive_config_key(key):
                old_value = masked_secret_text(old_value)
                new_value = masked_secret_text(new_value)
            change_reason = ""
            operator_ip = get_local_ip()
            if has_request_context():
                from services.auth_service import client_ip

                change_reason = request.headers.get('X-Change-Reason', '')
                operator_ip = client_ip(request)

            audit_log = ConfigAuditLog(
                config_key=key,
                old_value=old_value,
                new_value=new_value,
                operation_type=operation_type,
                operator=operator,
                operator_ip=operator_ip,
                change_reason=change_reason
            )
            self.session.add(audit_log)
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")


# 全局配置中心服务实例
config_center_service = ConfigCenterService()
