"""Durable photo-only catalog enrichment. Uses Commons/OSM, never an AI API."""
import logging
import math
import os
import re
import threading
from datetime import datetime,timezone
from sqlalchemy import select,text
from . import region_research as sources

logger=logging.getLogger('uvicorn.error')


def model():return 'Wikimedia Commons / OpenStreetMap — bez AI'


def _distance(a,b):
    return math.hypot((a['lat']-b['lat'])*111200,(a['lng']-b['lng'])*68000)


def _name_tokens(name):
    generic={'w','we','i','the','hotel','restauracja','pensjonat','winnica','palac','zamek','domki','domek','noclegi','apartamenty','apartament','osrodek','pokoje','goscinne','letniskowe','zajazd','agroturystyka','pod','nad','na'}
    return [word for word in sources.normalized(name).split() if len(word)>=3 and word not in generic and not word.isdigit()]


def _same_named_place(place,page):
    info=(page.get('imageinfo') or [{}])[0];meta=info.get('extmetadata') or {}
    if info.get('mime') not in ('image/jpeg','image/png','image/webp'):return False
    content=sources.normalized(page.get('title','')+' '+sources.clean_text(meta.get('ImageDescription',{}).get('value',''))+' '+meta.get('Categories',{}).get('value',''))
    kind=(place.get('details') or {}).get('kind')
    if kind in ('palace','castle') and not any(word.startswith(('palac','palace','schloss','castle','zamek','zamku','dwor','manor')) for word in content.split()):return False
    tokens=_name_tokens(place['name'])
    if not tokens or not all(any(word==token or len(token)>=6 and word.startswith(token[:6]) for word in content.split()) for token in tokens):return False
    town=sources.normalized(place['location'].split('·')[0])
    locality=bool(town) and all(any(word==token or len(token)>=4 and word.startswith(token[:min(5,len(token))]) for word in content.split()) for token in town.split())
    try:
        point={'lat':float(meta['GPSLatitude']['value']),'lng':float(meta['GPSLongitude']['value'])}
        nearby=_distance(place,point)<=150
    except (KeyError,ValueError,TypeError):nearby=False
    # An unnamed/generic accommodation is never illustrated with a nearby building.
    return locality or nearby


def find_photo(place):
    details=place.get('details') or {};qid=details.get('wikidata','')
    tags={}
    osm=re.fullmatch(r'https://(?:www\.)?openstreetmap\.org/(node|way|relation)/(\d+)/?',details.get('coordinate_source',''))
    if osm:
        data=sources.get_json(f'https://api.openstreetmap.org/api/0.6/{osm[1]}/{osm[2]}.json')
        source=next((e for e in data.get('elements',[]) if str(e.get('id'))==osm[2]),{})
        raw=source.get('tags') or {}
        for key in ('wikimedia_commons','wikidata'):
            if isinstance(raw.get(key),str):tags[key]=raw[key]
        if not qid:qid=tags.get('wikidata','')
    if not re.fullmatch(r'Q[1-9][0-9]*',qid or ''):qid=''
    candidate={'name':place['name'],'lat':place['lat'],'lng':place['lng'],'wikidata':qid,'tags':tags}
    entities=sources.wikidata_entities([qid]) if qid else {}
    image,photo,_=sources.obtain_photo(candidate,{},entities)
    if image:return image,photo,'Powiązany rekord Wikidata / OpenStreetMap'
    tokens=_name_tokens(place['name'])
    if not tokens:return '',None,'Brak jednoznacznej nazwy do przypisania fotografii.'
    town=place['location'].split('·')[0].strip()
    phrase=place['name'].replace('"',' ')[:150]
    query=f'"{phrase}" "{town[:80]}"'
    queries=[query]
    if town and details.get('kind') in ('palace','castle'):queries.append(f'"{town[:80]}" '+('pałac' if details['kind']=='palace' else 'zamek'))
    for query in queries:
        data=sources.get_json('https://commons.wikimedia.org/w/api.php',{'action':'query','generator':'search','gsrsearch':query,'gsrnamespace':6,'gsrlimit':12,'prop':'imageinfo','iiprop':'mime|extmetadata','format':'json'})
        for page in data.get('query',{}).get('pages',{}).values():
            if not _same_named_place(place,page):continue
            photo=sources.commons_photo(page['title'])
            if not photo:continue
            image=sources.store_photo(photo)
            return image,{key:value for key,value in photo.items() if key not in ('download_url','sha1')},'Nazwa i miejscowość / współrzędne potwierdzone w Commons'
    return '',None,'Nie znaleziono fotografii z potwierdzoną tożsamością obiektu, autorem i licencją.'


