"""后台模型预热必须带应用上下文，否则配置中心密钥读不到。"""

import threading

from flask import Flask

from app import warm_model_status
from models.config_models import ConfigItem
from models.models import db


def test_warmup_thread_reads_config_center_key(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "warmup.db"}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        db.session.add(ConfigItem(
            key='DEEPSEEK_API_KEY',
            value='sk-warmup-test',
            value_type='string',
            category='ai_model',
            is_sensitive=True,
        ))
        db.session.commit()
        db.session.remove()

    seen = {}

    def fake_summary(company):
        from services.config_center_service import config_center_service

        seen['company'] = company
        seen['key'] = config_center_service.get_config_value('DEEPSEEK_API_KEY')
        return {'company': company, 'is_available': True, 'message': 'ok'}

    monkeypatch.setattr(
        'utils.utils_core.remote_model_checker.model_checker.get_model_status_summary',
        fake_summary,
    )

    thread = threading.Thread(target=warm_model_status, args=(app, 'DEEPSEEK'))
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert seen['company'] == 'DEEPSEEK'
    assert seen['key'] == 'sk-warmup-test'
    assert app.config['MODEL_STATUS']['is_available'] is True
