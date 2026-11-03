import os
import threading
from uuid import uuid4
import pytest
from app import photo_research,contact_research,region_research


def test_photo_identity_is_not_just_the_nearest_building():
    place={'name':'Pensjonat SAGE','location':'Łagów','lat':52.33,'lng':15.29}
    def page(name,description):return {'title':'File:'+name,'imageinfo':[{'mime':'image/jpeg','extmetadata':{'ImageDescription':{'value':description}}}]}
    assert photo_research._same_named_place(place,page('SAGE.jpg','Pensjonat SAGE w Łagowie'))
    assert not photo_research._same_named_place(place,page('Gate.jpg','Brama Polska w Łagowie'))
    assert not photo_research._same_named_place(place,page('SAGE.jpg','SAGE w Krakowie'))
    assert not photo_research._same_named_place({**place,'name':'Domki letniskowe'},page('Domki.jpg','Domki letniskowe Łagów'))


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_admin_task_permissions_stop_and_photo_persistence(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,text,delete
    from app.main import app,SessionLocal,User,Region,Place,engine
    run='contact-task-'+uuid4().hex
    monkeypatch.setenv('CONTACT_RESEARCH_RUN',run)
    monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    monkeypatch.setenv('CONTACT_RESEARCH_WORKER','1')
    def fake_contact_worker(manual=False):
        contact_research.ensure_run(run)
        if not manual:contact_research.stop_work()
        return threading.Event()
    monkeypatch.setattr(contact_research,'start_worker',fake_contact_worker)
    email='tasks-'+uuid4().hex+'@example.com';slug='opolskie';photo_run='photo-test-'+uuid4().hex
    old=None
    with TestClient(app) as client:
        assert client.get('/api/admin/tasks').status_code in (401,403)
        auth=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Tasks'}).json()
        headers={'Authorization':'Bearer '+auth['access_token']}
        assert client.get('/api/admin/tasks',headers=headers).status_code==403
        with SessionLocal() as db:
            db.scalar(select(User).where(User.email==email)).is_superadmin=True
            if not db.get(Region,slug):db.add(Region(slug=slug,name='Test',allowed_types=['palace'],active=False))
            place=db.get(Place,910001);old={'image':place.image,'details':place.details}
            place.image='/images/attraction-placeholder.svg';place.details={**place.details,'contact':{'website':{'value':'https://example.com'}}};db.commit()
        try:
            data=client.get('/api/admin/tasks',headers=headers).json()
            assert len(data['tasks'])==3 and 'test-only-key' not in str(data)
            assert next(t for t in data['tasks'] if t['id']=='photos')['paid'] is False
            assert next(t for t in data['tasks'] if t['id']=='contacts')['status']=='stopped'
            assert client.post('/api/admin/tasks/region/start',headers=headers,json={'region':slug,'max_places':101}).status_code==422
            assert client.post('/api/admin/tasks/contacts/stop',headers=headers,json={}).status_code==200
            with engine.begin() as db:
                db.execute(text('DELETE FROM place_contact_tasks WHERE run_id=:run'),{'run':run})
                db.execute(text("INSERT INTO place_contact_tasks(run_id,place_id,status) VALUES (:run,910001,'cancelled')"),{'run':run})
            # Stop during a provider call must discard its response and prevent new work.
            def cancelled(records):
                contact_research.stop_work()
                return {910001:{'phone':{'value':'123456789','source_url':'https://example.com'}}}
            monkeypatch.setattr(contact_research,'research_contacts',cancelled)
            with engine.begin() as db:db.execute(text("UPDATE place_contact_tasks SET status='pending' WHERE run_id=:run"),{'run':run})
            contact_research.process_batch(run,threading.Event())
            with SessionLocal() as db:assert 'phone' not in db.get(Place,910001).details['contact']
            photo_research.create_run('lubuskie',photo_run)
            with engine.begin() as db:
                db.execute(text('DELETE FROM photo_research_tasks WHERE run_id=:run AND place_id<>910001'),{'run':photo_run})
            photo={'author':'Test Author','license':'CC BY-SA 4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','source_url':'https://commons.wikimedia.org/wiki/File:Test.jpg'}
            monkeypatch.setattr(photo_research,'find_photo',lambda place:('/api/media/test-photo.webp',photo,'Potwierdzone źródło'))
            assert photo_research.process_one(photo_run)
            with SessionLocal() as db:
                place=db.get(Place,910001)
                assert place.image=='/api/media/test-photo.webp'
                assert place.details['photo']['author']=='Test Author'
                assert place.details['contact']['website']['value']=='https://example.com'
            # Seed refresh during deployment preserves the downloaded photo and contact.
            with TestClient(app):pass
            with SessionLocal() as db:assert db.get(Place,910001).image=='/api/media/test-photo.webp'
            photo_research.stop_work('lubuskie')
            assert not photo_research.process_one(photo_run)
            assert client.post('/api/admin/tasks/photos/stop',headers=headers,json={'region':'lubuskie'}).status_code==200
        finally:
            with SessionLocal() as db:
                db.get(Place,910001).image=old['image'];db.get(Place,910001).details=old['details']
                db.execute(text('DELETE FROM photo_research_runs WHERE id=:run'),{'run':photo_run})
                db.execute(text('DELETE FROM place_contact_tasks WHERE run_id=:run'),{'run':run})
                db.execute(delete(User).where(User.email==email));db.commit()


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_contact_worker_has_a_per_start_budget(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from app.main import app,engine
    from sqlalchemy import text
    run='budget-'+uuid4().hex
    calls=[]
    class FastStop:
        def is_set(self):return False
        def wait(self,seconds):pass
    with TestClient(app):
        contact_research.ensure_run(run)
        monkeypatch.setattr(contact_research,'process_batch',lambda run,stop:(calls.append(run) or True))
        try:
            contact_research.worker_loop(FastStop(),run)
            assert len(calls)*contact_research.BATCH_SIZE==contact_research.MAX_PER_START
        finally:
            with engine.begin() as db:db.execute(text('DELETE FROM place_contact_tasks WHERE run_id=:run'),{'run':run})


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_region_budget_stops_before_an_extra_paid_batch(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete
    from app.main import app,SessionLocal,Region,User,RegionResearchJob,RegionResearchCandidate
    slug='podkarpackie';email='budget-'+uuid4().hex+'@example.com';job_id=None;user_id=None
    calls=[]
    monkeypatch.setattr(region_research,'wikidata_entities',lambda ids:{})
    def summarize(region,points,entities):
        calls.append(len(points))
        return {p['source_key']:{'verified':False,'warning':'Brak potwierdzenia.'} for p in points}
    monkeypatch.setattr(region_research,'research_batch',summarize)
    with TestClient(app):
        try:
            with SessionLocal() as db:
                if not db.get(Region,slug):db.add(Region(slug=slug,name='Budget',allowed_types=['castle'],active=False))
                user=User(email=email,name='Budget',password='not-a-login-hash');db.add(user);db.flush();user_id=user.id
                job=RegionResearchJob(region=slug,active_region=slug,created_by=user.id,status='queued',discovery_done=True,max_places=100,discovered=5,report={'manual_budget_start':0,'manual_budget_limit':3});db.add(job);db.flush();job_id=job.id
                for index in range(5):
                    payload={'source_key':f'osm:node:{index+1}','name':'Budget castle','lat':52.1,'lng':15.2,'wikidata':'','kind':'castle','tags':{}}
                    db.add(RegionResearchCandidate(job_id=job.id,source_key=payload['source_key'],payload=payload))
                db.commit()
            region_research.process_job_step(job_id,threading.Event())
            region_research.process_job_step(job_id,threading.Event())
            assert calls==[3],'A partial final batch must not exceed the per-Start budget'
            with SessionLocal() as db:assert db.get(RegionResearchJob,job_id).status=='cancelled'
        finally:
            with SessionLocal() as db:
                if job_id:
                    db.execute(delete(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job_id));db.execute(delete(RegionResearchJob).where(RegionResearchJob.id==job_id))
                if user_id:db.execute(delete(User).where(User.id==user_id))
                db.commit()


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_model_choices_persist_are_authorized_and_do_not_start_work(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete
    from app.main import app,SessionLocal,User,Region,RegionResearchJob,engine
    from app import task_models,ai_routes
    email='models-'+uuid4().hex+'@example.com'
    started=[]
    monkeypatch.setattr(contact_research,'start_worker',lambda **kwargs:(started.append('contacts') or threading.Event()))
    monkeypatch.setattr(region_research,'start_worker',lambda:threading.Event())
    monkeypatch.setattr(photo_research,'start_worker',lambda:threading.Event())
    monkeypatch.setattr(contact_research,'progress',lambda:{'status':'stopped','run':'test','checked':0,'total':1,'failed':0,'error':''})
    with TestClient(app) as client:
        started.clear()
        with engine.connect() as db:old=[dict(row) for row in db.execute(select(task_models.settings)).mappings()]
        auth=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Model test'}).json()
        headers={'Authorization':'Bearer '+auth['access_token']}
        url='/api/admin/tasks/contacts/model'
        assert client.put(url,json={'model':'gpt-6-luna'}).status_code in (401,403)
        assert client.put(url,headers=headers,json={'model':'gpt-6-luna'}).status_code==403
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==email));user.is_superadmin=True;user_id=user.id;db.commit()
        job_id=None
        try:
            assert client.put(url,headers=headers,json={'model':'unknown-model'}).status_code==422
            assert client.put('/api/admin/tasks/photos/model',headers=headers,json={'model':'gpt-6-luna'}).status_code==422
            for kind,selected in [('contacts','gpt-6.1-sol'),('region','gpt-6.1-terra'),('planner','gpt-6-luna')]:
                result=client.put(f'/api/admin/tasks/{kind}/model',headers=headers,json={'model':selected})
                assert result.status_code==200,result.text
            task_models.initialize(engine) # Simulate a fresh settings reader after restart.
            assert contact_research.model()=='gpt-6.1-sol'
            assert region_research.model()=='gpt-6.1-terra'
            assert ai_routes.model()=='gpt-6-luna'
            data=client.get('/api/admin/tasks',headers=headers).json()
            assert len(data['model_options'])==4 and data['planner']['model']=='gpt-6-luna'
            monkeypatch.setattr(contact_research,'progress',lambda:{'status':'running'})
            assert client.put(url,headers=headers,json={'model':'gpt-6-astra'}).status_code==409
            assert contact_research.model()=='gpt-6.1-sol'
            with SessionLocal() as db:
                job=RegionResearchJob(region='lubuskie',active_region='lubuskie',created_by=user_id,status='queued',max_places=25)
                db.add(job);db.flush();job_id=job.id;db.commit()
            assert client.put('/api/admin/tasks/region/model',headers=headers,json={'model':'gpt-6-astra'}).status_code==409
            assert region_research.model()=='gpt-6.1-terra'
            assert started==[],'Saving or reading model choices must never start a paid worker'
        finally:
            with engine.begin() as db:
                db.execute(delete(task_models.settings))
                if old:db.execute(task_models.settings.insert(),old)
            with SessionLocal() as db:
                if job_id:db.execute(delete(RegionResearchJob).where(RegionResearchJob.id==job_id))
                db.execute(delete(User).where(User.email==email));db.commit()


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_published_region_restart_remove_restore_and_preserve_places(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete,func
    from app.main import app,SessionLocal,User,Place,RegionResearchJob,RegionResearchCandidate,engine
    from app import task_models
    email='task-remove-'+uuid4().hex+'@example.com';slug='dolnoslaskie'
    monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    job_id=None
    with TestClient(app) as client:
        with engine.connect() as db:old=[dict(row) for row in db.execute(select(task_models.archived)).mappings()]
        auth=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Tasks'}).json()
        headers={'Authorization':'Bearer '+auth['access_token']};payload={'region':slug}
        url='/api/admin/tasks/region'
        assert client.request('DELETE',url,json=payload).status_code in (401,403)
        assert client.request('DELETE',url,headers=headers,json=payload).status_code==403
        assert client.post('/api/admin/tasks/restore',headers=headers,json=payload).status_code==403
        with SessionLocal() as db:
            db.scalar(select(User).where(User.email==email)).is_superadmin=True
            count=db.scalar(select(func.count()).select_from(Place));db.commit()
        try:
            client.post('/api/admin/tasks/restore',headers=headers,json=payload)
            row=next(t for t in client.get('/api/admin/tasks',headers=headers,params={'region':slug}).json()['tasks'] if t['id']=='region')
            assert row['can_start'] and row['status']!='published'
            result=client.post(url+'/start',headers=headers,json=payload)
            assert result.status_code==200,result.text
            job_id=result.json()['id']
            assert client.post(url+'/start',headers=headers,json=payload).status_code==409
            assert client.request('DELETE',url,headers=headers,json=payload).status_code==200
            region_research.process_job_step(job_id,threading.Event())
            task_models.initialize(engine)
            data=client.get('/api/admin/tasks',headers=headers,params={'region':slug}).json()
            assert not any(t['id']=='region' for t in data['tasks']) and data['archived_count']==1
            assert client.post('/api/admin/tasks/restore',headers=headers,json=payload).status_code==200
            data=client.get('/api/admin/tasks',headers=headers,params={'region':slug}).json()
            row=next(t for t in data['tasks'] if t['id']=='region')
            assert row['status']=='cancelled' and row['can_start']
            with SessionLocal() as db:
                assert db.scalar(select(func.count()).select_from(Place))==count
                assert db.get(RegionResearchJob,job_id).cancel_requested
            assert client.post(url+'/start',headers=headers,json=payload).status_code==200
            assert client.post(url+'/stop',headers=headers,json=payload).status_code==200
            region_research.process_job_step(job_id,threading.Event())
        finally:
            with engine.begin() as db:
                db.execute(delete(task_models.archived))
                if old:db.execute(task_models.archived.insert(),old)
            with SessionLocal() as db:
                if job_id:
                    db.execute(delete(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job_id))
                    db.execute(delete(RegionResearchJob).where(RegionResearchJob.id==job_id))
                db.execute(delete(User).where(User.email==email));db.commit()
