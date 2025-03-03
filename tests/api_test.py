import os
import sys
from fastapi.testclient import TestClient

sys.path.append(os.getcwd())  # prevents a nasty ModuleNotFoundError for imports below
from api import app, handler


client = TestClient(app)


def test_health_check():
    response = client.get('/docs')
    assert response.status_code == 200


def test_inconveniences():
    response = client.get('/inconveniences?name=test-entity')
    assert response.status_code == 200


def test_inconveniences_for_everyone():
    response = client.get('/inconveniences_for_everyone')
    assert response.status_code == 200


def test_current_inconveniences_for_everyone():
    response = client.get('/current_inconveniences_for_everyone?request_uuid=test_uuid')
    assert response.status_code == 200


def test_inconveniences_of_real_entity():
    response = client.get('/inconveniences?name=ИКБО-30-24')
    assert response.json() == handler.get_inconveniences('ИКБО-30-24')

    response = client.get('/inconveniences?name=Сафронов А. А.')
    assert response.json() == handler.get_inconveniences('Сафронов А. А.')

    response = client.get('/inconveniences?name=ИКБО-51-24')
    assert response.json() == handler.get_inconveniences('ИКБО-51-24')

    response = client.get('/inconveniences?name=Акатьев Я. А.')
    assert response.json() == handler.get_inconveniences('Акатьев Я. А.')
