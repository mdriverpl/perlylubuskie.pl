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
