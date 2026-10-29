import io
import json
from urllib.error import URLError, HTTPError
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import pytest
from fastapi import HTTPException
from app import routing

POINTS = [{'name': 'A & <B>', 'lat': 52.3347, 'lng': 15.2922}, {'name': 'Lake', 'lat': 52.3511, 'lng': 15.2973}]


@pytest.fixture(autouse=True)
def clear_cache():
    routing._cache.clear()


def response():
    return {'features': [{'geometry': {'type': 'LineString', 'coordinates': [[15.2922, 52.3347, 100], [15.293, 52.34, 110], [15.2973, 52.3511, 102]]}, 'properties': {'track-length': '2800', 'total-time': '2000'}}]}


@pytest.mark.parametrize(('transport', 'profile'), [('walk', 'hiking-mountain'), ('bike', 'trekking')])
def test_profiles_metrics_and_cache(monkeypatch, transport, profile):
    calls = []
    def fake_open(url, timeout):
        calls.append(parse_qs(urlparse(url).query))
        return io.BytesIO(json.dumps(response()).encode())
    monkeypatch.setattr(routing, 'urlopen', fake_open)
    result = routing.calculate_route(POINTS, transport)
    assert result['distance_m'] == 2800
    assert result['duration_s'] == 2000
    assert len(result['geometry']['coordinates']) == 3
    assert calls[0]['profile'] == [profile]
    assert calls[0]['lonlats'] == ['15.2922,52.3347|15.2973,52.3511']
    assert routing.calculate_route(POINTS, transport) == result
    assert len(calls) == 1


def test_gpx_exports_track_and_escaped_names():
    xml = ElementTree.fromstring(routing.route_gpx('Test <&>', POINTS, {'geometry': response()['features'][0]['geometry']}))
    ns = {'g': 'http://www.topografix.com/GPX/1/1'}
    assert xml.find('g:trk/g:name', ns).text == 'Test <&>'
    assert len(xml.findall('g:trk/g:trkseg/g:trkpt', ns)) == 3
    assert xml.find('g:wpt/g:name', ns).text == 'A & <B>'
    assert xml.find('g:trk/g:trkseg/g:trkpt/g:ele', ns).text == '100'


@pytest.mark.parametrize(('error', 'code'), [(URLError('offline'), 503), (HTTPError('http://router', 400, 'no path', {}, None), 422)])
def test_unavailable_or_no_path(monkeypatch, error, code):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(routing, 'urlopen', fail)
    with pytest.raises(HTTPException) as exc:
        routing.calculate_route(POINTS, 'walk')
    assert exc.value.status_code == code


def test_invalid_geometry_rejected(monkeypatch):
    data = response()
    data['features'][0]['geometry']['coordinates'][0][0] = float('nan')
    monkeypatch.setattr(routing, 'urlopen', lambda *a, **k: io.BytesIO(json.dumps(data).encode()))
    with pytest.raises(HTTPException) as exc:
        routing.calculate_route(POINTS, 'bike')
    assert exc.value.status_code == 502


@pytest.mark.parametrize(('points', 'mode'), [([], 'bike'), (POINTS, 'car'), ([{**POINTS[0], 'lat': 60}, POINTS[1]], 'walk')])
def test_request_limits(points, mode):
    with pytest.raises(HTTPException) as exc:
        routing.calculate_route(points, mode)
    assert exc.value.status_code == 422
