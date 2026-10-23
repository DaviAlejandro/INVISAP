import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_permissions(monkeypatch):
    from controllers import UserController
    from models.model_seguridad import ModuloModel

    monkeypatch.setattr(ModuloModel, 'consultar_activos', lambda self: [])
    monkeypatch.setattr(UserController, 'verificar_permiso', lambda *args, **kwargs: True)
    monkeypatch.setattr(
        UserController,
        'verificar_permiso_accion',
        lambda *args, **kwargs: True
    )
