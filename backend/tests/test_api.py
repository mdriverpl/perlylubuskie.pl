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


def test_lagow_attractions_catalog(client):
    catalog=client.get('/api/places').json()
    added=[p for p in catalog if 910001<=p['id']<=910008]
    assert len(added)==8
    assert next(p for p in added if p['id']==910005)['location']=='Kownaty'
    assert next(p for p in added if p['id']==910008)['location']=='Mostki'
    assert {p['id'] for p in client.get('/api/places?category=leisure').json()}>={910005,910008}
    assert any(p['id']==5 for p in client.get('/api/places',params={'q':'Ciecz'}).json())
    assert sum(p['id']==1 for p in catalog)==1
    assert sum(p['id']==5 for p in catalog)==1
    assert client.get('/api/places/910002/community').status_code==200


def test_ai_catalog_preserves_castle_identity(client, monkeypatch):
    from app import ai_routes
    captured = []
    monkeypatch.setattr(ai_routes, 'propose', lambda prompt, catalog, remote: captured.extend(catalog) or {'ok': True})
    assert client.post('/api/ai/plan', json={'prompt': 'Zaplanuj dzień w Łagowie'}).status_code == 200
    castle = next(p for p in captured if p['id'] == 1)
    assert 'zamek' in castle['name'].lower()
    assert 'joannit' in castle['name'].lower()
    assert castle['kind'] == 'castle'
    assert castle['location'] == 'Łagów'
    assert 'zamek' in castle['description'].lower()
    assert 'główna atrakcja' in castle['significance']
    assert set(castle) == {'id', 'name', 'display_name', 'subtitle', 'location', 'category', 'kind', 'description', 'significance', 'lat', 'lng'}


def test_lagow_hospitality_catalog(client):
    catalog = client.get('/api/places').json()
    services = [p for p in catalog if 920001 <= p['id'] <= 920133]
    assert len(services) == 133
    stays = client.get('/api/places', params={'category': 'stay', 'q': 'Łagów'}).json()
    food = client.get('/api/places', params={'category': 'food', 'q': 'Łagów'}).json()
    assert len(stays) == 115
    assert len(food) == 24
    assert 1 in {p['id'] for p in stays} & {p['id'] for p in food}
    assert 4 not in {p['id'] for p in food}
    laura = client.get('/api/places', params={'q': 'Restauracja Laura'}).json()
    assert len(laura) == 1
    assert laura[0]['name'] == 'Laura Spa'
    assert len(client.get('/api/places', params={'q': 'Chopina 20N/3'}).json()) == 1
    approximate = [p for p in services if p['details']['coordinate_accuracy'] == 'street']
    assert len(approximate) == 21
    assert all('przybliżona' in p['details']['visit_note'] for p in approximate)
    assert client.get(f"/api/places/{services[0]['id']}/community").status_code == 200


def test_create_place_catalog_and_social(client):
    from app.main import Place
    headers, _ = account(client)
    data = {'name': 'Test palace ' + uuid4().hex, 'subtitle': 'Nowe miejsce', 'location': 'Zabór', 'description': 'Opis miejsca', 'place_type': 'palace', 'lat': 51.95, 'lng': 15.7}
    assert client.post('/api/places', json=data).status_code in (401, 403)
    for patch in ({'name': ' '}, {'lat': 91}, {'place_type': 'custom'}, {'image': 'javascript:alert(1)'}, {'description': 'x' * 2001}):
        assert client.post('/api/places', headers=headers, json={**data, **patch}).status_code == 422
    result = client.post('/api/places', headers=headers, json=data)
    assert result.status_code == 201, result.text
    place = result.json()
    try:
        assert place['id'] >= 1000000000
        assert place['category'] == 'heritage'
        assert place['details']['kind'] == 'palace'
        assert client.get('/api/places', params={'q': data['name']}).json()[0]['id'] == place['id']
        url = f"/api/places/{place['id']}"
        assert client.put(url + '/like', headers=headers).json()['like_count'] == 1
        assert client.post(url + '/comments', headers=headers, json={'body': 'Nowe miejsce w katalogu'}).status_code == 201
        community = client.get(url + '/community').json()
        assert community['comment_count'] == 1
        assert community['like_count'] == 1
        assert client.get('/api/routes', headers=headers).json() == []
    finally:
        with SessionLocal() as db:
            db.delete(db.get(Place, place['id']))
            db.commit()


