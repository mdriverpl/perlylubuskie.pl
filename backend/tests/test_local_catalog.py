import json,os
from uuid import uuid4
import pytest
if not os.environ.get('TEST_DATABASE_URL'):pytest.skip('Needs isolated PostgreSQL',allow_module_level=True)
os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
os.environ.setdefault('SECRET_KEY','test-only-secret-that-is-more-than-32-characters')
from fastapi.testclient import TestClient
from sqlalchemy import select,delete,text
from app.main import app,SessionLocal,Region,User,Place,RegionResearchJob,RegionResearchCandidate,CORE_TYPES
from app.local_catalog import import_catalogs


def test_packaged_catalog_preserves_manual_places_deduplicates_and_stops_remote_job(tmp_path):
    slug='kujawsko-pomorskie';email=f'catalog-{uuid4().hex}@example.com'
    def record(qid,name):return {'research_key':'wd:'+qid,'name':name,'subtitle':'Opis','location':'Toruń','description':'Potwierdzony opis obiektu.','region':slug,'category':'heritage','image':'/images/heritage-placeholder.svg','lat':53.01,'lng':18.60,'rating':0,'details':{'kind':'palace','wikidata':qid,'sources':[{'title':'Wikidata','url':'https://www.wikidata.org/wiki/'+qid}]}}
    records=[record('Q999999991','Existing palace'),record('Q999999992','New palace')]
    path=tmp_path/'catalog.json';path.write_text(json.dumps({'region':slug,'places':records}),encoding='utf-8')
    with TestClient(app):
        try:
            with SessionLocal() as db:
                db.add(Region(slug=slug,name='Kujawsko-pomorskie',active=False,allowed_types=list(CORE_TYPES)))
                user=User(email=email,name='Test',password='test',is_superadmin=True);db.add(user);db.flush()
                db.add(Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")),**{**records[0],'description':'Manual description','details':{**records[0]['details'],'admin_managed':True}}))
                job=RegionResearchJob(region=slug,active_region=slug,created_by=user.id);db.add(job);db.commit();job_id=job.id
            result=import_catalogs(tmp_path)
            assert result==[{'region':slug,'added':1,'updated':0,'skipped':1,'total':2}]
            assert import_catalogs(tmp_path)==[]
            records[0]['description']='Should never replace manual text';path.write_text(json.dumps({'region':slug,'places':records}),encoding='utf-8')
            assert import_catalogs(tmp_path)[0]['added']==0
            with SessionLocal() as db:
                places=db.scalars(select(Place).where(Place.region==slug)).all();assert len(places)==2
                assert next(p for p in places if p.name=='Existing palace').description=='Manual description'
                job=db.get(RegionResearchJob,job_id);assert job.status=='cancelled' and job.cancel_requested and job.active_region is None
                assert job.report['local_import']['total']==2
                assert db.get(Region,slug).active is False,'Import must not publish a draft without owner action'
        finally:
            with SessionLocal() as db:
                db.execute(delete(RegionResearchCandidate).where(RegionResearchCandidate.job_id.in_(select(RegionResearchJob.id).where(RegionResearchJob.region==slug))))
                db.execute(delete(RegionResearchJob).where(RegionResearchJob.region==slug));db.execute(delete(Place).where(Place.region==slug));db.execute(delete(Region).where(Region.slug==slug));db.execute(delete(User).where(User.email==email))
                db.execute(text('DELETE FROM local_catalog_imports WHERE region=:region'),{'region':slug});db.commit()
