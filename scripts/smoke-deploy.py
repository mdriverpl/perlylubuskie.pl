"""Smoke test the real Nginx -> API -> PostgreSQL deployment. Uses the standard library."""
import json
import os
import urllib.request
import struct
import zlib
from uuid import uuid4

origin = os.environ.get('SMOKE_ORIGIN', 'http://127.0.0.1:8080')


def request(path, method='GET', data=None, token=None):
    headers = {'Content-Type': 'application/octet-stream' if isinstance(data,bytes) else 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = data if isinstance(data,bytes) else json.dumps(data).encode() if data is not None else None
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
def png_chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
# A valid small PNG with padding verifies the upload route exceeds the general 1 MB Nginx limit.
image=b'\x89PNG\r\n\x1a\n'+png_chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+png_chunk(b'IDAT',zlib.compress(b'\x00\x00\x80\x00'))+png_chunk(b'IEND',b'')+b'\x00'*1_200_000
upload=request('/api/place-photos','POST',image,token)
photo_place=request('/api/places','POST',{'name':'Deployment photo test','location':'Zabór','description':'Zdjęcie autora','place_type':'palace','lat':51.95,'lng':15.7,'photo_ids':[upload['id']],'photo_rights_confirmed':True},token)
photo=request(photo_place['image'])
assert photo[:4]==b'RIFF' and photo[8:12]==b'WEBP'
assert photo_place['details']['user_photos'][0]['author']=='Deployment test'
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
print('PASS: web, PostgreSQL, routing, auth, owned photo upload over 1 MB, public WebP, favorites, comments, unique visits and GPX through Nginx')
