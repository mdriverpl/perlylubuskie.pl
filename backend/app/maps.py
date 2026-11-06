"""HERE Raster Tile v3 access without exposing the API key to the browser."""
import json
import os
import threading
import time
import re
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Response, Path, Query

router = APIRouter(prefix='/api/maps')
STYLES = {'map': 'explore.day', 'satellite': 'explore.satellite.day', 'terrain': 'topo.day'}
_slots = threading.BoundedSemaphore(8)
_copyright_lock = threading.Lock()
_copyright_cache = None
_tile_cache = OrderedDict()
_tile_cache_lock = threading.Lock()
_tile_cache_bytes = 0
_TILE_CACHE_MAX_BYTES = 16_000_000
_TILE_CACHE_MAX_ITEMS = 256


def normalize_copyrights(data):
    if isinstance(data.get('base'), list):
        return {style: data['base'] for style in STYLES}
    sources = data['copyrights']
    styles = data['resources']['base']['styles']
    result = {}
    for style, here_style in STYLES.items():
        notices = []
        for group in styles[here_style]:
            for notice in sources[group]:
                notices.append({
                    'label': notice['label'], 'minLevel': notice.get('minLevel', 0), 'maxLevel': notice.get('maxLevel', 20),
                    'boxes': [[b['south'], b['west'], b['north'], b['east']] for b in notice.get('boundingBoxes', [])],
                })
        result[style] = notices
    return result


def here_request(path, params=None, *, service='maps'):
    key = os.environ.get('HERE_API_KEY', '').strip()
    if not key:
        raise HTTPException(503, 'Mapy HERE nie są skonfigurowane.')
    if not _slots.acquire(timeout=5):
        raise HTTPException(503, 'Mapa jest chwilowo zajęta.')
    try:
        base = {'maps': 'https://maps.hereapi.com/v3/', 'geocode': 'https://geocode.search.hereapi.com/v1/', 'reverse': 'https://revgeocode.search.hereapi.com/v1/'}[service]
        url = base + path + '?' + urlencode(dict(params or {}, apiKey=key))
        with urlopen(url, timeout=10) as upstream:
            body = upstream.read(2_000_001)
            if len(body) > 2_000_000:
                raise HTTPException(502, 'Nieprawidłowa odpowiedź mapy HERE.')
            return body, upstream.headers.get_content_type(), upstream.headers.get('Cache-Control', 'no-store')
    except HTTPError as error:
        # Never return upstream error bodies or URLs containing credentials.
        message = 'Klucz HERE nie ma dostępu do map.' if error.code in (401, 403) else 'Mapy HERE są chwilowo niedostępne.'
        raise HTTPException(502, message) from None
    except (URLError, TimeoutError, OSError):
        raise HTTPException(502, 'Nie udało się połączyć z mapami HERE.') from None
    finally:
        _slots.release()


@router.get('/config')
def map_config():
    global _copyright_cache
    if not os.environ.get('HERE_API_KEY', '').strip():
        return {'provider': 'osm', 'copyrights': []}
    with _copyright_lock:
        if not _copyright_cache or time.monotonic() - _copyright_cache[0] > 600:
            # Metadata endpoints can answer even when a key cannot fetch map tiles.
            here_request('base/mc/8/138/84/png', {'style': 'explore.day', 'size': 256})
            body, _, _ = here_request('copyright')
            try:
                notices = normalize_copyrights(json.loads(body))
            except (ValueError, AttributeError, KeyError, TypeError):
                raise HTTPException(502, 'Nieprawidłowe dane dostawców mapy.') from None
            _copyright_cache = (time.monotonic(), notices)
        return {'provider': 'here', 'copyrights': _copyright_cache[1]}


@router.get('/tiles/{style}/{z}/{x}/{y}')
def map_tile(style: str, z: int = Path(ge=0, le=20), x: int = Path(ge=0), y: int = Path(ge=0), roads_only: bool = Query(False)):
    global _tile_cache_bytes
    if style not in STYLES or x >= 2**z or y >= 2**z:
        raise HTTPException(422, 'Nieprawidłowy kafelek mapy.')
    cache_key = (hash(os.environ.get('HERE_API_KEY', '').strip()),style,z,x,y,roads_only)
    now = time.monotonic()
    with _tile_cache_lock:
        cached = _tile_cache.get(cache_key)
        if cached and cached[0] > now:
            _tile_cache.move_to_end(cache_key)
            _,created,body,content_type,cache_control = cached
            return Response(body,media_type=content_type,headers={'Cache-Control':cache_control,'Age':str(int(now-created)),'X-Content-Type-Options':'nosniff'})
        if cached:
            _tile_cache_bytes-=len(cached[2]);del _tile_cache[cache_key]
    image_format = 'jpeg' if style == 'satellite' else 'png'
    params = {'style': STYLES[style], 'size': 256}
    if roads_only:
        params.update(style=STYLES['map'],features='pois:disabled')
    body, content_type, cache_control = here_request(f'base/mc/{z}/{x}/{y}/{image_format}', params)
    if not body or content_type not in ('image/png', 'image/jpeg'):
        raise HTTPException(502, 'Nieprawidłowy format kafelka mapy.')
    max_age = re.search(r'(?:^|,)\s*(?:s-maxage|max-age)\s*=\s*(\d+)',cache_control,re.I)
    if max_age and not re.search(r'(?:no-store|private|no-cache)',cache_control,re.I):
        ttl = min(int(max_age.group(1)),3600)
        if ttl > 0:
            created=time.monotonic()
            with _tile_cache_lock:
                previous=_tile_cache.pop(cache_key,None)
                if previous:_tile_cache_bytes-=len(previous[2])
                _tile_cache[cache_key]=(created+ttl,created,body,content_type,cache_control)
                _tile_cache_bytes+=len(body)
                while _tile_cache_bytes>_TILE_CACHE_MAX_BYTES or len(_tile_cache)>_TILE_CACHE_MAX_ITEMS:
                    _,removed=_tile_cache.popitem(last=False);_tile_cache_bytes-=len(removed[2])
    return Response(body, media_type=content_type, headers={'Cache-Control': cache_control, 'X-Content-Type-Options': 'nosniff'})


@router.get('/search')
def search_location(q: str = Query(min_length=2, max_length=120)):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(422, 'Wpisz co najmniej dwa znaki.')
    body, _, _ = here_request('geocode', {'q': query, 'in': 'countryCode:POL', 'limit': 5, 'lang': 'pl-PL'}, service='geocode')
    try:
        items = json.loads(body)['items']
        results = []
        for item in items:
            address = item.get('address', {})
            lat, lng = item['position']['lat'], item['position']['lng']
            if address.get('countryCode') != 'POL':
                continue
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue
            results.append({'id': item['id'], 'name': item['title'], 'lat': lat, 'lng': lng})
        return {'items': results, 'provider': 'HERE'}
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, 'Nieprawidłowy wynik wyszukiwania HERE.') from None


@router.get('/reverse')
def reverse_location(lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180)):
    body, _, _ = here_request('revgeocode', {'at': f'{lat},{lng}', 'limit': 1, 'lang': 'pl-PL'}, service='reverse')
    try:
        results = []
        for item in json.loads(body)['items'][:1]:
            position = item['position']
            if not (-90 <= position['lat'] <= 90 and -180 <= position['lng'] <= 180):
                raise ValueError('Invalid coordinates')
            results.append({'id': item['id'], 'name': item.get('address', {}).get('label') or item['title'], 'lat': lat, 'lng': lng})
        return {'items': results, 'provider': 'HERE'}
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, 'Nieprawidłowy wynik odczytu adresu HERE.') from None
