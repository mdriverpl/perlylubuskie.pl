import json
from io import BytesIO
from urllib.error import URLError

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import offline_maps as maps

app = FastAPI()
app.include_router(maps.router)
client = TestClient(app)
BOUNDS = {'west': 15.28, 'south': 52.33, 'east': 15.30, 'north': 52.35}


@pytest.fixture(autouse=True)
def clear_cache():
    maps._cache.clear()


def data():
    return {'elements': [
        {'type': 'way', 'id': 1, 'tags': {'highway': 'path', 'name': '<Ścieżka>'}, 'geometry': [{'lon': 15.29, 'lat': 52.33}, {'lon': 15.30, 'lat': 52.34}]},
        {'type': 'way', 'id': 2, 'tags': {'natural': 'water'}, 'geometry': [{'lon': x, 'lat': y} for x, y in [[15.29, 52.33], [15.30, 52.33], [15.30, 52.34], [15.29, 52.33]]]},
        {'type': 'node', 'id': 3, 'lat': 52.34, 'lon': 15.29, 'tags': {'place': 'village', 'name': 'Łagów', 'unneeded': 'discard'}},
    ]}


def test_download_is_bounded_osm_data_not_tiles_and_cached(monkeypatch):
    requests = []
    def upstream(request, timeout):
        requests.append(request)
        assert request.full_url == 'https://overpass-api.de/api/interpreter'
        assert 'PerlyLubuskie' in request.get_header('User-agent')
        assert b'52.330000' in request.data
        assert timeout == 40
        return BytesIO(json.dumps(data()).encode())
    monkeypatch.setattr(maps, 'urlopen', upstream)
    first = client.get('/api/maps/offline', params=BOUNDS)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result['bounds'] == [15.28, 52.33, 15.30, 52.35]
    assert result['map']['type'] == 'FeatureCollection'
    assert len(result['map']['features']) == 3
    assert result['map']['features'][0]['geometry']['type'] == 'Polygon'
    assert 'unneeded' not in result['map']['features'][-1]['properties']
    assert 'OpenStreetMap' in result['attribution']
    assert client.get('/api/maps/offline', params=BOUNDS).json() == result
    assert len(requests) == 1


@pytest.mark.parametrize('bounds', [
    dict(west=14, south=50, east=16, north=54),
    dict(west=16, south=52, east=15, north=52.01),
    dict(west=15, south=52, east=15.001, north=53),
    dict(west=15, south=86, east=15.01, north=86.01),
    dict(west=float('nan'), south=52, east=15.01, north=52.01),
])
def test_invalid_or_large_extract_never_reaches_upstream(monkeypatch, bounds):
    monkeypatch.setattr(maps, 'urlopen', lambda *a, **k: pytest.fail('Unexpected map download'))
    assert client.get('/api/maps/offline', params=bounds).status_code == 422


def test_upstream_failure_and_oversize_preserve_error_messages(monkeypatch):
    def failed(*args, **kwargs):
        raise URLError('private upstream details')
    monkeypatch.setattr(maps, 'urlopen', failed)
    response = client.get('/api/maps/offline', params=BOUNDS)
    assert response.status_code == 502
    assert 'private' not in response.text
    monkeypatch.setattr(maps, 'urlopen', lambda *a, **k: BytesIO(b'x'*(maps.MAX_BYTES+1)))
    assert client.get('/api/maps/offline', params=BOUNDS).status_code == 422
    for body in [b'not json', b'{"remark":"runtime error","elements":[]}', b'{"elements":[]}']:
        monkeypatch.setattr(maps, 'urlopen', lambda *a, **k: BytesIO(body))
        assert client.get('/api/maps/offline', params=BOUNDS).status_code in (422, 502)


def test_multipolygon_rings_and_holes():
    def member(points, role='outer'):
        return {'role': role, 'geometry': [{'lon': x, 'lat': y} for x, y in points]}
    result = maps.to_geojson({'elements': [{'type': 'relation', 'id': 10, 'tags': {'natural': 'water'}, 'members': [
        member([[0, 0], [2, 0], [2, 2]]), member([[0, 0], [0, 2], [2, 2]]),
        member([[.5, .5], [1, .5], [1, 1], [.5, .5]], 'inner'),
    ]}]})
    polygon = result['features'][0]['geometry']
    assert polygon['type'] == 'MultiPolygon'
    assert len(polygon['coordinates'][0]) == 2
    assert polygon['coordinates'][0][0][0] == polygon['coordinates'][0][0][-1]


def test_concurrent_extract_limit():
    assert maps._slots.acquire(False)
    assert maps._slots.acquire(False)
    try:
        assert client.get('/api/maps/offline', params=BOUNDS).status_code == 429
    finally:
        maps._slots.release()
        maps._slots.release()
