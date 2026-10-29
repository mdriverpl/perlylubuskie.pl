"""Smoke test the real Nginx -> API -> PostgreSQL deployment. Uses the standard library."""
import json
import os
import urllib.request
from uuid import uuid4

origin = os.environ.get('SMOKE_ORIGIN', 'http://127.0.0.1:8080')


def request(path, method='GET', data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(urllib.request.Request(origin + path, data=body, headers=headers, method=method), timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if 'application/json' in response.headers.get('Content-Type', '') else raw


assert b'<div id="app"></div>' in request('/')
assert request('/healthz').strip() == b'ok'
assert request('/api/health')['status'] == 'ok'
places = request('/api/places')
assert len(places) >= 6
for transport in ('bike', 'walk'):
    route = request('/api/routing', 'POST', {'transport': transport, 'place_ids': [1, 5]})
    assert route['geometry']['type'] == 'LineString'
    assert len(route['geometry']['coordinates']) > 10
    assert route['distance_m'] > 1000
    assert route['duration_s'] > 0
credentials = {'name': 'Deployment test', 'email': f'deploy-{uuid4().hex}@example.com', 'password': 'ci-test-password-123'}
account = request('/api/auth/register', 'POST', credentials)
token = request('/api/auth/login', 'POST', credentials)['access_token']
place_id = places[0]['id']
community_path = f'/api/places/{place_id}/community'
before_visits = request(community_path)['visit_count']
request(f'/api/places/{place_id}/visit', 'PUT', token=token)
request(f'/api/places/{place_id}/visit', 'PUT', token=token)
community = request(community_path, token=token)
assert community['visit_count'] == before_visits + 1 and community['visited']
comment = request(f'/api/places/{place_id}/comments', 'POST', {'body': 'Deployment test comment'}, token)
assert request(community_path)['comments'][0]['body'] == 'Deployment test comment'
request(f"/api/places/{place_id}/comments/{comment['id']}", 'DELETE', token=token)
request(f'/api/places/{place_id}/visit', 'DELETE', token=token)
assert request(community_path)['visit_count'] == before_visits
request(f'/api/favorites/{place_id}', 'PUT', token=token)
assert place_id in request('/api/favorites', token=token)
trip = request('/api/routes', 'POST', {'name': 'Deployment test', 'transport': 'walk', 'place_ids': [1, 5]}, token)
assert request('/api/routes', token=token)[0]['id'] == trip['id']
assert b'<trkpt' in request(f"/api/routes/{trip['id']}/gpx", token=token)
print('PASS: web, PostgreSQL, routing, auth, favorites, comments, unique visits and GPX through Nginx')
