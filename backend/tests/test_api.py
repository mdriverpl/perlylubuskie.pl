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


def test_route_ownership_gpx_and_order(client, monkeypatch):
    monkeypatch.setattr('app.main.calculate_route', lambda points, transport: {'geometry': {'type': 'LineString', 'coordinates': [[p['lng'], p['lat']] for p in points]}, 'distance_m': 10000, 'duration_s': 3600})
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
    assert xml.find('g:trk/g:name', ns).text == payload['name']
    assert [p.find('g:name', ns).text for p in xml.findall('g:wpt', ns)] == ['Jezioro Trześniowskie', 'Łagów', 'Międzyrzecki Rejon Umocniony']
    assert len(xml.findall('g:trk/g:trkseg/g:trkpt', ns)) == 3
    assert client.delete(f'/api/routes/{trip_id}', headers=alice).status_code == 204
    assert client.get('/api/routes', headers=alice).json() == []


@pytest.mark.parametrize('patch', [{'place_ids': [999]}, {'place_ids': []}, {'place_ids': [1, 1]}, {'transport': 'plane'}, {'name': '   '}])
def test_invalid_routes(client, patch):
    headers, _ = account(client)
    data = {'name': 'Wycieczka', 'transport': 'walk', 'place_ids': [1]}
    assert client.post('/api/routes', headers=headers, json={**data, **patch}).status_code == 422


def test_routing_endpoint_order_and_validation(client, monkeypatch):
    calls = []
    def fake_route(points, transport):
        calls.append((points, transport))
        return {'geometry': {'type': 'LineString', 'coordinates': [[p['lng'], p['lat']] for p in points]}, 'distance_m': 3000, 'duration_s': 900}
    monkeypatch.setattr('app.main.calculate_route', fake_route)
    result = client.post('/api/routing', json={'place_ids': [5, 1], 'transport': 'walk'})
    assert result.status_code == 200
    assert calls[0][1] == 'walk'
    assert calls[0][0][0]['name'] == 'Jezioro Trześniowskie'
    assert client.post('/api/routing', json={'place_ids': [999, 1], 'transport': 'bike'}).status_code == 422
    assert client.post('/api/routing', json={'place_ids': [1], 'transport': 'bike'}).status_code == 422
    assert client.post('/api/routing', json={'place_ids': [5, 1], 'transport': 'car'}).status_code == 422


def test_visits_count_unique_accounts_and_allow_undo(client):
    alice, _ = account(client)
    bob, _ = account(client)
    url = '/api/places/1'
    before = client.get(url + '/community').json()['visit_count']
    assert client.put(url + '/visit').status_code in (401, 403)
    assert client.put('/api/places/999/visit', headers=alice).status_code == 404
    assert client.put(url + '/visit', headers=alice).status_code == 204
    assert client.put(url + '/visit', headers=alice).status_code == 204
    own = client.get(url + '/community', headers=alice).json()
    assert own['visited'] is True
    assert own['visit_count'] == before + 1
    assert client.get(url + '/community', headers=bob).json()['visited'] is False
    assert client.put(url + '/visit', headers=bob).status_code == 204
    assert client.get(url + '/community').json()['visit_count'] == before + 2
    assert client.delete(url + '/visit', headers=alice).status_code == 204
    assert client.delete(url + '/visit', headers=alice).status_code == 204
    assert client.get(url + '/community').json()['visit_count'] == before + 1
    client.delete(url + '/visit', headers=bob)
    assert client.get(url + '/community').json()['visit_count'] == before


def test_simultaneous_visit_marks_count_once(client):
    from concurrent.futures import ThreadPoolExecutor
    headers, _ = account(client)
    before = client.get('/api/places/5/community').json()['visit_count']
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.put('/api/places/5/visit', headers=headers).status_code, range(8)))
    assert responses == [204] * 8
    assert client.get('/api/places/5/community').json()['visit_count'] == before + 1
    client.delete('/api/places/5/visit', headers=headers)


def test_comments_public_read_private_ownership_and_validation(client):
    alice, email = account(client)
    bob, _ = account(client)
    url = '/api/places/1/comments'
    text = '<img src=x onerror=alert(1)> Ładne miejsce & widok.'
    assert client.post(url, json={'body': text}).status_code in (401, 403)
    for body in ('', '   ', 'x' * 2001):
        assert client.post(url, headers=alice, json={'body': body}).status_code == 422
    response = client.post(url, headers=alice, json={'body': '  ' + text + '  '})
    assert response.status_code == 201, response.text
    comment = response.json()
    assert comment['body'] == text
    assert comment['can_delete'] is True
    from datetime import datetime
    assert datetime.fromisoformat(comment['created_at']).tzinfo is not None
    public = client.get('/api/places/1/community').json()
    item = next(c for c in public['comments'] if c['id'] == comment['id'])
    assert item['can_delete'] is False
    assert item['author'] == 'Odkrywca'
    assert 'email' not in item and 'user_id' not in item and email not in str(item)
    path = f"{url}/{comment['id']}"
    assert client.delete(path, headers=bob).status_code == 404
    assert client.delete(f"/api/places/2/comments/{comment['id']}", headers=alice).status_code == 404
    assert client.delete(path, headers=alice).status_code == 204
    assert comment['id'] not in [c['id'] for c in client.get('/api/places/1/community').json()['comments']]
    assert client.get('/api/places/999/community').status_code == 404
    assert client.get('/api/places/1/community?limit=51').status_code == 422
    assert client.get('/api/places/1/community?offset=-1').status_code == 422
    assert client.get('/api/places/1/community', headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_comment_pagination_and_rate_limit(client):
    from app.main import Comment
    headers, email = account(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        rows = [Comment(user_id=user.id, place_id=2, body=f'Comment {i}') for i in range(21)]
        db.add_all(rows)
        db.commit()
        ids = {row.id for row in rows}
    first = client.get('/api/places/2/community?limit=2').json()
    second = client.get('/api/places/2/community?limit=2&offset=2').json()
    assert first['comment_count'] >= 21
    assert len(first['comments']) == len(second['comments']) == 2
    assert not ({c['id'] for c in first['comments']} & {c['id'] for c in second['comments']})
    assert client.post('/api/places/2/comments', headers=headers, json={'body': 'Too fast'}).status_code == 429
    with SessionLocal() as db:
        for row in db.scalars(select(Comment).where(Comment.id.in_(ids))).all():
            db.delete(row)
        db.commit()
