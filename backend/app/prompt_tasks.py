"""Saved administrator instructions, bounded contact research and durable progress."""
import logging
import os
import re
import threading
import unicodedata
from sqlalchemy import select,func,text
from fastapi import HTTPException
from . import contact_research

logger=logging.getLogger('uvicorn.error')
FIELDS={'phone':'numery telefonów','email':'adresy e-mail','website':'strony WWW',
        'accommodation':'noclegi','restaurant':'restauracje','region_import':'atrakcje, opisy i dostępne zdjęcia'}
KINDS={'castle':'Zamki','palace':'Pałace','lake':'Jeziora','beach':'Plaże','nature':'Parki i przyroda',
       'heritage':'Zabytki','leisure':'Atrakcje rodzinne','stay':'Noclegi','food':'Restauracje','vineyard':'Winiarnie'}


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.lower().replace('ł','l')) if not unicodedata.combining(c))


def region_instruction(prompt,region):
    from .main import REGION_NAMES,CORE_TYPES
    value=normalized(prompt)
    if not re.search(r'\b(?:dodaj|dodac|utworz)\b.{0,35}\bwojewodztw',value):return None
    named=[slug for slug in REGION_NAMES if re.search(r'\b'+re.escape(normalized(slug).removesuffix('ie')).replace(r'\-',r'[- ]'),value)]
    if not named and not region:raise HTTPException(422,'Podaj nazwę województwa, np. „Dodaj województwo lubelskie”.')
    if len(named)>1:raise HTTPException(422,'Dodawaj jedno województwo w jednym zadaniu.')
    if named and region and named[0]!=region:raise HTTPException(422,'Województwo w poleceniu nie zgadza się z wybranym zakresem.')
    slug=named[0] if named else region
    if slug not in REGION_NAMES:raise HTTPException(422,'Nie rozpoznano województwa.')
    positive=re.split(r'\b(?:opisz|sprawdz|czy|podaj)\b',re.split(r'\b(?:bez|oprocz)\b',value)[0])[0]
    patterns={'castle':r'\bzam(?:ek|k)','palace':r'\bpalac','lake':r'\bjezior','beach':r'\bplaz',
              'nature':r'\bpark|\bprzyrod','heritage':r'\bzabyt|\bhistor','leisure':r'\brodzinn'}
    kinds=[kind for kind,pattern in patterns.items() if re.search(pattern,positive)] or list(CORE_TYPES)
    return slug,kinds


def region_job(task,db):
    from .main import RegionResearchJob
    return db.scalar(select(RegionResearchJob).where(RegionResearchJob.report['prompt_task_id'].as_string()==task.id).order_by(RegionResearchJob.created_at.desc()).limit(1))


def parse(prompt,region,db):
    from .main import Region,REGION_NAMES
    value=normalized(prompt)
    patterns={'phone':r'telefon|numer[yuow]* kontakt','email':r'e[ -]?mail|\bmail',
              'website':r'\bwww\b|stron[ayęe].{0,15}(internet|oficjal)|witryn',
              'accommodation':r'nocleg|zakwaterowan','restaurant':r'restaurac|gastronom'}
    fields=[field for field,pattern in patterns.items() if re.search(pattern,value)]
    if not fields:
        raise HTTPException(422,'Wpisz np. „Dodaj województwo lubelskie” albo wskaż dane do uzupełnienia: numery telefonów, e-mail, strony WWW, noclegi lub restauracje.')
    kinds=[]
    # The target follows "dla" / "w" / "obiektów". Service words alone describe data, not target categories.
    for kind,pattern in {'castle':r'\bzam(?:ek|k)', 'palace':r'\bpalac','lake':r'\bjezior','beach':r'\bplaz',
                         'nature':r'\bpark|\bprzyrod','heritage':r'\bzabyt',
                         'leisure':r'\batrakcj.{0,12}rodzin','vineyard':r'\bwiniar|\bwinnic',
                         'stay':r'(?:dla|w|obiektow)\s+(?:wszystkich\s+)?(?:hotel|pensjonat|nocleg)',
                         'food':r'(?:dla|w|obiektow)\s+(?:wszystkich\s+)?restaurac'}.items():
        if re.search(pattern,value):kinds.append(kind)
    regions=db.scalars(select(Region)).all()
    if region and not any(r.slug==region for r in regions):raise HTTPException(404,'Nie znaleziono województwa.')
    named=[slug for slug,name in REGION_NAMES.items() if re.search(r'\b'+re.escape(normalized(slug).removesuffix('ie')).replace(r'\-',r'[- ]'),value)]
    if len(named)>1:raise HTTPException(422,'Dla jednego zadania wybierz jedno województwo albo wszystkie w polu zakresu.')
    if named:
        if not any(r.slug==named[0] for r in regions):raise HTTPException(422,'Najpierw dodaj wskazane województwo do bazy.')
        if region and region!=named[0]:raise HTTPException(422,'Województwo w poleceniu nie zgadza się z wybranym zakresem.')
        region=named[0]
    return fields,kinds,region


