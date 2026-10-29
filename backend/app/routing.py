"""Bounded, cached access to our private BRouter instance (OSM western Poland)."""
import json
import math
import os
import threading
import time
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import HTTPException

ROUTER_URL = os.environ.get('ROUTER_URL', 'http://router:17777/brouter')
PROFILES = {'bike': 'trekking', 'walk': 'hiking-mountain'}
_cache = OrderedDict()
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(2)


def calculate_route(points, transport):
    if transport not in PROFILES:
        raise HTTPException(422, 'Wyznaczanie przebiegu jest dostępne dla roweru i pieszych.')
    if len(points) < 2 or len(points) > 20:
        raise HTTPException(422, 'Wybierz od 2 do 20 punktów trasy.')
    if any(not (14 <= p['lng'] <= 17 and 50.5 <= p['lat'] <= 53.5) for p in points):
        raise HTTPException(422, 'Punkt jest poza obsługiwanym obszarem zachodniej Polski.')
    key = (transport, tuple((round(p['lng'], 6), round(p['lat'], 6)) for p in points))
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < 3600:
            _cache.move_to_end(key)
            return cached[1]
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'Trwa wyznaczanie innych tras. Spróbuj ponownie za chwilę.')
    try:
        query = urlencode({'lonlats': '|'.join(f"{p['lng']},{p['lat']}" for p in points), 'profile': PROFILES[transport], 'alternativeidx': 0, 'format': 'geojson'})
        try:
            with urlopen(ROUTER_URL + '?' + query, timeout=40) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('Response too large')
            data = json.loads(raw)
            feature = data['features'][0]
            geometry = feature['geometry']
            coordinates = geometry['coordinates']
            properties = feature['properties']
            distance = float(properties['track-length'])
            duration = float(properties['total-time'])
            if geometry['type'] != 'LineString' or len(coordinates) < 2 or len(coordinates) > 100_000:
                raise ValueError('Invalid geometry')
            if not math.isfinite(distance) or not math.isfinite(duration) or distance <= 0 or duration <= 0:
                raise ValueError('Invalid metrics')
            if any(len(p) < 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in p[:2]) or not (-180 <= p[0] <= 180 and -90 <= p[1] <= 90) for p in coordinates):
                raise ValueError('Invalid coordinates')
        except HTTPError as error:
            if error.code in (400, 404, 422):
                raise HTTPException(422, 'Nie znaleziono przejezdnego połączenia. Zmień punkty lub typ trasy.') from error
            raise HTTPException(503, 'Silnik trasowania jest chwilowo niedostępny. Spróbuj ponownie.') from error
        except (URLError, TimeoutError, OSError) as error:
            raise HTTPException(503, 'Silnik trasowania nie odpowiada. Spróbuj ponownie za chwilę.') from error
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise HTTPException(502, 'Silnik trasowania zwrócił nieprawidłową trasę. Zmień punkty i spróbuj ponownie.') from error
        result = {'geometry': geometry, 'distance_m': distance, 'duration_s': duration, 'transport': transport, 'provider': 'BRouter', 'attribution': '© OpenStreetMap contributors'}
        with _lock:
            _cache[key] = (time.monotonic(), result)
            _cache.move_to_end(key)
            while len(_cache) > 32 or sum(len(item[1]['geometry']['coordinates']) for item in _cache.values()) > 100_000:
                _cache.popitem(last=False)
        return result
    finally:
        _slots.release()


def route_gpx(name, places, result):
    root = Element('gpx', version='1.1', creator='Perły Ziemi Lubuskiej', xmlns='http://www.topografix.com/GPX/1/1')
    metadata = SubElement(root, 'metadata')
    SubElement(metadata, 'desc').text = 'Trasa wyznaczona przez BRouter na danych OpenStreetMap. Sprawdź warunki w terenie.'
    for place in places:
        waypoint = SubElement(root, 'wpt', lat=str(place['lat']), lon=str(place['lng']))
        SubElement(waypoint, 'name').text = place['name']
    track = SubElement(root, 'trk')
    SubElement(track, 'name').text = name
    segment = SubElement(track, 'trkseg')
    for point in result['geometry']['coordinates']:
        item = SubElement(segment, 'trkpt', lat=str(point[1]), lon=str(point[0]))
        if len(point) > 2 and isinstance(point[2], (int, float)) and math.isfinite(point[2]):
            SubElement(item, 'ele').text = str(point[2])
    return tostring(root, encoding='utf-8', xml_declaration=True)
