import json
import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import pytest
from PIL import Image
from app.map_previews import has_photo,is_map_image


def test_unnamed_lake_does_not_search_unrelated_generic_photographs(monkeypatch):
    from app import photo_research
    monkeypatch.setattr(photo_research.sources,'obtain_photo',lambda *args:('',None,None))
    monkeypatch.setattr(photo_research.sources,'get_json',lambda *args,**kwargs:pytest.fail('Generic photo search must not run'))
    image,photo,message=photo_research.find_photo({'name':'Jezioro bez nazwy','location':'Lubuskie','lat':52,'lng':15,'details':{'lake_catalog':{'unnamed':True}}})
    assert not image and photo is None and 'bez nazwy' in message


def test_map_assets_are_complete_and_distinguished_from_photos():
    root=Path(__file__).resolve().parents[2]
    data=json.loads((root/'backend/lake-map-previews.json').read_text(encoding='utf-8'))
    assert len(data['previews'])==430
    images=set()
    for preview in data['previews']:
        assert preview['image'] not in images;images.add(preview['image'])
        assert preview['map_preview']['kind']=='map' and 'OpenStreetMap' in preview['map_preview']['attribution']
        with Image.open(root/'public'/preview['image'].lstrip('/')) as image:
            assert image.format=='WEBP' and image.size==(1200,800)
        assert not has_photo(preview['image'],preview['details'])
    assert has_photo('/photos/lake.webp',{'map_preview':{'image':'/images/lake-maps/old.webp'}})
    assert not has_photo('/images/attraction-placeholder.svg',{})
    assert is_map_image('/images/lake-maps/map.webp',{'map_preview':None})


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_map_import_preserves_photos_and_can_later_be_replaced_by_real_photo(tmp_path,monkeypatch):
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import text,delete
    from app.main import app,SessionLocal,Place,engine
    from app.map_previews import import_previews
    from app import photo_research
    key='osm:way:99900001';image='/images/lake-maps/'+'a'*24+'.webp';other_id=None
    run='map-photo-'+uuid4().hex;original=None
    with TestClient(app):
        with SessionLocal() as db:
            place=db.get(Place,910001);original={'image':place.image,'details':deepcopy(place.details)}
            place.image='/images/attraction-placeholder.svg';place.details={**place.details,'wikidata':'Q11727012','lake_catalog':{'source_keys':['wd:Q11727012']},'contact':{'phone':{'value':'123456789'}},'lake_info':{'beach':{'status':'unknown'}}}
            other=Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")),name='Keep real photo',subtitle='',location='Test',region='lubuskie',category='nature',
                        lat=52.8,lng=15.8,rating=0,description='Keep',image='/photos/real.webp',research_key=key,details={'kind':'lake','photo':{'author':'Real author'}})
            db.add(other);db.flush();other_id=other.id
            def preview(record,key):
                return {'research_key':key,'name':record.name,'lat':record.lat,'lng':record.lng,'details':record.details,'image':image,
                        'map_preview':{'kind':'map','image':image,'attribution':'© OpenStreetMap contributors','source_url':'https://www.openstreetmap.org/way/123'}}
            entries=[preview(place,'osm:way:99900002'),preview(other,key)]
            db.commit()
        path=tmp_path/'maps.json';path.write_text(json.dumps({'region':'lubuskie','previews':entries}),encoding='utf-8')
        try:
            assert import_previews(path)=={'updated':1,'preserved':1}
            assert import_previews(path)=={'updated':0,'preserved':1}
            with TestClient(app):pass
            with SessionLocal() as db:
                place=db.get(Place,910001)
                assert place.image==image,'Map survives seed refresh while the seed still has no photo'
                assert place.details['contact']['phone']['value']=='123456789' and place.details['lake_info']['beach']['status']=='unknown'
                assert place.details['wikidata']=='Q11727012','Source identity survives seed refresh'
                assert db.get(Place,other_id).image=='/photos/real.webp'
            photo_research.create_run('lubuskie',run)
            with engine.begin() as db:db.execute(text('DELETE FROM photo_research_tasks WHERE run_id=:run AND place_id<>910001'),{'run':run})
            monkeypatch.setattr(photo_research,'find_photo',lambda record:('/api/media/real-lake.webp',{'author':'Verified author','license':'CC BY-SA 4.0','source_url':'https://commons.wikimedia.org/wiki/File:Lake.jpg'},''))
            assert photo_research.process_one(run)
            assert import_previews(path)=={'updated':0,'preserved':2}
            with SessionLocal() as db:
                place=db.get(Place,910001)
                assert place.image=='/api/media/real-lake.webp' and has_photo(place.image,place.details)
                assert place.details['contact']['phone']['value']=='123456789'
        finally:
            with SessionLocal() as db:
                place=db.get(Place,910001);place.image=original['image'];place.details=original['details']
                if other_id:db.execute(delete(Place).where(Place.id==other_id))
                db.execute(text('DELETE FROM photo_research_runs WHERE id=:run'),{'run':run});db.commit()