def has_value(contact,field):
    value=(contact.get(field) or {}).get('value')
    return value is not None and value!=''


def summary(task,db):
    from .main import PromptTaskItem,Region,REGION_NAMES,research_status
    counts=dict(db.execute(select(PromptTaskItem.status,func.count()).where(PromptTaskItem.task_id==task.id).group_by(PromptTaskItem.status)).all())
    updated=db.scalar(select(func.count()).select_from(PromptTaskItem).where(PromptTaskItem.task_id==task.id,PromptTaskItem.updated.is_(True)))
    region=db.get(Region,task.region) if task.region else None
    scope=', '.join(KINDS[k] for k in task.kinds) if task.kinds else 'Wszystkie rodzaje miejsc'
    scope+=' · '+(region.name if region else REGION_NAMES.get(task.region,'Cała Polska'))
    result={'id':task.id,'custom':True,'task_type':'region_import' if 'region_import' in task.fields else 'contacts','name':task.prompt[:180],'prompt':task.prompt,'scope':scope,
            'fields':', '.join(FIELDS[f] for f in task.fields),'agent':'Weryfikacja oficjalnych źródeł',
            'model':task.model,'region':task.region,'paid':True,'status':task.status,'limit':task.limit,
            'total':sum(counts.values()),'processed':counts.get('done',0)+counts.get('failed',0),
            'updated':updated,'failed':counts.get('failed',0),'message':task.message,
            'can_start':task.status not in ('queued','running','completed') and not task.archived,
            'can_stop':task.status in ('queued','running'),'can_change_model':task.status not in ('queued','running')}
    if 'region_import' in task.fields:
        job=region_job(task,db)
        data=research_status(job,db) if job else None
        status=('stopping' if job.cancel_requested and job.status in ('queued','running') else 'paused' if job.status=='cancelled' and not job.cancel_requested else {'cancelled':'stopped'}.get(job.status,job.status)) if job else task.status
        result.update(status=status,total=(data or {}).get('total',0),processed=(data or {}).get('processed',0),
                      updated=(data or {}).get('added',0)+(data or {}).get('updated',0),
                      message=(data or {}).get('error') or ((data or {}).get('report') or {}).get('message') or task.message,
                      can_start=status not in ('queued','running','stopping') and not task.archived,
                      can_stop=status in ('queued','running'),can_change_model=status not in ('queued','running','stopping'))
    return result


