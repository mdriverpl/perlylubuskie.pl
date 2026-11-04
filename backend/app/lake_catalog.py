"""Additive, licensed lake catalog imports; never replace researched or manual content."""
import hashlib
import json
import logging
import math
import re
from pathlib import Path
from sqlalchemy import select,func,text
from .region_research import normalized

logger=logging.getLogger('uvicorn.error')


def names(record):
    details=record.get('details') or {}
    values=[record['name'],details.get('official_name',''),*details.get('aliases',[])]
    result=set()
    for value in values:
        for variant in (value,re.sub(r'\([^)]*\)','',value)):
            name=re.sub(r'^(?:jezioro|jeziorko|lake)\s+','',normalized(variant))
            if name:result.add(name)
    return result


def source_keys(record):
    details=record.get('details') or {};keys=set((details.get('lake_catalog') or {}).get('source_keys',[]))
    if record.get('research_key'):keys.add(record['research_key'])
    if details.get('wikidata'):keys.add('wd:'+details['wikidata'])
    return keys


def as_record(place):
    return {'name':place.name,'lat':place.lat,'lng':place.lng,'research_key':place.research_key,'details':place.details}


def contains(bounds,lat,lng):
    return bool(bounds and bounds[0]-.0001<=lng<=bounds[2]+.0001 and bounds[1]-.0001<=lat<=bounds[3]+.0001)


def same_lake(a,b):
    if source_keys(a)&source_keys(b):return True
    am=(a.get('details') or {}).get('lake_catalog') or {};bm=(b.get('details') or {}).get('lake_catalog') or {}
    # Anonymous neighboring waters must never merge just because their labels are equal.
    if am.get('unnamed') or bm.get('unnamed'):
        ab,bb=am.get('bounds'),bm.get('bounds')
        return bool(ab and bb and all(abs(x-y)<.000001 for x,y in zip(ab,bb)))
    if not names(a)&names(b):return False
    if contains(am.get('bounds'),b['lat'],b['lng']) or contains(bm.get('bounds'),a['lat'],a['lng']):return True
    # Different coordinates can mark the same lake; bound this fallback to one kilometre.
    return math.hypot((a['lat']-b['lat'])*111.2,(a['lng']-b['lng'])*68)<1


def validate(record,slug):
    key=record.get('research_key','');details=record.get('details') or {}
    if not re.fullmatch(r'(?:wd:Q[1-9][0-9]*|osm:(?:node|way|relation):[1-9][0-9]*)',key):raise ValueError('Invalid lake source identity')
    if details.get('wikidata') and not re.fullmatch(r'Q[1-9][0-9]*',details['wikidata']):raise ValueError('Invalid Wikidata identity')
    if record.get('region')!=slug or record.get('category')!='nature' or details.get('kind')!='lake':raise ValueError('Invalid lake region/type')
    if not record.get('name') or len(record['name'])>200 or len(record.get('description',''))>2000:raise ValueError('Invalid lake text')
    if not all(isinstance(record.get(k),(float,int)) and math.isfinite(record[k]) for k in ('lat','lng')) or not 49<=record['lat']<=55 or not 14<=record['lng']<=24.2:raise ValueError('Invalid lake coordinates')
    if not details.get('sources') or not details.get('coordinate_license'):raise ValueError('Missing lake attribution')
    if record.get('image')!='/images/attraction-placeholder.svg':raise ValueError('Lake catalog must not introduce unverified photos')


def import_catalogs(directory=None):
    from .main import SessionLocal,Region,Place,REGION_NAMES
    root=Path(directory) if directory else Path(__file__).resolve().parents[1]/'lake-catalogs'
    results=[]
    for path in sorted(root.glob('*.json')):
        raw=path.read_bytes();version=hashlib.sha256(raw).hexdigest();data=json.loads(raw)
        slug=data['region'];records=data['places']
        if slug not in REGION_NAMES:raise ValueError('Unknown lake region')
        for record in records:validate(record,slug)
        with SessionLocal() as db:
            db.execute(text('CREATE TABLE IF NOT EXISTS lake_catalog_imports (catalog VARCHAR(120) PRIMARY KEY,version VARCHAR(64) NOT NULL,imported_at TIMESTAMPTZ NOT NULL DEFAULT now())'))
            if db.scalar(text('SELECT version FROM lake_catalog_imports WHERE catalog=:catalog'),{'catalog':path.name})==version:continue
            region=db.scalar(select(Region).where(Region.slug==slug).with_for_update())
            if not region:raise ValueError('Lake region must already exist')
            if 'lake' not in region.allowed_types:region.allowed_types=[*region.allowed_types,'lake']
            existing=list(db.scalars(select(Place)))
            by_source={key:p for p in existing for key in source_keys(as_record(p))}
            regional=[p for p in existing if p.region==slug and (p.details or {}).get('kind')=='lake']
            added=linked=0
            for record in records:
                previous=next((by_source[key] for key in sorted(source_keys(record)) if key in by_source),None)
                if not previous:previous=next((p for p in regional if same_lake(record,as_record(p))),None)
                if previous:
                    old=previous.details or {};new=record['details']
                    sources={s['url']:s for s in new['sources']};sources.update({s['url']:s for s in old.get('sources',[]) if s.get('url')})
                    old_meta=old.get('lake_catalog') or {};new_meta=new.get('lake_catalog') or {}
                    meta={**new_meta,**old_meta,'source_keys':sorted(source_keys(record)|source_keys(as_record(previous)))}
                    if not old_meta.get('bounds') and new_meta.get('bounds'):meta['bounds']=new_meta['bounds']
                    previous.details={**old,'sources':list(sources.values()),'aliases':sorted(set([*old.get('aliases',[]),*new.get('aliases',[]),record['name']])-{previous.name}),
                                      'lake_catalog':meta,**({'wikidata':new['wikidata']} if not old.get('wikidata') and new.get('wikidata') else {})}
                    if not old.get('admin_managed') and previous.location in ('Lubuskie','województwo lubuskie') and record['location']!='Lubuskie':previous.location=record['location']
                    for key in source_keys(record):by_source[key]=previous
                    linked+=1
                else:
                    place=Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")),**record)
                    db.add(place);regional.append(place);added+=1
                    for key in source_keys(record):by_source[key]=place
            db.execute(text('INSERT INTO lake_catalog_imports(catalog,version) VALUES (:catalog,:version) ON CONFLICT(catalog) DO UPDATE SET version=EXCLUDED.version,imported_at=now()'),{'catalog':path.name,'version':version})
            db.flush()
            total=db.scalar(select(func.count()).select_from(Place).where(Place.region==slug,Place.details['kind'].as_string()=='lake'))
            db.commit()
            result={'region':slug,'added':added,'linked':linked,'total':total};results.append(result)
            logger.info('Lake catalog imported region=%s added=%s linked=%s total=%s',slug,added,linked,total)
    return results
