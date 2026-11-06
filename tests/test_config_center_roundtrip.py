#!/usr/bin/python
# -*- coding: utf-8 -*-
"""配置中心：JSON 不重复编码、已有项类型与分类不被请求覆盖、导出再导入值不变、导入只认已有键。"""

import json

import pytest
from flask import Flask

from models.config_models import ConfigAuditLog, ConfigItem
from models.models import db
from services.config_center_service import ConfigCenterService


@pytest.fixture()
def service(tmp_path):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "cfg.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.add_all([
            ConfigItem(key='CONTENT_DEDUP_WEIGHTS', value='{"title": 0.4, "steps": 0.6}', value_type='json',
                       category='case_generation'),
            ConfigItem(key='MAX_CASE_NUM', value='20', value_type='int', category='case_generation'),
            ConfigItem(key='ENABLE_STREAMING', value='true', value_type='bool', category='performance'),
        ])
        db.session.commit()
        yield ConfigCenterService()


def test_json_text_is_not_double_encoded(service):
    ok, _ = service.set_config_value('CONTENT_DEDUP_WEIGHTS', '{"title": 0.5, "steps": 0.5}', 'json', 'case_generation')
    assert ok
    stored = ConfigItem.query.filter_by(key='CONTENT_DEDUP_WEIGHTS').first().value
    assert json.loads(stored) == {'title': 0.5, 'steps': 0.5}
    assert service.get_config_value('CONTENT_DEDUP_WEIGHTS') == {'title': 0.5, 'steps': 0.5}


def test_legacy_double_encoded_json_still_reads_as_dict(service):
    item = ConfigItem.query.filter_by(key='CONTENT_DEDUP_WEIGHTS').first()
    item.value = json.dumps('{"title": 1}')
    db.session.commit()
    assert service.get_config_value('CONTENT_DEDUP_WEIGHTS') == {'title': 1}


def test_existing_item_keeps_type_and_category(service):
    ok, _ = service.set_config_value('MAX_CASE_NUM', '30', 'string', 'general')
    assert ok
    item = ConfigItem.query.filter_by(key='MAX_CASE_NUM').first()
    assert (item.value_type, item.category, item.value) == ('int', 'case_generation', '30')
    ok, _ = service.set_config_value('MAX_CASE_NUM', 'abc', 'string', 'general')
    assert not ok


def test_export_then_import_keeps_values(service):
    ok, content, _ = service.export_configs('json', operator='alice')
    assert ok
    before = {row.key: row.value for row in ConfigItem.query.all()}
    ok, _, count = service.import_configs(content, 'json', operator='alice')
    assert ok and count == 3
    after = {row.key: row.value for row in ConfigItem.query.all()}
    assert json.loads(after['CONTENT_DEDUP_WEIGHTS']) == json.loads(before['CONTENT_DEDUP_WEIGHTS'])
    assert after['MAX_CASE_NUM'] == before['MAX_CASE_NUM']
    assert after['ENABLE_STREAMING'] == 'true'
    operators = {log.operator for log in ConfigAuditLog.query.all()}
    assert operators == {'alice'}


def test_import_skips_unknown_keys(service):
    content = json.dumps({'configs': [
        {'key': 'EVIL_NEW_KEY', 'value': 'x', 'value_type': 'string', 'category': 'ai_model'},
        {'key': 'MAX_CASE_NUM', 'value': '12', 'value_type': 'string', 'category': 'ai_model'},
    ]})
    ok, _, count = service.import_configs(content, 'json')
    assert ok and count == 1
    assert ConfigItem.query.filter_by(key='EVIL_NEW_KEY').first() is None
    item = ConfigItem.query.filter_by(key='MAX_CASE_NUM').first()
    assert (item.value, item.category, item.value_type) == ('12', 'case_generation', 'int')