def test_wineries_seed_and_community(client):
    vineyards = client.get('/api/places?category=vineyard').json()
    assert len(vineyards) == 30
    assert {900001, 900002, 900003, 900007, 900027, 900030}.issubset({p['id'] for p in vineyards})
    ingrid = next(p for p in vineyards if p['id'] == 900001)
    assert ingrid['name'] == 'Winnica Ingrid'
    assert 'Łaz' in ingrid['location']
    assert ingrid['details']['sources']
    assert client.get('/api/places/900001/community').status_code == 200


def test_heritage_catalog_sync_preserves_community(client):
    places = client.get('/api/places').json()
    heritage = [p for p in places if p['details'].get('wikidata')]
    assert len(heritage) == 175
    assert sum(p['details']['kind'] == 'palace' for p in heritage) == 151
    place_id = next(p['id'] for p in heritage if p['id'] != 1)
    headers, _ = account(client)
    assert client.put(f'/api/places/{place_id}/visit', headers=headers).status_code == 204
    comment = client.post(f'/api/places/{place_id}/comments', headers=headers, json={'body': 'Zachowaj po synchronizacji katalogu.'})
    assert comment.status_code == 201
    before = client.get(f'/api/places/{place_id}/community', headers=headers).json()
    # A second startup must update an existing database without recreating its rows.
    with TestClient(app) as restarted:
        after = restarted.get(f'/api/places/{place_id}/community', headers=headers).json()
        assert after == before


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
    payload = {'name': 'Jeziora & <zamki>', 'description': 'Opis trasy <jeziora> i lasy.', 'transport': 'bike', 'place_ids': [5, 1, 3]}
    response = client.post('/api/routes', headers=alice, json=payload)
    assert response.status_code == 201, response.text
    trip_id = response.json()['id']
    assert client.get('/api/routes', headers=alice).json()[0]['place_ids'] == [5, 1, 3]
    assert client.get('/api/routes', headers=alice).json()[0]['description'] == payload['description']
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
    updated = {**payload, 'name': 'Changed route', 'description': 'Updated description', 'transport': 'walk', 'place_ids': [3, 1]}
    assert client.put(f'/api/routes/{trip_id}', headers=bob, json=updated).status_code == 404
    assert client.put(f'/api/routes/{trip_id}', json=updated).status_code in (401, 403)
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'place_ids': [999]}).status_code == 422
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'place_ids': [1, 1]}).status_code == 422
    changed = client.put(f'/api/routes/{trip_id}', headers=alice, json=updated)
    assert changed.status_code == 200, changed.text
    assert changed.json() == {**updated, 'id': trip_id, 'point_positions': [], 'cover_image': '', 'is_public': False, 'custom_points': []}
    assert client.get('/api/routes', headers=alice).json() == [{**updated, 'id': trip_id, 'point_positions': [], 'cover_image': '', 'is_public': False, 'custom_points': []}]
    positions = [{'id': 3, 'lat': 52.12, 'lng': 15.31}]
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'point_positions': positions}).json()['point_positions'] == positions
    assert client.get('/api/routes', headers=alice).json()[0]['point_positions'] == positions
    assert client.put(f'/api/routes/{trip_id}', headers=bob, json={**updated, 'point_positions': positions}).status_code == 404
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'point_positions': [{'id': 999, 'lat': 52, 'lng': 15}]}).status_code == 422
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'point_positions': positions*2}).status_code == 422
    gpx = client.get(f'/api/routes/{trip_id}/gpx', headers=alice)
    assert '52.12' in gpx.text
    cover = 'data:image/webp;base64,UklGRg=='
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'cover_image': cover}).json()['cover_image'] == cover
    assert client.get('/api/routes', headers=alice).json()[0]['cover_image'] == cover
    assert client.put(f'/api/routes/{trip_id}', headers=bob, json={**updated, 'cover_image': cover}).status_code == 404
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'cover_image': 'javascript:alert(1)'}).status_code == 422
    assert client.put(f'/api/routes/{trip_id}', headers=alice, json={**updated, 'cover_image': 'data:image/webp;base64,' + 'A'*900000}).status_code == 422
    assert client.delete(f'/api/routes/{trip_id}', headers=alice).status_code == 204
    assert client.get('/api/routes', headers=alice).json() == []


