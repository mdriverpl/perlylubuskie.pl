import json
import os
from pathlib import Path
from uuid import uuid4
import pytest
from app.lake_catalog import validate,source_keys,same_lake


def test_packaged_lakes_cover_sources_zabor_and_anonymous_waters():
    data=json.loads((Path(__file__).resolve().parents[1]/'lake-catalogs/lubuskie.json').read_text(encoding='utf-8'))
    records=data['places'];keys=set()
    assert len(records)==data['report']['catalog_lakes']
    assert data['report']['named_lakes']+data['report']['unnamed_lakes']==len(records)
    assert len(records)>=500 and data['report']['unnamed_lakes']>0
    for record in records:
        validate(record,'lubuskie')
        assert not keys&source_keys(record),'An identity must only occur in one packaged lake'
        keys|=source_keys(record)
    assert len([key for key in keys if key.startswith('osm:')])==data['report']['osm_lake_objects']
    assert {'osm:way:141626503','osm:way:141626526','osm:way:217653701'}.issubset(keys)
    zabor=next(p for p in records if p['research_key']=='osm:way:141626503')
    assert 'Liwno Wielkie' in zabor['details']['aliases'] and 'Zabór' in zabor['location']


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_lake_import_is_additive_idempotent_and_preserves_enrichment(tmp_path):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import select,delete,text
    from app.main import app,SessionLocal,Region,Place,RegionResearchJob,User
    from app.lake_catalog import import_catalogs
    slug='podlaskie';email='lake-catalog-'+uuid4().hex+'@example.com';original_id=None;job_id=None
    def record(key,name,lat,lng,bounds,unnamed=False):
        return {'research_key':key,'name':name,'location':'Test','region':slug,'category':'nature','description':'Catalog metadata only.',
                'subtitle':'Lake','image':'/images/attraction-placeholder.svg','lat':lat,'lng':lng,'rating':0,
                'details':{'kind':'lake','aliases':[],'sources':[{'title':'OSM','url':'https://www.openstreetmap.org/way/123'}],
                           'coordinate_license':'OpenStreetMap ODbL 1.0','lake_catalog':{'source_keys':[key],'bounds':bounds,'unnamed':unnamed}}}
    records=[record('osm:way:99111','Długie',52.51,15.49,[15.48,52.48,15.52,52.52]),
             record('osm:way:99112','New lake',52.7,15.7,[15.69,52.69,15.71,52.71]),
             record('osm:way:99113','Jezioro bez nazwy',52.8,15.8,[15.8,52.8,15.8002,52.8002],True),
             record('osm:way:99114','Jezioro bez nazwy',52.8005,15.8005,[15.8005,52.8005,15.8007,52.8007],True)]
    assert not same_lake(records[2],records[3])
    path=tmp_path/'test-lakes.json';path.write_text(json.dumps({'region':slug,'places':records}),encoding='utf-8')
    with TestClient(app):
        try:
            with SessionLocal() as db:
                db.add(Region(slug=slug,name='Test',allowed_types=['lake'],active=True))
                user=User(email=email,name='Test',password='test');db.add(user);db.flush()
                original=Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")),name='Jezioro Długie',subtitle='Manual',location='Manual location',
                    region=slug,category='nature',description='Keep description',image='/keep-photo.webp',lat=52.5,lng=15.5,rating=0,
                    details={'kind':'lake','admin_managed':True,'photo':{'author':'Keep'},'contact':{'phone':{'value':'123456789'}},'lake_info':{'motorboats':{'status':'unknown'}}})
                db.add(original);job=RegionResearchJob(region=slug,active_region=slug,created_by=user.id,status='queued');db.add(job);db.commit();original_id=original.id;job_id=job.id
            result=import_catalogs(tmp_path)
            assert result==[{'region':slug,'added':3,'linked':1,'total':4}]
            with SessionLocal() as db:
                original=db.get(Place,original_id)
                original.details={**original.details,'lake_catalog':{**original.details['lake_catalog'],'source_keys':['osm:way:99111','wd:Q11727012']}}
                db.commit()
            assert import_catalogs(tmp_path)==[]
            with SessionLocal() as db:
                assert db.get(Place,original_id).details['wikidata']=='Q11727012','Previously linked source identity is repaired even when catalog version is unchanged'
            records[0]['description']='Never overwrite manual text'
            path.write_text(json.dumps({'region':slug,'places':records}),encoding='utf-8')
            assert import_catalogs(tmp_path)[0]['added']==0
            with SessionLocal() as db:
                original=db.get(Place,original_id)
                assert original.description=='Keep description' and original.image=='/keep-photo.webp'
                assert original.details['contact']['phone']['value']=='123456789' and original.details['photo']['author']=='Keep'
                assert original.details['lake_info']['motorboats']['status']=='unknown'
                assert db.get(RegionResearchJob,job_id).status=='queued','A lake import never cancels another task'
                assert 'osm:way:99111' in original.details['lake_catalog']['source_keys']
            records[1]['lng']=99
            path.write_text(json.dumps({'region':slug,'places':records}),encoding='utf-8')
            with pytest.raises(ValueError):import_catalogs(tmp_path)
        finally:
            with SessionLocal() as db:
                if job_id:db.execute(delete(RegionResearchJob).where(RegionResearchJob.id==job_id))
                db.execute(delete(Place).where(Place.region==slug));db.execute(delete(Region).where(Region.slug==slug))
                db.execute(delete(User).where(User.email==email));db.execute(text("DELETE FROM lake_catalog_imports WHERE catalog='test-lakes.json'"));db.commit()
