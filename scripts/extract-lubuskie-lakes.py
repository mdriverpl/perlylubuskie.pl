"""Extract regional OSM lakes; requires osmium and shapely. Inputs are cached in .tools/lubuskie-lakes-sources."""
import json,re,sys,time
from pathlib import Path
import osmium
from shapely.geometry import Polygon,MultiPolygon,mapping
from shapely import wkb
root=Path('.tools/lubuskie-lakes-sources')
lines=(root/'lubuskie.poly').read_text().splitlines();rings=[];coords=[]
for line in lines[1:]:
 parts=line.split()
 if len(parts)==2:
  try:coords.append(tuple(map(float,parts)))
  except ValueError:pass
 elif line.strip()=='END' and coords:rings.append(Polygon(coords));coords=[]
boundary=MultiPolygon(rings)
factory=osmium.geom.WKBFactory();items=[];administrative=[];start=time.monotonic()
for area in osmium.FileProcessor(str(root/'lubuskie-latest.osm.pbf')).with_areas().with_filter(osmium.filter.EntityFilter(osmium.osm.AREA)):
 tags=dict(area.tags)
 if tags.get('boundary')=='administrative' and (tags.get('ISO3166-2')=='PL-08' or tags.get('admin_level')=='7'):
  try:
   administrative.append({'name':tags.get('name',''),'iso':tags.get('ISO3166-2',''),'id':area.orig_id(),'level':tags.get('admin_level'),'geometry':mapping(wkb.loads(factory.create_multipolygon(area),hex=True))})
  except Exception:pass
 if tags.get('natural')!='water':continue
 name=tags.get('name:pl') or tags.get('name','')
 if tags.get('water')!='lake' and not (re.match(r'(?i)^jezior',name)):continue
 try:
  geometry=wkb.loads(factory.create_multipolygon(area),hex=True)
  if not geometry.is_valid:geometry=geometry.buffer(0)
  clipped=geometry.intersection(boundary)
  if clipped.is_empty or clipped.area<=0:continue
  if not boundary.covers(geometry.centroid) and clipped.area<geometry.area*.1:continue
  point=clipped.representative_point()
  typ='way' if area.from_way() else 'relation'
  items.append({'type':typ,'id':area.orig_id(),'center':{'lat':point.y,'lon':point.x},'bounds':dict(zip(['minlon','minlat','maxlon','maxlat'],geometry.bounds)),'tags':tags,'geometry':mapping(geometry)})
 except Exception as error:print('Geometry skipped',area.orig_id(),type(error).__name__,flush=True)
from shapely.geometry import shape
exact=next(shape(a['geometry']) for a in administrative if a['iso']=='PL-08')
filtered=[]
for item in items:
 geometry=shape(item['geometry']);clipped=geometry.intersection(exact)
 if clipped.is_empty or clipped.area<=0:continue
 point=clipped.representative_point();item['center']={'lat':point.y,'lon':point.x};item['cross_border']=not exact.covers(geometry);filtered.append(item)
items=filtered
(root/'extracted-lakes.json').write_text(json.dumps({'elements':items,'source':'https://download.geofabrik.de/europe/poland/lubuskie-latest.osm.pbf'},ensure_ascii=False),encoding='utf-8')
(root/'administrative.json').write_text(json.dumps(administrative,ensure_ascii=False),encoding='utf-8')
print('Administrative areas:',len(administrative),'province:',any(p['iso']=='PL-08' for p in administrative),flush=True)
print('Extracted lakes:',len(items),'named:',sum(bool(p['tags'].get('name') or p['tags'].get('name:pl')) for p in items),'seconds:',round(time.monotonic()-start,1),flush=True)
print('Zabor IDs:',[(p['type'],p['id']) for p in items if p['id'] in [141626503,141626526,217653701]],flush=True)