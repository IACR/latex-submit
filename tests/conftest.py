"""Shared configuration for tests."""
import json
from pathlib import Path
import pytest

from webapp import config
from webapp import create_app
from webapp import user_datastore

@pytest.fixture
def app():
    """Create the app for tests."""
    config_file = Path('tests/test_config.json')
    conf = config.Config.model_validate_json(config_file.read_text(encoding='UTF-8'))
    conf.TESTING = True
    conf.DEBUG = False
    conf.SQLALCHEMY_ENGINES = {'default': 'sqlite:///:memory:'}
    conf.WTF_CSRF_ENABLED = False
    conf.SECURITY_CONFIRMABLE = False
    conf.SECURITY_PASSWORD_HASH = 'plaintext'
    #conf.INIT_FILE = 'tests/test_init.json'
    app = create_app(conf)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

class AuthActions():
    def __init__(self, client):
        self.client = client

    def login(self, user):
        return self.client.post(
            '/sec/login',
            data={'email': user.email,
                  'password': user.password}
        )

    def logout(self):
        return self.client.get('/sec/logout')

@pytest.fixture
def auth(client):
    return AuthActions(client)

@pytest.fixture
def admin_user(app):
    with app.app_context():
        return user_datastore.find_user(email='testing@digicrime.com')

@pytest.fixture
def nobody_user(app):
    with app.app_context():
        return user_datastore.find_user(email='nobody@digicrime.com')


@pytest.fixture
def editor_user(app):
    with app.app_context():
        return user_datastore.find_user(email='editor@digicrime.com')

@pytest.fixture
def debug_data(app):
    path = Path(app.config['INIT_FILE'])
    yield json.loads(path.read_text(encoding='UTF-8'))