def create(db,user_id,prompt,model,region=None):
    from .main import Place,PromptTask,PromptTaskItem
    prompt=prompt.strip()
    if len(prompt)<10:raise HTTPException(422,'Wpisz polecenie zadania.')
    instruction=region_instruction(prompt,region)
    if instruction:
        slug,kinds=instruction
        task=PromptTask(prompt=prompt,model=model,region=slug,kinds=kinds,fields=['region_import'],limit=25,created_by=user_id,
                        status='idle',message='Zapisano zadanie dodania województwa. Kliknij Start.')
        db.add(task);db.commit();return summary(task,db)
    fields,kinds,region=parse(prompt,region,db)
    query=select(Place)
    if region:query=query.where(Place.region==region)
    if kinds:query=query.where(Place.details['kind'].as_string().in_(kinds))
    places=db.scalars(query.order_by(Place.id)).all()
    targets=[p for p in places if any(not has_value((p.details or {}).get('contact') or {},field) for field in fields)]
    task=PromptTask(prompt=prompt,model=model,region=region,kinds=kinds,fields=fields,created_by=user_id,
                    status='idle' if targets else 'completed',message='Zapisano zadanie. Uruchom przyciskiem Start.' if targets else 'Brak obiektów z brakującymi danymi w tym zakresie.')
    db.add(task);db.flush()
    for place in targets:db.add(PromptTaskItem(task_id=task.id,place_id=place.id))
    db.commit()
    return summary(task,db)


def get_task(db,task_id):
    from .main import PromptTask
    task=db.scalar(select(PromptTask).where(PromptTask.id==task_id).with_for_update())
    if not task:raise HTTPException(404,'Nie znaleziono zadania.')
    return task


def command(db,task_id,action):
    from .main import PromptTaskItem
    task=get_task(db,task_id)
    if 'region_import' in task.fields:return command_region(db,task,action)
    if action=='start':
        if task.archived:raise HTTPException(409,'Najpierw przywróć zadanie na listę.')
        if task.status in ('queued','running'):raise HTTPException(409,'Zadanie jest już uruchomione.')
        if os.environ.get('PROMPT_TASK_WORKER','1')=='0':raise HTTPException(409,'Wykonywanie zadań z promptu jest wyłączone na serwerze.')
        if not os.environ.get('OPENAI_API_KEY','').strip():raise HTTPException(503,'Brakuje klucza OpenAI.')
        db.query(PromptTaskItem).filter(PromptTaskItem.task_id==task.id,PromptTaskItem.status.in_(['failed','running'])).update({'status':'pending','message':''})
        pending=db.scalar(select(func.count()).select_from(PromptTaskItem).where(PromptTaskItem.task_id==task.id,PromptTaskItem.status=='pending'))
        if not pending:raise HTTPException(409,'Wszystkie obiekty zostały już sprawdzone.')
        task.status='queued';task.remaining=task.limit;task.message='Oczekuje na wykonanie porcji.'
    else:
        task.status='stopped';task.remaining=0;task.message='Zatrzymano. Gotowe wyniki pozostają w bazie.'
        db.query(PromptTaskItem).filter(PromptTaskItem.task_id==task.id,PromptTaskItem.status=='running').update({'status':'pending'})
        if action=='delete':task.archived=True
    task.run_version+=1
    db.commit()
    return summary(task,db)


def change_model(db,task_id,model):
    task=get_task(db,task_id)
    if not summary(task,db)['can_change_model']:raise HTTPException(409,'Zatrzymaj zadanie przed zmianą modelu.')
    task.model=model;db.commit()
    return summary(task,db)


