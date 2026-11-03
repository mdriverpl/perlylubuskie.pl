import json
import os
import threading
from uuid import uuid4

import httpx
import pytest
from app import contact_research as research


def record(id=1):
    empty={'value':None,'source_url':'','evidence':''}
    return {'place_id':id,'identity_confirmed':True,'accommodation':dict(empty),'restaurant':dict(empty),
            'phone':{'value':'+48 123 456 789','source_url':'https://palace.example/kontakt','evidence':'Recepcja +48 123 456 789'},
            'email':dict(empty),'website':dict(empty),'note':''}


def test_unknown_is_not_no_and_every_field_requires_grounded_evidence():
    data=record()
    data['accommodation']={'value':'yes','source_url':'https://invented.example','evidence':'hotel'}
    result=research.validated_contact(research.ContactRecord(**data),{'https://palace.example/kontakt'})
    assert result['restaurant']['value'] is None
    assert result['accommodation']['value'] is None
    assert result['phone']['value']=='+48 123 456 789'
    data['phone']['evidence']=''
    assert research.validated_contact(research.ContactRecord(**data),{'https://palace.example/kontakt'})['phone']['value'] is None
    data['identity_confirmed']=False
    data['phone']['evidence']='Recepcja +48 123 456 789'
    assert research.validated_contact(research.ContactRecord(**data),{'https://palace.example/kontakt'})['phone']['value'] is None


def test_research_requires_exact_batch_ids_and_provider_citations(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    data=record()
    def post(url,**kwargs):
        payload=kwargs['json']
        assert payload['store'] is False
        assert payload['tool_choice']=='required'
        assert payload['tools']==[{'type':'web_search'}]
        return httpx.Response(200,json={'status':'completed','output':[
            {'type':'web_search_call','action':{'sources':[{'url':'https://palace.example/kontakt'}]}},
            {'type':'message','content':[{'type':'output_text','text':json.dumps({'records':[data]})}]}]})
    monkeypatch.setattr(research.httpx,'post',post)
    assert research.research_contacts([{'id':1}])[1]['phone']['value']=='+48 123 456 789'
    data['place_id']=2
    with pytest.raises(research.ContactError):research.research_contacts([{'id':1}])
    monkeypatch.setattr(research.httpx,'post',lambda *a,**k:httpx.Response(429))
    with pytest.raises(research.ContactError) as error:research.research_contacts([{'id':1}])
    assert error.value.fatal is True


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')
def test_production_worker_checkpoint_restart_seed_preservation_and_permissions(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-that-is-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import text,select,delete
    from app.main import app,engine,SessionLocal,Place,Region,User
    run='test-'+uuid4().hex
    monkeypatch.setenv('CONTACT_RESEARCH_RUN',run)
    with TestClient(app) as client:
        assert client.get('/api/admin/contact-research').status_code in (401,403)
        assert client.post('/api/admin/contact-research/resume').status_code in (401,403)
        with SessionLocal() as db:
            original=db.get(Place,1).details
        try:
            # Isolate this test's queue; use an existing seed ID to check deploy preservation.
            with engine.begin() as db:
                db.execute(text('DELETE FROM place_contact_tasks WHERE run_id=:run'),{'run':run})
                db.execute(text("INSERT INTO place_contact_tasks(run_id,place_id) VALUES (:run,1)"),{'run':run})
            contact=research.validated_contact(research.ContactRecord(**record()),{'https://palace.example/kontakt'})
            monkeypatch.setattr(research,'research_contacts',lambda records:{1:contact})
            assert research.process_batch(run,threading.Event()) is True
            assert research.process_batch(run,threading.Event()) is False
            assert research.progress()['checked']==1
            with SessionLocal() as db:
                place=db.get(Place,1)
                assert place.details['contact']==contact
                assert place.details['kind']==original['kind']
                assert place.details['photo']==original['photo']
            # Same seed refresh performed on every deployment must preserve production contacts.
            with TestClient(app):pass
            with SessionLocal() as db:assert db.get(Place,1).details['contact']==contact
            with engine.begin() as db:
                db.execute(text("UPDATE place_contact_tasks SET status='pending' WHERE run_id=:run AND place_id=1"),{'run':run})
            def fail(records):raise research.ContactError('Limit',fatal=True)
            monkeypatch.setattr(research,'research_contacts',fail)
            research.process_batch(run,threading.Event())
            assert research.progress()['blocked']>0
            # Failure never replaces the last confirmed facts.
            with SessionLocal() as db:assert db.get(Place,1).details['contact']==contact
        finally:
            with SessionLocal() as db:
                db.get(Place,1).details=original
                db.execute(text('DELETE FROM place_contact_tasks WHERE run_id=:run'),{'run':run});db.commit()
