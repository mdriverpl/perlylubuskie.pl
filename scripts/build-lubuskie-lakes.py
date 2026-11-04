"""Build a source-attributed union of OSM/Geofabrik and Wikidata lake records.

Run extract-lubuskie-lakes.py first (osmium + shapely); the builder uses shapely
only for exact province/municipality membership. No OpenAI requests are made.
"""
import hashlib
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path
from shapely.geometry import shape,Point

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.region_research import clean_text
from app.lake_catalog import same_lake,source_keys

SOURCE=ROOT/'.tools/lubuskie-lakes-sources'
OUTPUT=ROOT/'backend/lake-catalogs/lubuskie.json'
NOW=datetime.now(timezone.utc).isoformat()
admin=json.loads((SOURCE/'administrative.json').read_text(encoding='utf-8'))
province=next(shape(p['geometry']) for p in admin if p['iso']=='PL-08')
municipalities=[(p['name'],shape(p['geometry'])) for p in admin if p['level']=='7']
osm=json.loads((SOURCE/'extracted-lakes.json').read_text(encoding='utf-8'))['elements']
wikidata=json.loads((SOURCE/'wikidata.json').read_text(encoding='utf-8'))


def location(lat,lng):
    point=Point(lng,lat)
    return next((name for name,geometry in municipalities if geometry.covers(point)),'Lubuskie')


def record(key,name,lat,lng,sources,license,details):
    loc=location(lat,lng)
    text=f'{name}. Zbiornik wodny w województwie lubuskim. Nazwa i położenie pochodzą z podanych źródeł.'
    if details['lake_catalog'].get('unnamed'):text='Jezioro w województwie lubuskim. W danych źródłowych nie podano nazwy własnej akwenu.'
    return {'research_key':key,'name':name[:200],'subtitle':'Jezioro · '+loc,'location':loc,'region':'lubuskie','category':'nature',
            'description':text,'image':'/images/attraction-placeholder.svg','lat':round(lat,7),'lng':round(lng,7),'rating':0,
            'details':{'kind':'lake','sources':sources,'coordinate_source':sources[0]['url'],'coordinate_license':license,
                       'location_note':'Znacznik wskazuje akwen, nie wyznaczone wejście ani kąpielisko.',
                       'description_license':'Opis katalogowy opracowany na podstawie wskazanych danych.',**details}}


def merge(a,b):
    old=a['details'];new=b['details']
    old['lake_catalog']['source_keys']=sorted(source_keys(a)|source_keys(b))
    old['aliases']=sorted(set([*old.get('aliases',[]),*new.get('aliases',[]),b['name']])-{a['name']})
    sources={s['url']:s for s in old['sources']};sources.update({s['url']:s for s in new['sources']});old['sources']=list(sources.values())
    if new.get('wikidata'):old['wikidata']=new['wikidata']
    if old['lake_catalog'].get('unnamed') and not new['lake_catalog'].get('unnamed'):
        a['name']=b['name'];old['official_name']=b['name'];old['lake_catalog']['unnamed']=False;a['description']=b['description']


records=[]
for item in osm:
    tags=item['tags'];key=f"osm:{item['type']}:{item['id']}";source=f"https://www.openstreetmap.org/{item['type']}/{item['id']}"
    name=clean_text(tags.get('name:pl') or tags.get('name',''))
    aliases=[]
    for field in ('name','name:pl','alt_name','official_name','loc_name'):
        aliases.extend(clean_text(value) for value in tags.get(field,'').split(';') if value.strip())
    qid=tags.get('wikidata','');qid=qid if re.fullmatch(r'Q[1-9][0-9]*',qid) else ''
    bounds=item['bounds'];sources=[{'title':'OpenStreetMap — akwen i jego geometria','url':source}]
    details={'aliases':sorted(set(aliases)),**({'official_name':name} if name else {}),**({'wikidata':qid} if qid else {}),
             'coordinate_accuracy':'osm_water_interior','lake_catalog':{'source_keys':[key]+(['wd:'+qid] if qid else []),
             'bounds':[bounds[k] for k in ('minlon','minlat','maxlon','maxlat')],'unnamed':not bool(name),
             'water_type':tags.get('water','unspecified'),'intermittent':tags.get('intermittent','unknown'),
             'cross_border':item.get('cross_border',False),'imported_at':NOW}}
    # Local aliases and identity corroborated by the official PZW register.
    if key=='osm:way:141626503':
        details['aliases']+=['Liwno','Liwno Wielkie','Liwno Duże','Zabór Duży','Jezioro Liwno (Zabór Duży)']
        sources.append({'title':'PZW — Liwno (Zabór Duży)','url':'https://pzw.pl/strefa-wedkarza/lowiska-i-wody-pzw/liwno-zabor-duzy_zlegKVn54E0s9aw3QA9r'})
    if key=='osm:way:141626526':
        details['aliases']+=['Zabór Mały','Liwno Małe','Jezioro Zabór Mały']
        sources.append({'title':'PZW — Zabór Mały (Liwno Małe)','url':'https://pzw.pl/strefa-wedkarza/lowiska-i-wody-pzw/Zab%C3%B3r%20Ma%C5%82y%20%28Liwno%20Ma%C5%82e%29_TcYI2NdLHefkIW6ACiyj'})
    candidate=record(key,name or 'Jezioro bez nazwy',item['center']['lat'],item['center']['lon'],sources,'OpenStreetMap contributors — ODbL 1.0',details)
    # Overlapping member ways and relations can describe the same water.
    previous=next((p for p in records if same_lake(p,candidate)),None)
    if previous:merge(previous,candidate)
    else:records.append(candidate)

wd_added=wd_linked=wd_outside=0
for item in wikidata:
    candidate=record(item['source_key'],item['name'],item['lat'],item['lng'],[{'title':'Wikidata — dane jeziora','url':item['source_url']}],
                     'Wikidata CC0 1.0',{'official_name':item['name'],'wikidata':item['wikidata'],'coordinate_accuracy':'wikidata_coordinate',
                     'lake_catalog':{'source_keys':[item['source_key']],'unnamed':False,'imported_at':NOW}})
    previous=next((p for p in records if same_lake(p,candidate)),None)
    if previous:merge(previous,candidate);wd_linked+=1
    elif province.covers(Point(item['lng'],item['lat'])):records.append(candidate);wd_added+=1
    else:wd_outside+=1

records.sort(key=lambda p:p['research_key'])
report={'osm_lake_objects':len(osm),'wikidata_lakes':len(wikidata),'wikidata_linked':wd_linked,'wikidata_added':wd_added,
        'wikidata_coordinates_outside_province':wd_outside,'catalog_lakes':len(records),
        'named_lakes':sum(not p['details']['lake_catalog'].get('unnamed') for p in records),
        'unnamed_lakes':sum(bool(p['details']['lake_catalog'].get('unnamed')) for p in records)}
data={'region':'lubuskie','retrieved_at':NOW,'source_extract':'https://download.geofabrik.de/europe/poland/lubuskie-latest.osm.pbf',
      'extract_sha256':hashlib.sha256((SOURCE/'lubuskie-latest.osm.pbf').read_bytes()).hexdigest(),
      'license':'OSM database: ODbL 1.0; Wikidata: CC0 1.0','report':report,'places':records}
OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'public/lakes-lubuskie.json').write_text(OUTPUT.read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
print('Zabor lakes:',[(p['name'],p['location'],p['research_key']) for p in records if p['research_key'] in ('osm:way:141626503','osm:way:141626526')])