def command_region(db,task,action):
    from .main import Region,REGION_NAMES,RegionResearchJob,RegionResearchCandidate,Place
    from sqlalchemy.exc import IntegrityError
    job=region_job(task,db)
    if action=='start':
        if task.archived:raise HTTPException(409,'Najpierw przywróć zadanie.')
        if os.environ.get('REGION_RESEARCH_WORKER','1')=='0':raise HTTPException(409,'Zbieranie atrakcji jest wyłączone na serwerze.')
        if not os.environ.get('OPENAI_API_KEY','').strip():raise HTTPException(503,'Brakuje klucza OpenAI.')
        region=db.scalar(select(Region).where(Region.slug==task.region).with_for_update())
        if not region:
            region=Region(slug=task.region,name=REGION_NAMES[task.region],active=True,allowed_types=list(task.kinds));db.add(region);db.flush()
        active=db.scalar(select(RegionResearchJob.id).where(RegionResearchJob.active_region==task.region))
        if active:raise HTTPException(409,'Zbieranie danych dla tego województwa już trwa. Poczekaj na zakończenie albo zatrzymaj jego zadanie.')
        if not set(task.kinds).issubset(set(region.allowed_types)):
            region.allowed_types=list(dict.fromkeys([*region.allowed_types,*task.kinds]))
        if not job or job.status=='completed':
            job=RegionResearchJob(region=task.region,active_region=task.region,created_by=task.created_by,max_places=5000,report={})
            db.add(job)
        elif job.status not in ('cancelled','failed'):
            raise HTTPException(409,'Poczekaj na zatrzymanie poprzedniej porcji.')
        report=job.report or {}
        if job.discovery_done and report.get('discovery_errors'):
            job.discovery_done=False;report={**report,'discovery_cursor':0,'discovery_errors':[]}
        lake_questions='lake' in task.kinds and bool(re.search(r'plyw|motorow|plaz|kapiel',normalized(task.prompt)))
        db.flush()
        if lake_questions:
            from .region_research import catalog_candidate
            queued={row.source_key:row for row in db.scalars(select(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job.id))}
            for place in db.scalars(select(Place).where(Place.region==task.region,Place.details['kind'].as_string()=='lake')):
                payload=catalog_candidate(place)
                if payload['source_key'] not in queued:
                    db.add(RegionResearchCandidate(job_id=job.id,source_key=payload['source_key'],payload=payload))
                elif not report.get('lake_questions'):
                    queued[payload['source_key']].status='pending';queued[payload['source_key']].result={}
            db.flush()
        processed=db.scalar(select(func.count()).select_from(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job.id,RegionResearchCandidate.status!='pending'))
        job.status='queued';job.active_region=task.region;job.cancel_requested=False;job.error=''
        job.report={**report,'prompt_task_id':task.id,'prompt_model':task.model,'admin_prompt':task.prompt,'prompt_kinds':list(task.kinds),
                    'manual_budget_start':processed,'manual_budget_limit':task.limit,'lake_questions':lake_questions,'message':'Wyszukiwanie atrakcji oczekuje na rozpoczęcie.'}
        task.status='idle';task.message='Zbieranie danych zlecono. Postęp jest zapisywany na bieżąco.'
    else:
        if job and job.status in ('queued','running'):job.cancel_requested=True
        task.status='stopped';task.message='Zatrzymano zadanie. Zapisane miejsca pozostają w bazie.'
        if action=='delete':task.archived=True
    task.run_version+=1
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Inne zadanie dla tego województwa zostało już uruchomione.') from None
    return summary(task,db)


def list_tasks(db):
    from .main import PromptTask
    return [summary(task,db) for task in db.scalars(select(PromptTask).where(PromptTask.archived.is_(False)).order_by(PromptTask.created_at.desc()))]


def archived_count(db):
    from .main import PromptTask
    return db.scalar(select(func.count()).select_from(PromptTask).where(PromptTask.archived.is_(True)))


def restore(db):
    from .main import PromptTask
    db.query(PromptTask).filter(PromptTask.archived.is_(True)).update({'archived':False});db.commit()


