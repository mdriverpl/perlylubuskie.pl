"""Extract OSM water, landcover, roads, buildings and settlements for local static map rendering. Requires osmium and shapely."""
import json,time,math
from pathlib import Path
import osmium
from shapely import wkb
from shapely.geometry import mapping,box
from shapely.strtree import STRtree
root=Path('.tools/lubuskie-lakes-sources')

records=json.loads(Path('backend/lake-catalogs/lubuskie.json').read_text(encoding='utf-8'))['places']
boxes=[]
for record in records:
 bounds=record['details']['lake_catalog'].get('bounds')
 if bounds:
  west,south,east,north=bounds;cx=(west+east)/2;cy=(south+north)/2
  latspan=max((north-south)*1.8,(east-west)*math.cos(math.radians(cy))*1.8/1.5,.006)
  lonspan=latspan*1.5/math.cos(math.radians(cy))
  boxes.append(box(cx-lonspan/2,cy-latspan/2,cx+lonspan/2,cy+latspan/2))
 else:boxes.append(box(record['lng']-.03,record['lat']-.02,record['lng']+.03,record['lat']+.02))
focus=STRtree(boxes)

factory=osmium.geom.WKBFactory();features=[];places=[];t=time.monotonic()
for obj in osmium.FileProcessor(str(root/'lubuskie-latest.osm.pbf')).with_areas().with_filter(osmium.filter.KeyFilter('natural','landuse','leisure','building','highway','place')):
 tags=dict(obj.tags)
 try:
  if obj.is_node():
   if tags.get('place') in ('city','town','village','hamlet') and tags.get('name') and obj.location.valid():places.append({'name':tags['name'],'kind':tags['place'],'lat':obj.lat,'lng':obj.lon})
  elif obj.is_way() and tags.get('highway') and tags['highway'] not in ('proposed','construction'):
   geometry=wkb.loads(factory.create_linestring(obj),hex=True)
   if not geometry.is_empty and len(focus.query(geometry))>0:features.append({'kind':'road','subtype':tags['highway'],'name':tags.get('name',''),'geometry':mapping(geometry.simplify(.000005,preserve_topology=True))})
  elif obj.is_area():
   kind=None;subtype=''
   if tags.get('natural')=='water':kind='water'
   elif tags.get('natural') in ('wood','scrub') or tags.get('landuse') in ('forest','meadow','grass','farmland','orchard','residential','industrial','allotments'):
    kind='land';subtype=tags.get('landuse') or tags.get('natural')
   elif tags.get('leisure') in ('park','garden'):kind='land';subtype='grass'
   elif tags.get('building'):kind='building'
   if kind:
    geometry=wkb.loads(factory.create_multipolygon(obj),hex=True)
    if not geometry.is_valid:geometry=geometry.buffer(0)
    if not geometry.is_empty and len(focus.query(geometry))>0:features.append({'kind':kind,'subtype':subtype,'name':tags.get('name',''),'osm_key':('osm:way:' if obj.from_way() else 'osm:relation:')+str(obj.orig_id()),'geometry':mapping(geometry.simplify(.000005,preserve_topology=True))})
 except Exception:pass
(root/'map-context.json').write_text(json.dumps({'features':features,'places':places},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('Map context:',len(features),'features,',len(places),'settlements,',round(time.monotonic()-t,1),'seconds',flush=True)