import os
import threading
from uuid import uuid4
import pytest


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_add_region_from_prompt_progress_model_stop_and_restart(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete
    from app.main import app,SessionLocal,User,Region,Place,PromptTask,RegionResearchJob,RegionResearchCandidate,CORE_TYPES
    from app import prompt_tasks,region_research as research
    email='prompt-region-'+uuid4().hex+'@example.com';slug='lubelskie';task_id=None
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    points=research.parse_candidates([{'type':'node','id':987654321,'lat':51.25,'lon':22.56,'tags':{'name':'Test castle for region prompt','historic':'castle'}}],['castle'])
    calls=[]
    monkeypatch.setattr(research,'discover_region',lambda *args,**kwargs:(points,1) if kwargs.get('group')=='castle' else ([],0))
    monkeypatch.setattr(research,'wikidata_entities',lambda ids:{})
    def descriptions(region,items,entities,**kwargs):
        calls.append(kwargs)
        return {p['source_key']:{'verified':True,'description':'Opis potwierdzony w źródle.','subtitle':'Zamek','location':'Lublin','sources':[{'title':'OSM','url':p['source_url']}],'wikidata':'','warning':''} for p in items}
    monkeypatch.setattr(research,'research_batch',descriptions)
    monkeypatch.setattr(research,'obtain_photo',lambda *args:('/api/media/test-region.webp',{'author':'Test','license':'CC BY-SA 4.0','source_url':'https://commons.wikimedia.org/wiki/File:Test.jpg'},''))
    with TestClient(app) as client:
        with SessionLocal() as db:assert db.get(Region,slug) is None
        auth=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Region prompt'}).json()
        headers={'Authorization':'Bearer '+auth['access_token']}
        with SessionLocal() as db:
            db.scalar(select(User).where(User.email==email)).is_superadmin=True;db.commit()
        try:
            assert client.post('/api/admin/prompt-tasks',headers=headers,json={'prompt':'Dodaj województwo'}).status_code==422
            body={'prompt':'Dodaj województwo lubelskie — atrakcje, opisy i zdjęcia','model':'gpt-6.1-terra'}
            saved=client.post('/api/admin/prompt-tasks',headers=headers,json=body)
            assert saved.status_code==201,saved.text
            task=saved.json();task_id=task['id'];url='/api/admin/prompt-tasks/'+task_id
            assert task['task_type']=='region_import' and task['status']=='idle' and task['limit']==25
            assert 'Lubelskie' in task['scope'] and 'noclegi' not in task['fields']
            with SessionLocal() as db:
                assert db.get(Region,slug) is None,'Saving creates only the task, without work or a public region'
                assert set(db.get(PromptTask,task_id).kinds)==set(CORE_TYPES)
            assert calls==[]
            monkeypatch.setenv('REGION_RESEARCH_WORKER','1') # The startup worker remains disabled in this test.
            started=client.post(url+'/start',headers=headers)
            assert started.status_code==200,started.text
            assert started.json()['status']=='queued'
            with SessionLocal() as db:
                job=prompt_tasks.region_job(db.get(PromptTask,task_id),db);job_id=job.id
                assert job.report['manual_budget_limit']==25 and job.report['prompt_model']==body['model']
                assert db.get(Region,slug).active is True
            assert client.post(url+'/start',headers=headers).status_code==409
            research.process_job_step(job_id,threading.Event())
            research.process_job_step(job_id,threading.Event())
            assert calls==[{'selected_model':'gpt-6.1-terra','admin_prompt':body['prompt']}]
            public=client.get('/api/places',params={'region':slug}).json()
            assert len(public)==1 and public[0]['image']=='/api/media/test-region.webp'
            data=client.get('/api/admin/tasks',headers=headers,params={'region':slug}).json()
            row=next(t for t in data['tasks'] if t['id']==task_id)
            assert row['updated']==1 and row['processed']==1 and row['status']=='running'
            assert not any(t['id']=='region' for t in data['tasks']),'Linked progress appears once'
            assert data['archived_count']==0
            stopping=client.post(url+'/stop',headers=headers).json()
            assert stopping['status']=='stopping' and not stopping['can_start']
            research.process_job_step(job_id,threading.Event())
            assert client.post(url+'/start',headers=headers).status_code==200
            assert client.delete(url,headers=headers).status_code==200
            research.process_job_step(job_id,threading.Event())
            assert len(client.get('/api/places',params={'region':slug}).json())==1
            assert client.post('/api/admin/tasks/restore',headers=headers,json={}).status_code==200
            assert client.post(url+'/start',headers=headers).status_code==200
            # Restart stops linked work before the region worker may issue a new AI request.
            prompt_tasks.start_worker()
            with SessionLocal() as db:
                assert prompt_tasks.region_job(db.get(PromptTask,task_id),db).status=='cancelled'
            assert len(calls)==1
            assert client.post(url+'/start',headers=headers).status_code==200
            for _ in range(14):research.process_job_step(job_id,threading.Event())
            with SessionLocal() as db:
                summary=prompt_tasks.summary(db.get(PromptTask,task_id),db)
                assert summary['status']=='completed' and summary['can_start']
            assert len(client.get('/api/places',params={'region':slug}).json())==1
        finally:
            with SessionLocal() as db:
                jobs=select(RegionResearchJob.id).where(RegionResearchJob.region==slug)
                db.execute(delete(RegionResearchCandidate).where(RegionResearchCandidate.job_id.in_(jobs)))
                db.execute(delete(RegionResearchJob).where(RegionResearchJob.region==slug))
                if task_id:db.execute(delete(PromptTask).where(PromptTask.id==task_id))
                db.execute(delete(Place).where(Place.region==slug));db.execute(delete(Region).where(Region.slug==slug))
                db.execute(delete(User).where(User.email==email));db.commit()
