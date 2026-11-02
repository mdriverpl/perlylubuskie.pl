import io
import json
import os
import threading
from uuid import uuid4

import httpx
import pytest
from PIL import Image
from app import region_research as research


def candidate(id=1,**tags):
    return research.parse_candidates([{'type':'node','id':id,'lat':53.01,'lon':18.60,'tags':{'name':'Test castle','historic':'castle',**tags}}],['castle'])[0]


def description(point,verified=True):
    return {'source_key':point['source_key'],'subtitle':'Krótki opis','description':'Opis potwierdzony w źródłach.','location':'Toruń','sources':[{'title':'OSM','url':point['source_url']}],'wikidata':'','verified':verified,'warning':'' if verified else 'Wymaga weryfikacji'}


def test_candidates_categories_coordinates_and_duplicates():
    point={'type':'node','id':1,'lat':53,'lon':18,'tags':{'name':'Zamek','historic':'castle','wikidata':'Q123'}}
    data=research.parse_candidates([point,{**point,'id':2},{**point,'lat':60},{**point,'id':3,'tags':{**point['tags'],'tourism':'hotel'}},{**point,'id':4,'tags':{**point['tags'],'amenity':'restaurant'}}],['castle'])
    assert len(data)==1
    assert data[0]['source_key']=='wd:Q123'
    assert research.classify({'name':'Winiarnia','craft':'winery','historic':'building'}) is None
    assert research.classify({'name':'Jezioro Test','natural':'water'})=='lake'


def test_ai_requires_grounded_citations_and_exact_ids(monkeypatch):
    point=candidate();result=description(point)
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    result['sources']=[{'title':'Invented','url':'https://invented.example/not-searched'}]
    def post(url,**kwargs):
        payload=kwargs['json']
        assert payload['tools']==[{'type':'web_search'}]
        assert payload['tool_choice']=='required'
        assert payload['store'] is False
        return httpx.Response(200,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'records':[result]})}]}]})
    monkeypatch.setattr(research.httpx,'post',post)
    assert research.research_batch('Kujawsko-pomorskie',[point],{})[point['source_key']]['verified'] is False
    result['sources']=[{'title':'OSM','url':point['source_url']}]
    assert research.research_batch('Kujawsko-pomorskie',[point],{})[point['source_key']]['verified'] is True
    result['source_key']='osm:node:999'
    with pytest.raises(research.ResearchError):research.research_batch('Region',[point],{})


