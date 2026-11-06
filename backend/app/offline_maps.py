"""Small, user-selected OSM data extracts. No raster tile prefetching."""
import json
import math
import os
import threading
import time
from collections import OrderedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix='/api/maps')
_slots = threading.BoundedSemaphore(2)
_lock = threading.Lock()
_cache = OrderedDict()
MAX_BYTES = 8_000_000
MAX_AREA_KM2 = 25


def validate_bounds(west, south, east, north):
    if not all(math.isfinite(n) for n in (west, south, east, north)) or not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
        raise HTTPException(422, 'Nieprawidłowy obszar mapy.')
    width = (east-west)*111.32*math.cos(math.radians((south+north)/2))
    height = (north-south)*111.32
    if width*height > MAX_AREA_KM2 or max(width, height) > 10:
        raise HTTPException(422, 'Przybliż mapę. Można pobrać do 25 km², o szerokości i wysokości do 10 km.')


def _coordinates(geometry):
    if not isinstance(geometry, list):
        return []
    return [[p['lon'], p['lat']] for p in geometry if isinstance(p, dict) and isinstance(p.get('lon'), (int, float)) and isinstance(p.get('lat'), (int, float)) and math.isfinite(p['lon']) and math.isfinite(p['lat']) and abs(p['lon']) <= 180 and abs(p['lat']) <= 90]


def _rings(parts):
    parts = [p for p in parts if len(p) > 1]
    result = []
    while parts:
        ring = parts.pop()
        while ring[0] != ring[-1]:
            for i, other in enumerate(parts):
                if ring[-1] == other[0]:
                    ring += other[1:]
                elif ring[-1] == other[-1]:
                    ring += other[-2::-1]
                elif ring[0] == other[-1]:
                    ring = other[:-1]+ring
                elif ring[0] == other[0]:
                    ring = other[:0:-1]+ring
                else:
                    continue
                parts.pop(i)
                break
            else:
                break
        if len(ring) >= 4 and ring[0] == ring[-1]:
            result.append(ring)
    return result


def _contains(ring, point):
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def to_geojson(data):
    if not isinstance(data, dict) or not isinstance(data.get('elements'), list) or data.get('remark'):
        raise HTTPException(502, 'Nie udało się pobrać całego fragmentu mapy. Spróbuj ponownie lub wybierz mniejszy obszar.')
    if len(data['elements']) > 30000:
        raise HTTPException(422, 'Ten fragment zawiera zbyt wiele szczegółów. Przybliż mapę.')
    features = []
    for element in data['elements']:
        tags = element.get('tags', {})
        properties = {k: str(v)[:200] for k, v in tags.items() if k in ('name', 'highway', 'waterway', 'natural', 'landuse', 'building', 'railway', 'place', 'leisure', 'amenity', 'tourism')}
        kind = element.get('type')
        geometry = None
        if kind == 'node':
            coords = _coordinates([element])
            if coords:
                geometry = {'type': 'Point', 'coordinates': coords[0]}
        elif kind == 'way':
            coords = _coordinates(element.get('geometry'))
            if len(coords) >= 2:
                area = len(coords) >= 4 and coords[0] == coords[-1] and not tags.get('highway') and (tags.get('building') or tags.get('landuse') or tags.get('natural') in ('water', 'wood', 'scrub', 'wetland', 'grassland') or tags.get('leisure') == 'park')
                geometry = {'type': 'Polygon' if area else 'LineString', 'coordinates': [coords] if area else coords}
        elif kind == 'relation':
            members = element.get('members', [])
            outer = _rings([_coordinates(m.get('geometry')) for m in members if m.get('role') in ('outer', '')])
            inner = _rings([_coordinates(m.get('geometry')) for m in members if m.get('role') == 'inner'])
            if outer:
                geometry = {'type': 'MultiPolygon', 'coordinates': [[ring]+[hole for hole in inner if _contains(ring, hole[0])] for ring in outer]}
        if geometry:
            features.append({'type': 'Feature', 'id': f"{kind}/{element.get('id')}", 'properties': properties, 'geometry': geometry})
    if not features:
        raise HTTPException(422, 'Brak danych mapy dla tego fragmentu. Wybierz obszar lądowy.')
    # Land and water first; paths and labels remain legible above them.
    features.sort(key=lambda f: {'Polygon': 0, 'MultiPolygon': 0, 'LineString': 1, 'Point': 2}[f['geometry']['type']])
    return {'type': 'FeatureCollection', 'features': features}


@router.get('/offline')
def offline_map(west: float = Query(), south: float = Query(), east: float = Query(), north: float = Query()):
    validate_bounds(west, south, east, north)
    key = tuple(round(n, 5) for n in (west, south, east, north))
    with _lock:
        cached = _cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'Pobieranie mapy jest chwilowo zajęte. Spróbuj za chwilę.')
    try:
        bbox = f'{south:.6f},{west:.6f},{north:.6f},{east:.6f}'
        query = f'''[out:json][timeout:30][maxsize:16777216];(
way[highway]({bbox});way[railway]({bbox});way[waterway]({bbox});
way[natural~"^(water|wood|scrub|wetland|grassland)$"]({bbox});way[landuse]({bbox});way[building]({bbox});way[leisure=park]({bbox});
relation[type=multipolygon][natural~"^(water|wood|scrub|wetland|grassland)$"]({bbox});relation[type=multipolygon][landuse]({bbox});
node[place][name]({bbox});node[amenity~"^(drinking_water|shelter|toilets|parking)$"]({bbox});node[tourism][name]({bbox});
);out geom;'''
        endpoint = os.environ.get('OVERPASS_API_URL', 'https://overpass-api.de/api/interpreter')
        request = Request(endpoint, data=urlencode({'data': query}).encode(), headers={'User-Agent': 'PerlyLubuskie/1.0 (+https://perlylubuskie.pl)', 'Content-Type': 'application/x-www-form-urlencoded'})
        with urlopen(request, timeout=40) as upstream:
            raw = upstream.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise HTTPException(422, 'Fragment mapy jest zbyt duży. Przybliż mapę i spróbuj ponownie.')
        collection = to_geojson(json.loads(raw))
        result = {'version': 1, 'bounds': [west, south, east, north], 'map': collection, 'attribution': '© OpenStreetMap contributors · ODbL 1.0'}
        if len(json.dumps(result).encode()) > MAX_BYTES:
            raise HTTPException(422, 'Fragment mapy jest zbyt duży. Przybliż mapę.')
        with _lock:
            _cache[key] = (time.monotonic()+900, result)
            # At most two bounded extracts are retained in server memory.
            while len(_cache) > 2:
                _cache.popitem(last=False)
        return result
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        raise HTTPException(502, 'Nie udało się pobrać fragmentu mapy. Spróbuj ponownie za chwilę.') from None
    finally:
        _slots.release()