def process_batch(task_id,event):
    from .main import SessionLocal,PromptTask,PromptTaskItem,Place
    with SessionLocal() as db:
        task=get_task(db,task_id)
        if 'region_import' in task.fields:return False
        if task.archived or task.status not in ('queued','running') or event.is_set():return False
        items=db.scalars(select(PromptTaskItem).where(PromptTaskItem.task_id==task.id,PromptTaskItem.status=='pending').order_by(PromptTaskItem.place_id).limit(min(2,task.remaining))).all()
        if not items:
            task.status='completed' if not db.scalar(select(PromptTaskItem.place_id).where(PromptTaskItem.task_id==task.id,PromptTaskItem.status=='pending').limit(1)) else 'paused'
            task.message='Zakończono sprawdzanie wszystkich obiektów.' if task.status=='completed' else 'Osiągnięto limit porcji. Kliknij Start, aby kontynuować.'
            db.commit();return False
        ids=[item.place_id for item in items];version=task.run_version
        fields,prompt,model=list(task.fields),task.prompt,task.model
        places=db.scalars(select(Place).where(Place.id.in_(ids))).all()
        records=[{'id':p.id,'name':p.name,'location':p.location,'region':p.region,'lat':p.lat,'lng':p.lng,
                  'known_sources':(p.details or {}).get('sources',[]),'wikidata':(p.details or {}).get('wikidata','')} for p in places
                 if any(not has_value((p.details or {}).get('contact') or {},f) for f in fields)]
        for item in items:item.status='running'
        task.status='running';task.message='Sprawdzam: '+', '.join(p.name for p in places)[:900];db.commit()
    try:
        results=contact_research.research_contacts(records,selected_model=model,prompt=prompt,fields=fields) if records else {}
        if event.is_set():return False
        with SessionLocal() as db:
            task=get_task(db,task_id)
            if task.run_version!=version or task.status!='running' or task.archived:return False
            for place_id in ids:
                item=db.get(PromptTaskItem,(task_id,place_id))
                place=db.scalar(select(Place).where(Place.id==place_id).with_for_update())
                contact=dict((place.details or {}).get('contact') or {}) if place else {}
                finding=results.get(place_id) or {};updated=False
                if place:
                    for field in fields:
                        fact=finding.get(field) or {}
                        if not has_value(contact,field) and fact.get('value') is not None and fact.get('source_url'):
                            contact[field]=fact;updated=True
                    if updated:
                        place.details={**(place.details or {}),'contact':contact}
                item.status='done';item.updated=updated;item.message='Uzupełniono dane.' if updated else 'Nie znaleziono potwierdzonych brakujących danych lub dane już uzupełniono.'
            task.remaining=max(0,task.remaining-len(ids));task.message='Zapisano wyniki porcji.';db.commit()
        return True
    except contact_research.ContactError as error:
        fail(task_id,version,str(error))
        return False


def fail(task_id,version,message):
    from .main import SessionLocal,PromptTaskItem
    with SessionLocal() as db:
        task=get_task(db,task_id)
        if task.run_version!=version or task.status not in ('queued','running'):return
        db.query(PromptTaskItem).filter(PromptTaskItem.task_id==task.id,PromptTaskItem.status=='running').update({'status':'failed','message':message[:1000]})
        task.status='blocked';task.message=message[:1000];task.remaining=0;db.commit()


def worker_loop(event):
    from .main import SessionLocal,PromptTask,engine
    while not event.is_set():
        with engine.connect() as lock:
            if lock.scalar(text('SELECT pg_try_advisory_lock(673059382)')):
                try:
                    with SessionLocal() as db:
                        row=db.execute(select(PromptTask.id,PromptTask.run_version).where(PromptTask.status.in_(['queued','running']),PromptTask.archived.is_(False)).order_by(PromptTask.created_at).limit(1)).first()
                    if row:
                        try:process_batch(row.id,event)
                        except Exception as error:
                            logger.error('Prompt task stopped type=%s',type(error).__name__)
                            fail(row.id,row.run_version,'Przerwano sprawdzanie. Sprawdź konfigurację i uruchom ponownie ręcznie.')
                finally:
                    lock.execute(text('SELECT pg_advisory_unlock(673059382)'));lock.commit()
        event.wait(2)


def start_worker():
    from .main import SessionLocal,PromptTask,PromptTaskItem,RegionResearchJob
    event=threading.Event()
    with SessionLocal() as db:
        db.query(RegionResearchJob).filter(RegionResearchJob.status.in_(['queued','running']),RegionResearchJob.report['prompt_task_id'].as_string().is_not(None)).update({'status':'cancelled','cancel_requested':True,'active_region':None},synchronize_session=False)
        db.query(PromptTask).filter(PromptTask.status.in_(['queued','running'])).update({'status':'stopped','remaining':0,'message':'Przerwano podczas restartu serwera. Kliknij Start, aby kontynuować.','run_version':PromptTask.run_version+1})
        db.query(PromptTaskItem).filter(PromptTaskItem.status=='running').update({'status':'pending'});db.commit()
    if os.environ.get('PROMPT_TASK_WORKER','1')!='0':
        threading.Thread(target=worker_loop,args=(event,),daemon=True,name='prompt-tasks').start()
    return event
