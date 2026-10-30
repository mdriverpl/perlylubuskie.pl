"""HERE Raster Tile v3 access without exposing the API key to the browser."""
import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Response, Path, Query

router = APIRouter(prefix='/api/maps')
STYLES = {'map': 'explore.day', 'satellite': 'explore.satellite.day', 'terrain': 'topo.day'}
_slots = threading.BoundedSemaphore(8)
_copyright_lock = threading.Lock()
_copyright_cache = None


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
    if not _slots.acquire(blocking=False):
        raise HTTPException(503, 'Mapa jest chwilowo zajęta.')
    try:
        base = {'maps': 'https://maps.hereapi.com/v3/', 'geocode': 'https://geocode.search.hereapi.com/v1/'}[service]
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
def map_tile(style: str, z: int = Path(ge=0, le=20), x: int = Path(ge=0), y: int = Path(ge=0)):
    if style not in STYLES or x >= 2**z or y >= 2**z:
        raise HTTPException(422, 'Nieprawidłowy kafelek mapy.')
    image_format = 'jpeg' if style == 'satellite' else 'png'
    body, content_type, cache_control = here_request(f'base/mc/{z}/{x}/{y}/{image_format}', {'style': STYLES[style], 'size': 256})
    if content_type not in ('image/png', 'image/jpeg'):
        raise HTTPException(502, 'Nieprawidłowy format kafelka mapy.')
    return Response(body, media_type=content_type, headers={'Cache-Control': cache_control, 'X-Content-Type-Options': 'nosniff'})


@router.get('/search')
def search_location(q: str = Query(min_length=2, max_length=120)):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(422, 'Wpisz co najmniej dwa znaki.')
    body, _, _ = here_request('geocode', {'q': query + ', lubuskie', 'in': 'countryCode:POL', 'at': '52.15,15.16', 'limit': 5, 'lang': 'pl-PL'}, service='geocode')
    try:
        items = json.loads(body)['items']
        results = []
        for item in items:
            address = item.get('address', {})
            state = address.get('state', '').lower()
            lat, lng = item['position']['lat'], item['position']['lng']
            if address.get('countryCode') != 'POL' or not ('lubusk' in state or 'lubusz' in state):
                continue
            if not (51.3 <= lat <= 53.1 and 14.4 <= lng <= 16.5):
                continue
            results.append({'id': item['id'], 'name': item['title'], 'lat': lat, 'lng': lng})
        return {'items': results, 'provider': 'HERE'}
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, 'Nieprawidłowy wynik wyszukiwania HERE.') from None
