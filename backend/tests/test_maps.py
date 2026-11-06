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


@pytest.fixture(autouse=True)
def clear_tile_cache():
    maps._tile_cache.clear()
    maps._tile_cache_bytes=0


def test_no_key_and_invalid_tiles(monkeypatch):
    monkeypatch.delenv('HERE_API_KEY', raising=False)
    assert client.get('/api/maps/config').json()['provider'] == 'osm'
    assert client.get('/api/maps/tiles/map/8/138/84').status_code == 503
    for tile in ['map/21/0/0', 'map/8/256/0', 'map/8/0/256', 'other/8/0/0', 'map/-1/0/0']:
        assert client.get('/api/maps/tiles/' + tile).status_code == 422


def test_simplified_roads_disable_pois_and_labels(monkeypatch):
    calls=[]
    def here(path, params=None, **kwargs):
        calls.append((path, params))
        return b'map-image', 'image/png', 'max-age=60'
    monkeypatch.setattr(maps, 'here_request', here)
    result=client.get('/api/maps/tiles/map/12/2221/1346?roads_only=true')
    assert result.status_code==200
    assert calls[0][0]=='base/mc/12/2221/1346/png'
    assert calls[0][1]['features']=='pois:disabled'
    assert calls[0][1]['style']=='explore.day'
    client.get('/api/maps/tiles/map/12/2221/1346')
    assert len(calls)==2, 'Detailed and simplified tiles use separate cache keys'


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
    maps._tile_cache.clear();maps._tile_cache_bytes=0
    response = client.get('/api/maps/tiles/map/8/138/84')
    assert response.status_code == 502
    assert key not in response.text


def test_here_tile_burst_queues_instead_of_rejecting(monkeypatch):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setenv('HERE_API_KEY','test-concurrent-key')
    lock=threading.Lock()
    active=peak=0
    def upstream(url,timeout):
        nonlocal active,peak
        with lock:
            active+=1;peak=max(peak,active)
        time.sleep(.04)
        with lock:active-=1
        result=BytesIO(b'png');result.headers=Message();result.headers['Content-Type']='image/png'
        return result
    monkeypatch.setattr(maps,'urlopen',upstream)
    with ThreadPoolExecutor(max_workers=12) as executor:
        results=list(executor.map(lambda i:maps.here_request(f'base/mc/12/2221/{1340+i}/png'),range(12)))
    assert len(results)==12 and all(body==b'png' for body,_,_ in results)
    assert peak<=8


def test_here_tile_cache_reuses_tiles_and_bounds_memory(monkeypatch):
    calls=[]
    def request(path,params=None):
        calls.append(path)
        return b'image','image/png','max-age=86400'
    monkeypatch.setattr(maps,'here_request',request)
    monkeypatch.setattr(maps,'_TILE_CACHE_MAX_BYTES',5)
    url='/api/maps/tiles/map/8/138/84'
    assert client.get(url).status_code==200
    cached=client.get(url)
    assert cached.status_code==200 and cached.headers['age']=='0'
    assert len(calls)==1
    assert client.get('/api/maps/tiles/map/8/139/84').status_code==200
    assert maps._tile_cache_bytes<=5
    assert client.get(url).status_code==200
    assert len(calls)==3


@pytest.mark.parametrize('cache_control',['no-store','private, max-age=60','no-cache, max-age=60','max-age=0'])
def test_tile_cache_respects_upstream_policy(monkeypatch,cache_control):
    calls=[]
    def request(path,params=None):
        calls.append(path);return b'image','image/png',cache_control
    monkeypatch.setattr(maps,'here_request',request)
    for _ in range(2):assert client.get('/api/maps/tiles/map/8/138/84').status_code==200
    assert len(calls)==2


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


def test_location_search_covers_poland_and_uses_separate_here_service(monkeypatch):
    location = {'id': 'here:sample:laz', 'title': 'Łaz, gmina Zabór, Polska', 'position': {'lat': 51.94944, 'lng': 15.68673}, 'address': {'state': 'Woj. Lubuskie', 'countryCode': 'POL'}}
    outside = dict(location, id='outside', address={'state': 'Berlin', 'countryCode': 'DEU'})
    def request(path, params, *, service):
        assert service == 'geocode' and path == 'geocode'
        assert params['q'] == 'Łaz'
        assert params['in'] == 'countryCode:POL'
        assert 'at' not in params
        return json.dumps({'items': [location, outside]}).encode(), 'application/json', 'no-store'
    monkeypatch.setattr(maps, 'here_request', request)
    response = client.get('/api/maps/search', params={'q': ' Łaz '})
    assert response.status_code == 200
    assert response.json()['items'] == [{'id': 'here:sample:laz', 'name': location['title'], 'lat': 51.94944, 'lng': 15.68673}]
    for query in ['', 'a', '   ', 'x' * 121]:
        assert client.get('/api/maps/search', params={'q': query}).status_code == 422


@pytest.mark.parametrize('query,lat,lng',[
    ('Warszawa, Marszałkowska 1',52.219,21.019),
    ('Gdańsk, Długa 1',54.35,18.646),
    ('Zakopane, Krupówki 1',49.296,19.95),
    ('Poznań, Stary Rynek 1',52.408,16.934),
    ('Białystok',53.132,23.168),
])
def test_addresses_outside_lubuskie_are_returned(monkeypatch,query,lat,lng):
    def request(path,params,*,service):
        assert params['q']==query
        return json.dumps({'items':[{'id':'address','title':query,'position':{'lat':lat,'lng':lng},'address':{'countryCode':'POL'}}]}).encode(),'application/json','no-store'
    monkeypatch.setattr(maps,'here_request',request)
    response=client.get('/api/maps/search',params={'q':query})
    assert response.status_code==200
    assert response.json()['items']==[{'id':'address','name':query,'lat':lat,'lng':lng}]


def test_reverse_address_uses_gps_coordinates_and_separate_service(monkeypatch):
    def request(path, params, *, service):
        assert service == 'reverse' and path == 'revgeocode'
        assert params == {'at': '52.4,16.9', 'limit': 1, 'lang': 'pl-PL'}
        item = {'id': 'address', 'title': 'Street', 'address': {'label': 'Poznań, ulica 1'}, 'position': {'lat': 52.4001, 'lng': 16.9001}}
        return json.dumps({'items': [item]}).encode(), 'application/json', 'no-store'
    monkeypatch.setattr(maps, 'here_request', request)
    response = client.get('/api/maps/reverse?lat=52.4&lng=16.9')
    assert response.status_code == 200
    assert response.json()['items'] == [{'id': 'address', 'name': 'Poznań, ulica 1', 'lat': 52.4, 'lng': 16.9}]
    for query in ['lat=91&lng=0', 'lat=0&lng=181', 'lat=nan&lng=0', 'lat=0', 'lat=0&lng=inf']:
        assert client.get('/api/maps/reverse?' + query).status_code == 422


def test_reverse_address_handles_missing_configuration_and_invalid_results(monkeypatch):
    monkeypatch.delenv('HERE_API_KEY', raising=False)
    assert client.get('/api/maps/reverse?lat=52&lng=15').status_code == 503
    monkeypatch.setattr(maps, 'here_request', lambda *args, **kwargs: (b'{"items": []}', 'application/json', 'no-store'))
    assert client.get('/api/maps/reverse?lat=52&lng=15').json()['items'] == []
    monkeypatch.setattr(maps, 'here_request', lambda *args, **kwargs: (b'{"items": [{"position": {"lat": 99, "lng": 15}}]}', 'application/json', 'no-store'))
    assert client.get('/api/maps/reverse?lat=52&lng=15').status_code == 502