def test_photo_licensing_hosts_and_real_image_storage(monkeypatch,tmp_path):
    metadata={'LicenseShortName':{'value':'CC BY-SA 4.0'},'LicenseUrl':{'value':'https://creativecommons.org/licenses/by-sa/4.0/'},'Artist':{'value':'<b>Autor</b>'}}
    info={'mime':'image/jpeg','thumburl':'https://upload.wikimedia.org/test.jpg','descriptionurl':'https://commons.wikimedia.org/wiki/File:Test.jpg','sha1':'abc','extmetadata':metadata}
    monkeypatch.setattr(research,'get_json',lambda *args,**kwargs:{'query':{'pages':{'1':{'imageinfo':[info]}}}})
    photo=research.commons_photo('Test.jpg');assert photo['author']=='Autor'
    metadata['LicenseShortName']['value']='All rights reserved'
    assert research.commons_photo('Test.jpg') is None
    metadata['LicenseShortName']['value']='CC BY-SA 4.0';info['thumburl']='https://untrusted.example/test.jpg'
    assert research.commons_photo('Test.jpg') is None
    output=io.BytesIO();Image.new('RGB',(20,10),'green').save(output,format='JPEG')
    class Download:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        status_code=200
        def raise_for_status(self):pass
        def iter_bytes(self):yield output.getvalue()
    monkeypatch.setattr(research.httpx,'stream',lambda *args,**kwargs:Download())
    monkeypatch.setenv('CATALOG_MEDIA_ROOT',str(tmp_path))
    path=research.store_photo(photo)
    assert path.startswith('/api/media/')
    with Image.open(tmp_path/path.rsplit('/',1)[-1]) as image:assert image.format=='WEBP' and image.size==(20,10)
    with pytest.raises(research.ResearchError):research.store_photo({**photo,'source_url':photo['source_url']+'other','download_url':'http://127.0.0.1/private'})


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_durable_job_permissions_resume_dedupe_and_publication(monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-that-is-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete
    from app.main import app,SessionLocal,User,Place,Region,RegionResearchJob,RegionResearchCandidate
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    slug='kujawsko-pomorskie';path='/api/admin/regions/'+slug+'/research';email=f'research-{uuid4().hex}@example.com'
    points=[candidate(1),candidate(2,name='Second castle'),candidate(3,name='Unverified castle')]
    monkeypatch.setattr(research,'discover_region',lambda *args:(points,3))
    monkeypatch.setattr(research,'wikidata_entities',lambda ids:{})
    calls=[]
    def summarize(region,items,entities):
        calls.append(len(items));return {point['source_key']:description(point,point['name']!='Unverified castle') for point in items}
    monkeypatch.setattr(research,'research_batch',summarize)
    saved_during_batch=[]
    def photo(*args):
        with SessionLocal() as db:saved_during_batch.append(len(db.scalars(select(Place).where(Place.region==slug)).all()))
        return '',None,'Brak zdjęcia'
    monkeypatch.setattr(research,'obtain_photo',photo)
    with TestClient(app) as client:
        response=client.post('/api/auth/register',json={'email':email,'name':'Test','password':'research-test-password-123'})
        headers={'Authorization':'Bearer '+response.json()['access_token']}
        try:
            assert client.get(path).status_code in (401,403)
            assert client.post(path,headers=headers,json={}).status_code==403
            with SessionLocal() as db:
                db.scalar(select(User).where(User.email==email)).is_superadmin=True;db.commit()
            assert client.post('/api/admin/regions',headers=headers,json={'slug':slug}).status_code==201
            assert client.post('/api/admin/regions/lubuskie/research',headers=headers,json={}).status_code==422
            assert client.post(path,headers=headers,json={'max_places':5001}).status_code==422
            created=client.post(path,headers=headers,json={'max_places':100});assert created.status_code==202,created.text
            job_id=created.json()['id'];event=threading.Event()
            assert created.json()['batch_size']==research.BATCH_SIZE
            assert client.post(path,headers=headers,json={}).status_code==409
            assert client.patch('/api/admin/regions/'+slug,headers=headers,json={'active':True}).status_code==409
            research.process_job_step(job_id,event)
            assert client.get(path,headers=headers).json()['job']['total']==3
            client.post(path+'/cancel',headers=headers)
            research.process_job_step(job_id,event)
            assert client.get(path,headers=headers).json()['job']['status']=='cancelled'
            assert client.post(path+'/resume',headers=headers).status_code==202
            research.process_job_step(job_id,event);research.process_job_step(job_id,event)
            report=client.get(path,headers=headers).json()['job']
            assert report['status']=='completed' and report['added']==2 and report['review']==1
            assert report['missing_photos']==2
            assert saved_during_batch==[0,1],'Places commit progressively while a batch is still running'
            assert len(calls)==1
            with SessionLocal() as db:
                places=db.scalars(select(Place).where(Place.region==slug)).all()
                assert all(p.details['coordinate_source'] and p.details['sources'] and p.research_key for p in places)
                places[0].description='Manual edit';places[0].details={**places[0].details,'admin_managed':True};db.commit()
            created=client.post(path,headers=headers,json={'max_places':100});new_id=created.json()['id']
            research.process_job_step(new_id,event);research.process_job_step(new_id,event);research.process_job_step(new_id,event)
            report=client.get(path,headers=headers).json()['job']
            assert report['duplicates']==2 and report['added']==0
            with SessionLocal() as db:
                assert db.scalar(select(Place).where(Place.description=='Manual edit')) is not None
            assert client.get('/api/places',params={'region':slug}).json()==[]
            assert client.patch('/api/admin/regions/'+slug,headers=headers,json={'active':True}).status_code==200
            assert len(client.get('/api/places',params={'region':slug}).json())==2
        finally:
            with SessionLocal() as db:
                ids=select(RegionResearchJob.id).where(RegionResearchJob.region==slug)
                db.execute(delete(RegionResearchCandidate).where(RegionResearchCandidate.job_id.in_(ids)))
                db.execute(delete(RegionResearchJob).where(RegionResearchJob.region==slug))
                db.execute(delete(Place).where(Place.region==slug));db.execute(delete(Region).where(Region.slug==slug));db.execute(delete(User).where(User.email==email));db.commit()