def test_private_public_routes_with_custom_points(client):
    alice, _ = account(client)
    bob, _ = account(client)
    data = {'name': 'Short route', 'transport': 'walk', 'place_ids': [1, -1], 'custom_points': [{'id': -1, 'name': 'Route waypoint', 'lat': 52.3, 'lng': 15.3}]}
    response = client.post('/api/routes', headers=alice, json=data)
    assert response.status_code == 201, response.text
    route = response.json()
    route_id = route['id']
    try:
        assert route['is_public'] is False
        assert route['description'] == ''
        assert route_id not in {r['id'] for r in client.get('/api/routes/public').json()}
        assert client.get('/api/routes', headers=bob).json() == []
        public = {**data, 'is_public': True}
        assert client.put(f'/api/routes/{route_id}', headers=bob, json=public).status_code == 404
        assert client.put(f'/api/routes/{route_id}', headers=alice, json=public).status_code == 200
        shared = next(r for r in client.get('/api/routes/public').json() if r['id'] == route_id)
        assert shared['is_public'] is True
        assert shared['custom_points'] == data['custom_points']
        assert client.delete(f'/api/routes/{route_id}', headers=bob).status_code == 404
        assert client.put(f'/api/routes/{route_id}', headers=alice, json=data).status_code == 200
        assert route_id not in {r['id'] for r in client.get('/api/routes/public').json()}
    finally:
        client.delete(f'/api/routes/{route_id}', headers=alice)


@pytest.mark.parametrize('patch', [{'place_ids': [999]}, {'place_ids': []}, {'place_ids': [1, 1]}, {'transport': 'plane'}, {'name': '   '}, {'description': 'x' * 2001}])
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


def test_routing_private_custom_points(client, monkeypatch):
    calls = []
    monkeypatch.setattr('app.main.calculate_route', lambda points, transport: calls.append(points) or {'ok': True})
    point = {'id': -1234567890123, 'name': 'Mój punkt', 'lat': 52.1, 'lng': 15.3}
    payload = {'place_ids': [1, point['id']], 'transport': 'walk', 'custom_points': [point]}
    assert client.post('/api/routing', json=payload).status_code == 200
    assert calls[0][0]['name'] == 'Łagów'
    assert calls[0][1] == {k: point[k] for k in ('name', 'lat', 'lng')}
    assert client.post('/api/routing', json={**payload, 'custom_points': []}).status_code == 422
    assert client.post('/api/routing', json={**payload, 'custom_points': [point, point]}).status_code == 422
    assert client.post('/api/routing', json={**payload, 'custom_points': [dict(point, id=1)]}).status_code == 422
    assert client.post('/api/routing', json={**payload, 'custom_points': [dict(point, lat=91)]}).status_code == 422
    assert client.post('/api/routing', json={**payload, 'custom_points': [dict(point, name=' ')]}).status_code == 422
    assert client.get('/api/places', params={'q': point['name']}).json() == []


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


def test_likes_unique_accounts_counts_and_comment_popularity(client):
    alice, _ = account(client)
    bob, _ = account(client)
    url = '/api/places/5'
    before = client.get(url + '/community').json()
    assert client.put(url + '/like').status_code in (401, 403)
    assert client.put('/api/places/999/like', headers=alice).status_code == 404
    for _ in range(2):
        marked = client.put(url + '/like', headers=alice).json()
        assert marked['like_count'] == before['like_count'] + 1
        assert marked['liked'] is True
    assert client.get(url + '/community', headers=bob).json()['liked'] is False
    client.put(url + '/like', headers=bob)
    comment = client.post(url + '/comments', headers=alice, json={'body': 'Warto odwiedzić!'}).json()
    own = next(p for p in client.get('/api/places', headers=alice).json() if p['id'] == 5)
    public = next(p for p in client.get('/api/places').json() if p['id'] == 5)
    assert own['liked'] is True and public['liked'] is False
    assert own['like_count'] == before['like_count'] + 2
    assert own['comment_count'] == before['comment_count'] + 1
    assert own['popularity'] == own['like_count'] + own['comment_count']
    client.delete(url + '/comments/' + str(comment['id']), headers=alice)
    for _ in range(2):
        removed = client.delete(url + '/like', headers=alice).json()
        assert removed['liked'] is False
        assert removed['like_count'] == before['like_count'] + 1
    client.delete(url + '/like', headers=bob)
    assert client.get(url + '/community').json()['popularity'] == before['popularity']
    assert client.get('/api/places', headers={'Authorization': 'Bearer expired-token'}).status_code == 200


def test_concurrent_likes_are_idempotent(client):
    from concurrent.futures import ThreadPoolExecutor
    headers, _ = account(client)
    url = '/api/places/6'
    before = client.get(url + '/community').json()['like_count']
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda _: client.put(url + '/like', headers=headers), range(4)))
    assert all(response.status_code == 200 for response in responses)
    assert client.get(url + '/community').json()['like_count'] == before + 1
    client.delete(url + '/like', headers=headers)


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
