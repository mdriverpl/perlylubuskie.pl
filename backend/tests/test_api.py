"""Run against an explicitly configured isolated PostgreSQL test database."""
import os
from uuid import uuid4
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

if not os.environ.get('TEST_DATABASE_URL'):
    pytest.skip('Ustaw TEST_DATABASE_URL na osobną bazę testową PostgreSQL.', allow_module_level=True)
os.environ['DATABASE_URL'] = os.environ['TEST_DATABASE_URL']
os.environ.setdefault('SECRET_KEY', 'test-only-secret-that-is-more-than-32-characters')
from app.main import app, User, SessionLocal
from sqlalchemy import select


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def account(client):
    email = f'test-{uuid4().hex}@example.com'
    response = client.post('/api/auth/register', json={'email': email, 'name': 'Odkrywca', 'password': 'test-password-123'})
    assert response.status_code == 201, response.text
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}, email


def test_catalog_and_filter(client):
    assert client.get('/api/health').json()['status'] == 'ok'
    places = client.get('/api/places').json()
    assert len(places) >= 6
    assert all(p['category'] == 'nature' for p in client.get('/api/places?category=nature').json())
    assert client.get('/api/places', params={'q': 'Łagów'}).json()[0]['id'] == 1


def test_password_hash_and_login(client):
    headers, email = account(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user.password.startswith('$argon2')
        assert user.password != 'test-password-123'
    assert client.post('/api/auth/login', json={'email': email, 'password': 'wrong-password'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': email.upper(), 'password': 'test-password-123'}).status_code == 200
    assert client.post('/api/auth/register', json={'email': email, 'name': 'Duplicate', 'password': 'test-password-123'}).status_code == 409
    assert client.get('/api/routes', headers={'Authorization': 'Bearer forged-token'}).status_code == 401
    assert client.get('/api/routes').status_code in (401, 403)


def test_favorites_are_private_and_idempotent(client):
    alice, _ = account(client)
    bob, _ = account(client)
    assert client.put('/api/favorites/1', headers=alice).status_code == 204
    assert client.put('/api/favorites/1', headers=alice).status_code == 204
    assert client.get('/api/favorites', headers=alice).json() == [1]
    assert client.get('/api/favorites', headers=bob).json() == []
    assert client.put('/api/favorites/999', headers=alice).status_code == 404
    assert client.delete('/api/favorites/1', headers=alice).status_code == 204
    assert client.get('/api/favorites', headers=alice).json() == []


def test_route_ownership_gpx_and_order(client):
    alice, _ = account(client)
    bob, _ = account(client)
    payload = {'name': 'Jeziora & <zamki>', 'transport': 'bike', 'place_ids': [5, 1, 3]}
    response = client.post('/api/routes', headers=alice, json=payload)
    assert response.status_code == 201, response.text
    trip_id = response.json()['id']
    assert client.get('/api/routes', headers=alice).json()[0]['place_ids'] == [5, 1, 3]
    assert client.get('/api/routes', headers=bob).json() == []
    assert client.get(f'/api/routes/{trip_id}/gpx', headers=bob).status_code == 404
    assert client.delete(f'/api/routes/{trip_id}', headers=bob).status_code == 404
    gpx = client.get(f'/api/routes/{trip_id}/gpx', headers=alice)
    assert gpx.status_code == 200
    xml = ElementTree.fromstring(gpx.content)
    ns = {'g': 'http://www.topografix.com/GPX/1/1'}
    assert xml.find('g:rte/g:name', ns).text == payload['name']
    assert [p.find('g:name', ns).text for p in xml.findall('g:rte/g:rtept', ns)] == ['Jezioro Trześniowskie', 'Łagów', 'Międzyrzecki Rejon Umocniony']
    assert client.delete(f'/api/routes/{trip_id}', headers=alice).status_code == 204
    assert client.get('/api/routes', headers=alice).json() == []


@pytest.mark.parametrize('patch', [{'place_ids': [999]}, {'place_ids': []}, {'place_ids': [1, 1]}, {'transport': 'plane'}, {'name': '   '}])
def test_invalid_routes(client, patch):
    headers, _ = account(client)
    data = {'name': 'Wycieczka', 'transport': 'walk', 'place_ids': [1]}
    assert client.post('/api/routes', headers=headers, json={**data, **patch}).status_code == 422