def ensure_tables():
    from .main import engine
    with engine.begin() as db:
        db.execute(text('''CREATE TABLE IF NOT EXISTS photo_research_runs (
            id VARCHAR(100) PRIMARY KEY,region VARCHAR(40) NOT NULL,status VARCHAR(20) NOT NULL,
            error VARCHAR(500) NOT NULL DEFAULT '',current_name VARCHAR(200) NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())'''))
        db.execute(text('''CREATE TABLE IF NOT EXISTS photo_research_tasks (
            run_id VARCHAR(100) REFERENCES photo_research_runs(id) ON DELETE CASCADE,
            place_id INTEGER REFERENCES places(id) ON DELETE CASCADE,status VARCHAR(20) NOT NULL DEFAULT 'pending',
            message VARCHAR(500) NOT NULL DEFAULT '',PRIMARY KEY(run_id,place_id))'''))


def create_run(region='lubuskie',run_id=None,initialize_only=False):
    from .main import engine
    run_id=run_id or ('photos-'+region)
    with engine.begin() as db:
        exists=db.scalar(text('SELECT id FROM photo_research_runs WHERE id=:id FOR UPDATE'),{'id':run_id})
        if exists and initialize_only:return run_id
        if not exists:db.execute(text("INSERT INTO photo_research_runs(id,region,status) VALUES (:id,:region,'running')"),{'id':run_id,'region':region})
        db.execute(text("INSERT INTO photo_research_tasks(run_id,place_id) SELECT :run,id FROM places WHERE region=:region AND (image LIKE '%placeholder.svg' OR image='') ON CONFLICT DO NOTHING"),{'run':run_id,'region':region})
        if exists:
            db.execute(text("UPDATE photo_research_tasks SET status='pending',message='' WHERE run_id=:run AND status IN ('failed','missing','running')"),{'run':run_id})
            db.execute(text("UPDATE photo_research_runs SET status='running',error='',updated_at=now() WHERE id=:id"),{'id':run_id})
    return run_id


def progress(region='lubuskie'):
    from .main import engine
    with engine.connect() as db:
        run=db.execute(text('SELECT * FROM photo_research_runs WHERE region=:region ORDER BY created_at DESC LIMIT 1'),{'region':region}).mappings().first()
        if not run:return {'status':'idle','region':region,'total':0,'processed':0,'added':0,'missing':0,'failed':0,'model':model(),'tokens':0}
        counts=dict(db.execute(text('SELECT status,count(*) FROM photo_research_tasks WHERE run_id=:run GROUP BY status'),{'run':run['id']}).all())
        return {**dict(run),'total':sum(counts.values()),'processed':sum(v for k,v in counts.items() if k!='pending' and k!='running'),
                'added':counts.get('added',0),'missing':counts.get('missing',0),'failed':counts.get('failed',0),'model':model(),'tokens':0}


def stop_work(region='lubuskie'):
    from .main import engine
    with engine.begin() as db:
        db.execute(text("UPDATE photo_research_runs SET status='stopped',current_name='',updated_at=now() WHERE region=:region AND status='running'"),{'region':region})
        db.execute(text("UPDATE photo_research_tasks SET status='pending' WHERE status='running' AND run_id IN (SELECT id FROM photo_research_runs WHERE region=:region)"),{'region':region})
    return progress(region)


