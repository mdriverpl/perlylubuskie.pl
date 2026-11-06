"""Real endpoint/ORM tests against an isolated in-memory database, with no startup workers."""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault('SECRET_KEY', 'test-only-live-location-secret-at-least-32-characters')

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, User, LiveLocation, GuestLiveLocation, get_db, SECRET_KEY
from app import live_locations


@pytest.fixture
def environment():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    User.__table__.create(engine)
    LiveLocation.__table__.create(engine)
    GuestLiveLocation.__table__.create(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
    with Session() as db:
        db.add_all([User(id=i, email=f'person-{i}@example.com', name=f'Osoba {i}', password='test-placeholder') for i in range(1, 6)])
        db.commit()
    def test_db():
        with Session() as db:
            yield db
    old_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = test_db
    client = TestClient(app)  # No lifespan: no catalog import or production database connection.
    def headers(user_id):
        token = jwt.encode({'sub': str(user_id), 'iss': 'perly', 'exp': datetime.now(timezone.utc)+timedelta(hours=1)}, SECRET_KEY, algorithm='HS256')
        return {'Authorization': 'Bearer '+token}
    yield client, headers, Session
    client.close()
    if old_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = old_override
    engine.dispose()


def point(lat=52.33, lng=15.29, **changes):
    return dict(lat=lat, lng=lng, accuracy=8, measured_at=datetime.now(timezone.utc).isoformat(), **changes)


def start(client, headers, user_id, **kwargs):
    response = client.post('/api/live-location', headers=headers(user_id), json=point(**kwargs))
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store, private'
    return response.json()['session_id']


def test_opt_in_authentication_radius_and_no_identity_leak(environment):
    client, headers, Session = environment
    assert client.get('/api/live-location/nearby').status_code in (401, 403)
    assert client.post('/api/live-location', json=point()).status_code in (401, 403)
    assert client.get('/api/live-location/nearby', headers=headers(1)).status_code == 403
    start(client, headers, 1)
    start(client, headers, 2, lat=52.331)
    start(client, headers, 3, lat=53.3)
    result = client.get('/api/live-location/nearby', headers=headers(1))
    assert result.status_code == 200, result.text
    people = result.json()['people']
    assert [p['id'] for p in people] == [2]
    assert people[0]['name'] == 'Osoba 2'
    assert 100 < people[0]['distance_m'] < 120
    assert not {'email', 'session_id', 'password', 'token'} & people[0].keys()
    assert result.headers['cache-control'] == 'no-store, private'
    assert client.get('/api/live-location/nearby?radius_km=11', headers=headers(1)).status_code == 422
    assert client.get('/api/live-location/nearby?lat=53.3&lng=15.29', headers=headers(1)).json()['people'] == people, 'Arbitrary search origins are ignored'


def test_update_stop_old_requests_and_device_isolation(environment):
    client, headers, Session = environment
    session = start(client, headers, 1)
    update = {**point(lat=52.332), 'session_id': session}
    assert client.put('/api/live-location', headers=headers(1), json=update).status_code == 200
    assert client.put('/api/live-location', headers=headers(2), json=update).status_code == 409
    assert client.request('DELETE', '/api/live-location', headers=headers(2), json={'session_id': session}).status_code == 204
    assert client.get('/api/live-location/nearby', headers=headers(1)).status_code == 200
    newer = start(client, headers, 1)
    assert newer != session
    assert client.request('DELETE', '/api/live-location', headers=headers(1), json={'session_id': session}).status_code == 204
    assert client.get('/api/live-location/nearby', headers=headers(1)).status_code == 200, 'Old device cannot stop the newer session'
    assert client.put('/api/live-location', headers=headers(1), json=update).status_code == 409
    assert client.request('DELETE', '/api/live-location', headers=headers(1), json={'session_id': newer}).status_code == 204
    assert client.get('/api/live-location/nearby', headers=headers(1)).status_code == 403
    assert client.put('/api/live-location', headers=headers(1), json={**point(), 'session_id': newer}).status_code == 409
    with Session() as db:
        assert db.scalar(select(LiveLocation)) is None, 'Stopping deletes the actual server position'


def test_stale_positions_expire_and_cleanup_removes_coordinates(environment):
    client, headers, Session = environment
    start(client, headers, 1)
    old = start(client, headers, 2, lat=52.331)
    with Session() as db:
        db.get(LiveLocation, 2).expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        db.commit()
    assert client.get('/api/live-location/nearby', headers=headers(1)).json()['people'] == []
    assert client.get('/api/live-location/nearby', headers=headers(2)).status_code == 403
    assert client.put('/api/live-location', headers=headers(2), json={**point(), 'session_id': old}).status_code == 409
    with Session() as db:
        live_locations.purge_expired(db, LiveLocation)
        db.commit()
        assert db.get(LiveLocation, 2) is None
        assert db.get(LiveLocation, 1) is not None


@pytest.mark.parametrize('changes', [
    {'lat': 91}, {'lng': -181}, {'accuracy': 101}, {'accuracy': -1},
    {'measured_at': '2020-01-01T00:00:00Z'}, {'measured_at': '2035-01-01T00:00:00Z'}, {'measured_at': '2026-01-01T00:00:00'},
])
def test_bad_or_stale_gps_never_gets_published(environment, changes):
    client, headers, Session = environment
    payload = point()
    payload.update(changes)
    response = client.post('/api/live-location', headers=headers(1), json=payload)
    assert response.status_code == 422, response.text
    with Session() as db:
        assert db.scalar(select(LiveLocation)) is None


def test_out_of_order_gps_cannot_overwrite_newer_fix(environment):
    client, headers, Session = environment
    session = start(client, headers, 1)
    stale = point(lat=50)
    stale['measured_at'] = (datetime.now(timezone.utc)-timedelta(seconds=20)).isoformat()
    response = client.put('/api/live-location', headers=headers(1), json={**stale, 'session_id': session})
    assert response.status_code == 409
    with Session() as db:
        assert db.get(LiveLocation, 1).lat == 52.33


def test_guests_can_share_nick_and_see_participants_without_accounts(environment):
    client, headers, Session = environment
    first = client.post('/api/live-location/guest', json={**point(), 'nick': 'Wędrowiec'}).json()
    second = client.post('/api/live-location/guest', json={**point(lat=52.331), 'nick': '<b>Rowerzysta</b>'}).json()
    auth = {'X-Location-Token': first['guest_token']}
    assert client.get('/api/live-location/guest/nearby').status_code == 401
    result = client.get('/api/live-location/guest/nearby', headers=auth)
    assert result.status_code == 200, result.text
    assert [p['name'] for p in result.json()['people']] == ['<b>Rowerzysta</b>']
    assert 'guest_token' not in result.text and 'token_hash' not in result.text
    start(client, headers, 1, lat=52.332)
    assert len(client.get('/api/live-location/guest/nearby', headers=auth).json()['people']) == 2
    assert len(client.get('/api/live-location/nearby', headers=headers(1)).json()['people']) == 2
    update = {**point(lat=52.333), 'session_id': first['session_id']}
    assert client.put('/api/live-location/guest', headers=auth, json=update).status_code == 200
    assert client.put('/api/live-location/guest', headers={'X-Location-Token': second['guest_token']}, json=update).status_code == 409
    assert client.request('DELETE', '/api/live-location/guest', headers=auth, json={'session_id': first['session_id']}).status_code == 204
    assert client.get('/api/live-location/guest/nearby', headers=auth).status_code == 401
    assert client.put('/api/live-location/guest', headers=auth, json=update).status_code == 401
    with Session() as db:
        assert db.get(GuestLiveLocation, first['session_id']) is None
        stored = db.get(GuestLiveLocation, second['session_id'])
        assert stored.token_hash != second['guest_token']


def test_guest_expiry_and_nickname_validation(environment):
    client, headers, Session = environment
    for nick in ['', ' ', 'A', 'x'*33, 'Hi\nthere']:
        assert client.post('/api/live-location/guest', json={**point(), 'nick': nick}).status_code == 422
    guest = client.post('/api/live-location/guest', json={**point(), 'nick': 'Gość'}).json()
    with Session() as db:
        db.get(GuestLiveLocation, guest['session_id']).expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        db.commit()
    assert client.get('/api/live-location/guest/nearby', headers={'X-Location-Token': guest['guest_token']}).status_code == 401
    with Session() as db:
        live_locations.purge_expired(db, LiveLocation, GuestLiveLocation);db.commit()
        assert db.get(GuestLiveLocation, guest['session_id']) is None
