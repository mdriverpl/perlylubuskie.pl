import json
from io import BytesIO
from email.message import Message
from urllib.error import HTTPError

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import maps

app = FastAPI()
app.include_router(maps.router)
client = TestClient(app)


def test_no_key_and_invalid_tiles(monkeypatch):
    monkeypatch.delenv('HERE_API_KEY', raising=False)
    assert client.get('/api/maps/config').json()['provider'] == 'osm'
    assert client.get('/api/maps/tiles/map/8/138/84').status_code == 503
    for tile in ['map/21/0/0', 'map/8/256/0', 'map/8/0/256', 'other/8/0/0', 'map/-1/0/0']:
        assert client.get('/api/maps/tiles/' + tile).status_code == 422


def test_here_tile_proxy_and_credential_redaction(monkeypatch):
    key = 'test-private-key'
    monkeypatch.setenv('HERE_API_KEY', key)
    def upstream(url, timeout):
        assert url.startswith('https://maps.hereapi.com/v3/base/mc/8/138/84/jpeg?')
        assert 'style=explore.satellite.day' in url and 'apiKey=' + key in url
        response = BytesIO(b'jpeg-image')
        response.headers = Message()
        response.headers['Content-Type'] = 'image/jpeg'
        response.headers['Cache-Control'] = 'max-age=60'
        return response
    monkeypatch.setattr(maps, 'urlopen', upstream)
    response = client.get('/api/maps/tiles/satellite/8/138/84')
    assert response.content == b'jpeg-image'
    assert response.headers['cache-control'] == 'max-age=60'
    assert key not in str(response.headers)
    def denied(url, timeout):
        raise HTTPError(url, 403, key, None, BytesIO(key.encode()))
    monkeypatch.setattr(maps, 'urlopen', denied)
    response = client.get('/api/maps/tiles/map/8/138/84')
    assert response.status_code == 502
    assert key not in response.text


def test_supplier_notices_support_live_here_format_and_style(monkeypatch):
    notice = {'label': 'Supplier', 'minLevel': 3, 'maxLevel': 20, 'boundingBoxes': [{'south': 51, 'west': 14, 'north': 53, 'east': 16}]}
    raw = {'copyrights': {'ground': [notice], 'sat': [dict(notice, label='Satellite supplier')]}, 'resources': {'base': {'styles': {'explore.day': ['ground'], 'explore.satellite.day': ['sat'], 'topo.day': ['ground']}}}}
    normalized = maps.normalize_copyrights(raw)
    assert normalized['map'][0]['boxes'] == [[51, 14, 53, 16]]
    assert normalized['satellite'][0]['label'] == 'Satellite supplier'
    monkeypatch.setenv('HERE_API_KEY', 'private-config-key')
    monkeypatch.setattr(maps, '_copyright_cache', None)
    calls = []
    def request(path, params=None):
        calls.append(path)
        return json.dumps(raw).encode(), 'application/json', 'no-store'
    monkeypatch.setattr(maps, 'here_request', request)
    assert client.get('/api/maps/config').json() == {'provider': 'here', 'copyrights': normalized}
    assert client.get('/api/maps/config').status_code == 200
    assert calls == ['base/mc/8/138/84/png', 'copyright']


def test_metadata_success_does_not_enable_invalid_key(monkeypatch):
    monkeypatch.setenv('HERE_API_KEY', 'invalid-key')
    monkeypatch.setattr(maps, '_copyright_cache', None)
    def denied(path, params=None):
        raise maps.HTTPException(502, 'Klucz HERE nie ma dostępu do map.')
    monkeypatch.setattr(maps, 'here_request', denied)
    response = client.get('/api/maps/config')
    assert response.status_code == 502
    assert 'invalid-key' not in response.text


def test_location_search_is_regional_and_uses_separate_here_service(monkeypatch):
    location = {'id': 'here:sample:laz', 'title': 'Łaz, gmina Zabór, Polska', 'position': {'lat': 51.94944, 'lng': 15.68673}, 'address': {'state': 'Woj. Lubuskie', 'countryCode': 'POL'}}
    outside = dict(location, id='outside', address={'state': 'Woj. Śląskie', 'countryCode': 'POL'})
    def request(path, params, *, service):
        assert service == 'geocode' and path == 'geocode'
        assert params['q'] == 'Łaz, lubuskie'
        assert params['in'] == 'countryCode:POL'
        return json.dumps({'items': [location, outside]}).encode(), 'application/json', 'no-store'
    monkeypatch.setattr(maps, 'here_request', request)
    response = client.get('/api/maps/search', params={'q': ' Łaz '})
    assert response.status_code == 200
    assert response.json()['items'] == [{'id': 'here:sample:laz', 'name': location['title'], 'lat': 51.94944, 'lng': 15.68673}]
    for query in ['', 'a', '   ', 'x' * 121]:
        assert client.get('/api/maps/search', params={'q': query}).status_code == 422
