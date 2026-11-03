import os
import threading
from uuid import uuid4
import pytest


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_prompt_task_lifecycle_bounded_updates_and_stop_race(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete,text
    from app.main import app,SessionLocal,User,Region,Place,PromptTask,PromptTaskItem
    from app import prompt_tasks,contact_research
    email='prompt-'+uuid4().hex+'@example.com';slug='prompt-'+uuid4().hex[:12]
    created_ids=[];calls=[]
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    def provider(records,**kwargs):
        calls.append((records,kwargs))
        return {p['id']:{'phone':{'value':'+48 123 456 789','source_url':'https://example.com/contact'},
                         'website':{'value':'https://example.com/changed','source_url':'https://example.com/contact'}} for p in records}
    monkeypatch.setattr(contact_research,'research_contacts',provider)
    with TestClient(app) as client:
        auth=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Prompt tasks'}).json()
        headers={'Authorization':'Bearer '+auth['access_token']}
        body={'prompt':'Uzupełnij wszystkie numery telefonów dla Zamków','model':'gpt-6.1-terra','region':slug}
        assert client.post('/api/admin/prompt-tasks',json=body).status_code in (401,403)
        assert client.post('/api/admin/prompt-tasks',headers=headers,json=body).status_code==403
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==email));user.is_superadmin=True;db.commit();user_id=user.id
            db.add(Region(slug=slug,name='Test promptów',allowed_types=['castle','palace'],active=True));db.flush()
            for i in range(5):
                place_id=db.scalar(text("SELECT nextval('submitted_place_ids')"));created_ids.append(place_id)
                contact={'email':{'value':'existing@example.com','source_url':'https://example.com/contact'}}
                if i==3:contact['phone']={'value':'+48 987 654 321','source_url':'https://example.com/contact'}
                db.add(Place(id=place_id,name=f'Castle test {i}',subtitle='',category='heritage',image='/keep.webp',lat=52,lng=15,rating=0,location='Test',description='Keep description',region=slug,
                             details={'kind':'palace' if i==4 else 'castle','contact':contact,'photo':{'author':'Existing'}}))
            db.commit()
        task_id=None;race_id=None
        try:
            assert client.post('/api/admin/prompt-tasks',headers=headers,json={**body,'prompt':'Usuń całą bazę danych'}).status_code==422
            assert client.post('/api/admin/prompt-tasks',headers=headers,json={**body,'model':'invalid'}).status_code==422
            response=client.post('/api/admin/prompt-tasks',headers=headers,json=body)
            assert response.status_code==201,response.text
            task=response.json();task_id=task['id'];url='/api/admin/prompt-tasks/'+task_id
            assert task['total']==3 and task['status']=='idle' and task['fields']=='numery telefonów'
            assert calls==[],'Saving/counting must never invoke OpenAI'
            for method,path,payload in [('post',url+'/start',{}),('put',url+'/model',{'model':'gpt-6-luna'}),('delete',url,None)]:
                assert client.request(method,path,json=payload).status_code in (401,403)
            with SessionLocal() as db:db.get(PromptTask,task_id).limit=2;db.commit()
            monkeypatch.setenv('PROMPT_TASK_WORKER','1') # Start endpoint only; TestClient worker was disabled at startup.
            assert client.post(url+'/start',headers=headers).status_code==200
            assert client.post(url+'/start',headers=headers).status_code==409
            assert client.put(url+'/model',headers=headers,json={'model':'gpt-6-astra'}).status_code==409
            prompt_tasks.process_batch(task_id,threading.Event())
            prompt_tasks.process_batch(task_id,threading.Event())
            with SessionLocal() as db:
                state=prompt_tasks.summary(db.get(PromptTask,task_id),db)
                assert state['processed']==2 and state['updated']==2 and state['status']=='paused'
                place=db.get(Place,created_ids[0]);assert place.description=='Keep description' and place.image=='/keep.webp'
                assert place.details['contact']['email']['value']=='existing@example.com'
                assert 'website' not in place.details['contact'],'Only requested fields may be written'
                assert db.get(Place,created_ids[3]).details['contact']['phone']['value']=='+48 987 654 321'
                assert 'phone' not in db.get(Place,created_ids[4]).details['contact'],'Palaces must not enter a castle-only task'
            assert calls[0][1]=={'selected_model':'gpt-6.1-terra','prompt':body['prompt'],'fields':['phone']}
            assert client.post(url+'/start',headers=headers).status_code==200
            prompt_tasks.process_batch(task_id,threading.Event());prompt_tasks.process_batch(task_id,threading.Event())
            with SessionLocal() as db:assert db.get(PromptTask,task_id).status=='completed'
            assert client.delete(url,headers=headers).status_code==200
            assert not any(t['id']==task_id for t in client.get('/api/admin/tasks',headers=headers).json()['tasks'])
            assert client.post('/api/admin/tasks/restore',headers=headers,json={}).status_code==200
            with SessionLocal() as db:assert db.get(PromptTask,task_id).status=='stopped'
            # Stop followed immediately by a new Start must discard the old in-flight response.
            with SessionLocal() as db:
                place=db.get(Place,created_ids[0]);place.details={**place.details,'contact':{'email':{'value':'existing@example.com'}}};db.commit()
            race=client.post('/api/admin/prompt-tasks',headers=headers,json=body).json();race_id=race['id'];race_url='/api/admin/prompt-tasks/'+race_id
            assert client.post(race_url+'/start',headers=headers).status_code==200
            def interrupted(records,**kwargs):
                assert client.post(race_url+'/stop',headers=headers).status_code==200
                assert client.post(race_url+'/start',headers=headers).status_code==200
                return provider(records,**kwargs)
            monkeypatch.setattr(contact_research,'research_contacts',interrupted)
            prompt_tasks.process_batch(race_id,threading.Event())
            with SessionLocal() as db:assert 'phone' not in db.get(Place,created_ids[0]).details['contact']
            assert client.delete(race_url,headers=headers).status_code==200
            monkeypatch.setenv('PROMPT_TASK_WORKER','0')
            prompt_tasks.start_worker()
            assert calls and len(calls)==3
        finally:
            with SessionLocal() as db:
                ids=[key for key in [task_id,race_id] if key]
                db.execute(delete(PromptTaskItem).where(PromptTaskItem.task_id.in_(ids)))
                db.execute(delete(PromptTask).where(PromptTask.id.in_(ids)))
                db.execute(delete(Place).where(Place.id.in_(created_ids)));db.execute(delete(Region).where(Region.slug==slug))
                db.execute(delete(User).where(User.email==email));db.commit()
