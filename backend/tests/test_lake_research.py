import os
import threading
from copy import deepcopy
from uuid import uuid4
import pytest
from app import region_research as research,prompt_tasks

PROMPT='Dodaj jeziora w województwie lubuskim, opisz czy można tam pływać, czy mogą pływać motorówki, czy jezioro ma plaże'


def test_lake_prompt_targets_lakes_and_requires_sources():
    assert prompt_tasks.region_instruction(PROMPT,None)==('lubuskie',['lake'])
    source='https://official.example/regulamin'
    facts={'swimming':{'status':'yes','explanation':'Tylko wyznaczone kąpielisko.','source_url':source},
           'motorboats':{'status':'no','explanation':'Brak wzmianki.','source_url':'https://invented.example'},
           'beach':{'status':'unknown','explanation':'','source_url':''}}
    result=research.verified_lake_info(facts,{source})
    assert result['swimming']['status']=='yes'
    assert result['motorboats']['status']=='unknown' and result['motorboats']['source_url']==''
    assert result['beach']['status']=='unknown'
    schema=research.strict_schema(research.ResearchBatch.model_json_schema())
    assert 'default' not in schema['$defs']['Description']['properties']['lake_info']


def test_wikidata_lake_discovery_checks_identity_coordinates_and_region(monkeypatch):
    def get(url,params):
        assert url=='https://query.wikidata.org/sparql'
        assert 'PL-08' in params['query'] and 'Q23397' in params['query']
        def row(qid,point):return {'item':{'value':'http://www.wikidata.org/entity/'+qid},'label':{'value':'Jezioro testowe'},'coord':{'value':point}}
        return {'results':{'bindings':[row('Q123','Point(15.3 52.3)'),row('Q123','Point(15.3 52.3)'),row('Q124','Point(100 70)'),row('invalid','Point(15 52)')]}}
    monkeypatch.setattr(research,'get_json',get)
    items,total=research.discover_wikidata_lakes('lubuskie',100)
    assert total==1 and items[0]['source_key']=='wd:Q123' and items[0]['kind']=='lake'


def test_lake_discovery_unions_sources_instead_of_returning_the_first(monkeypatch):
    import httpx
    first={'source_key':'wd:Q123','source_url':'https://www.wikidata.org/wiki/Q123','name':'First','kind':'lake','wikidata':'Q123','tags':{}}
    second={**first,'source_key':'wd:Q124','source_url':'https://www.wikidata.org/wiki/Q124','name':'Second','wikidata':'Q124'}
    monkeypatch.setattr(research,'discover_wikidata_lakes',lambda *args:([first],1))
    monkeypatch.setattr(research,'discover_commons',lambda *args:([second],1))
    monkeypatch.setattr(research.httpx,'get',lambda *args,**kwargs:httpx.Response(200,request=httpx.Request('GET','https://overpass-api.de/api/interpreter'),json={'elements':[{'type':'way','id':12345,'center':{'lat':51.94,'lon':15.72},'tags':{'name':'Jezioro Zabór','natural':'water'}}]}))
    items,total=research.discover_region('lubuskie',['lake'],5000,group='lake')
    assert total==3 and {p['source_key'] for p in items}=={'wd:Q123','wd:Q124','osm:way:12345'}


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_existing_lakes_are_enriched_before_discovery_failure_and_survive_restart(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete
    from app.main import app,SessionLocal,User,Place,PromptTask,RegionResearchJob,RegionResearchCandidate
    email='lakes-'+uuid4().hex+'@example.com';task_id=None;job_id=None;original={};calls=[]
    monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    monkeypatch.setattr(research,'wikidata_entities',lambda ids:{})
    def discovery(*args,**kwargs):raise research.ResearchError('Źródło zewnętrzne nie odpowiedziało.')
    monkeypatch.setattr(research,'discover_region',discovery)
    def describe(region,items,entities,**kwargs):
        calls.append(len(items));assert kwargs['admin_prompt']==PROMPT
        return {p['source_key']:{'verified':True,'description':'Opis jeziora','subtitle':'Jezioro','location':p['location'],
                'sources':[{'title':'Oficjalny regulamin','url':'https://official.example/regulamin'}],
                'wikidata':p['wikidata'],'warning':'','lake_info':research.verified_lake_info({
                'swimming':{'status':'unknown','source_url':'','explanation':''},
                'motorboats':{'status':'no','source_url':'https://official.example/regulamin','explanation':'Zakaz silników spalinowych.'},
                'beach':{'status':'yes','source_url':'https://official.example/regulamin','explanation':'Wyznaczona plaża.'}}, {'https://official.example/regulamin'})} for p in items}
    monkeypatch.setattr(research,'research_batch',describe)
    with TestClient(app) as client:
        auth=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Lakes'}).json()
        headers={'Authorization':'Bearer '+auth['access_token']}
        with SessionLocal() as db:
            db.scalar(select(User).where(User.email==email)).is_superadmin=True
            lakes=db.scalars(select(Place).where(Place.region=='lubuskie',Place.details['kind'].as_string()=='lake')).all()
            assert lakes
            original={p.id:deepcopy(p.details) for p in lakes};descriptions={p.id:p.description for p in lakes};db.commit()
        try:
            created=client.post('/api/admin/prompt-tasks',headers=headers,json={'prompt':PROMPT})
            assert created.status_code==201,created.text
            task_id=created.json()['id'];url='/api/admin/prompt-tasks/'+task_id
            monkeypatch.setenv('REGION_RESEARCH_WORKER','1')
            assert client.post(url+'/start',headers=headers).status_code==200
            with SessionLocal() as db:
                job=prompt_tasks.region_job(db.get(PromptTask,task_id),db);job_id=job.id
                assert job.report['prompt_kinds']==['lake'] and job.report['lake_questions']
            for _ in range(10):research.process_job_step(job_id,threading.Event())
            assert calls and all(size<=2 for size in calls)
            with SessionLocal() as db:
                task=prompt_tasks.summary(db.get(PromptTask,task_id),db)
                assert task['updated']==len(original) and task['status']=='completed'
                for place_id in original:
                    place=db.get(Place,place_id)
                    assert place.details['lake_info']['motorboats']['status']=='no'
                    assert place.details['lake_info']['swimming']['status']=='unknown'
                    assert place.description==descriptions[place_id]
                assert db.get(RegionResearchJob,job_id).report['discovery_errors']
            monkeypatch.setenv('REGION_RESEARCH_WORKER','0')
            with TestClient(app):pass
            with SessionLocal() as db:
                for place_id in original:assert db.get(Place,place_id).details['lake_info']['beach']['status']=='yes'
        finally:
            with SessionLocal() as db:
                if job_id:
                    db.execute(delete(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job_id))
                    db.execute(delete(RegionResearchJob).where(RegionResearchJob.id==job_id))
                if task_id:db.execute(delete(PromptTask).where(PromptTask.id==task_id))
                for place_id,details in original.items():db.get(Place,place_id).details=details
                db.execute(delete(User).where(User.email==email));db.commit()