def process_one(run_id):
    from .main import SessionLocal,Place
    with SessionLocal() as db:
        run=db.execute(text('SELECT * FROM photo_research_runs WHERE id=:run'),{'run':run_id}).mappings().first()
        if not run or run['status']!='running':return False
        place_id=db.scalar(text("SELECT t.place_id FROM photo_research_tasks t JOIN places p ON p.id=t.place_id WHERE t.run_id=:run AND t.status='pending' ORDER BY CASE WHEN p.details->>'wikidata' IS NOT NULL THEN 0 ELSE 1 END,t.place_id LIMIT 1"),{'run':run_id})
        if place_id is None:
            db.execute(text("UPDATE photo_research_runs SET status='completed',current_name='',updated_at=now() WHERE id=:run"),{'run':run_id});db.commit()
            state=progress(run['region']);logger.info('Photo research completed region=%s checked=%s added=%s missing=%s failed=%s',run['region'],state['processed'],state['added'],state['missing'],state['failed'])
            return False
        place=db.get(Place,place_id)
        record={key:getattr(place,key) for key in ('id','name','region','location','lat','lng','image','details')}
        db.execute(text("UPDATE photo_research_tasks SET status='running' WHERE run_id=:run AND place_id=:id"),{'run':run_id,'id':place_id})
        db.execute(text('UPDATE photo_research_runs SET current_name=:name,updated_at=now() WHERE id=:run'),{'run':run_id,'name':place.name});db.commit()
    pause=False
    try:
        if not record['image'].endswith('placeholder.svg') and record['image']:
            image,photo,message='',None,'Fotografia została już uzupełniona.';status='added'
        else:
            image,photo,message=find_photo(record);status='added' if image else 'missing'
    except sources.ResearchError as error:
        image,photo,message='',None,str(error);status='failed'
        pause=error.status_code==429
    with SessionLocal() as db:
        state=db.scalar(text('SELECT status FROM photo_research_runs WHERE id=:run FOR UPDATE'),{'run':run_id})
        if state!='running':return False
        place=db.scalar(select(Place).where(Place.id==place_id).with_for_update())
        if image and photo and place and place.image.endswith('placeholder.svg'):
            place.image=image;place.details={**(place.details or {}),'photo':{**photo,'checked_at':datetime.now(timezone.utc).date().isoformat()}}
        db.execute(text('UPDATE photo_research_tasks SET status=:status,message=:message WHERE run_id=:run AND place_id=:id'),{'run':run_id,'id':place_id,'status':status,'message':message[:500]});db.commit()
        if pause:
            db.execute(text("UPDATE photo_research_runs SET status='paused',error='Źródło fotografii zgłosiło limit. Wznów później.',updated_at=now() WHERE id=:run"),{'run':run_id});db.commit()
    counts=progress(record['region'])
    logger.info('Photo research item region=%s place=%s status=%s checked=%s total=%s added=%s missing=%s failed=%s',record['region'],place_id,status,counts['processed'],counts['total'],counts['added'],counts['missing'],counts['failed'])
    return not pause


def worker_loop(stop):
    from .main import engine
    with engine.connect() as lock:
        if not lock.scalar(text('SELECT pg_try_advisory_lock(673059383)')):return
        try:
            with engine.begin() as db:db.execute(text("UPDATE photo_research_tasks SET status='pending' WHERE status='running'"))
            while not stop.is_set():
                with engine.connect() as db:run=db.scalar(text("SELECT id FROM photo_research_runs WHERE status='running' ORDER BY created_at LIMIT 1"))
                if not run:break
                process_one(run);stop.wait(1.5)
        except Exception as error:
            logger.error('Photo research stopped type=%s',type(error).__name__)
            with engine.begin() as db:db.execute(text("UPDATE photo_research_runs SET status='failed',error='Przerwano pobieranie. Możesz wznowić zadanie.' WHERE status='running'"))
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(673059383)'));lock.commit()


def start_worker():
    ensure_tables();stop=threading.Event()
    if os.environ.get('PHOTO_RESEARCH_WORKER','1')=='0':return stop
    run=os.environ.get('PHOTO_RESEARCH_RUN','').strip()
    if run:create_run(os.environ.get('PHOTO_RESEARCH_REGION','lubuskie'),run,initialize_only=True)
    threading.Thread(target=worker_loop,args=(stop,),daemon=True,name='photo-research').start()
    return stop
