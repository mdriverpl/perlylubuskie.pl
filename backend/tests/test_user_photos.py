import os
from io import BytesIO
from uuid import uuid4
from datetime import datetime,timedelta,timezone
import pytest
from PIL import Image
from fastapi import HTTPException
from app.user_photos import normalize_photo,MAX_BYTES


def picture():
    output=BytesIO();image=Image.new('RGB',(1800,900),'green')
    exif=Image.Exif();exif[270]='private metadata';image.save(output,format='JPEG',exif=exif)
    return output.getvalue()


def test_upload_reencodes_pixels_and_discards_metadata():
    with Image.open(BytesIO(normalize_photo(picture()))) as image:
        assert image.format=='WEBP' and image.size==(1600,800)
        assert not image.getexif() and 'exif' not in image.info
    for content in (b'',b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',b'not a photograph'):
        with pytest.raises(HTTPException) as error:normalize_photo(content)
        assert error.value.status_code==422


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Needs isolated PostgreSQL')
def test_owned_photos_create_append_authorize_and_survive_restart():
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    os.environ.setdefault('SECRET_KEY','test-only-secret-more-than-32-characters')
    from fastapi.testclient import TestClient
    from sqlalchemy import delete,select,func
    from app.main import app,SessionLocal,Place,PlacePhoto,User
    emails=[];place_id=None
    with TestClient(app) as client:
        def account():
            email=uuid4().hex+'@example.com';emails.append(email)
            r=client.post('/api/auth/register',json={'email':email,'name':'Autorka zdjęć','password':'photo-test-password'})
            assert r.status_code==201
            return {'Authorization':'Bearer '+r.json()['access_token']}
        owner=account();other=account();image=picture()
        def upload(headers=owner):
            r=client.post('/api/place-photos',headers={**headers,'Content-Type':'image/jpeg'},content=image)
            assert r.status_code==201,r.text
            return r.json()['id']
        data={'name':'Miejsce ze zdjęciami','location':'Zabór','description':'Opis','place_type':'lake','lat':51.95,'lng':15.7}
        try:
            assert client.post('/api/place-photos',content=image).status_code in (401,403)
            assert client.post('/api/place-photos',headers=owner,content=b'invalid').status_code==422
            assert client.post('/api/place-photos',headers=owner,content=b'x'*(MAX_BYTES+1)).status_code==413
            first=upload();second=upload();foreign=upload(other)
            url=f'/api/place-photos/{first}.webp'
            assert client.get(url).status_code==404,'Unattached photos are not public'
            with SessionLocal() as db:before=db.scalar(select(func.count()).select_from(Place))
            for ids,rights in (([first],False),([foreign],True),([first,first],True)):
                assert client.post('/api/places',headers=owner,json={**data,'photo_ids':ids,'photo_rights_confirmed':rights}).status_code==422
            with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(Place))==before,'Invalid uploads must not create partial places'
            r=client.post('/api/places',headers=owner,json={**data,'photo_ids':[second,first],'photo_rights_confirmed':True})
            assert r.status_code==201,r.text
            place=r.json();place_id=place['id'];path=f'/api/places/{place_id}/photos'
            assert place['image']==f'/api/place-photos/{second}.webp'
            assert [p['id'] for p in place['details']['user_photos']]==[second,first]
            assert all(p['author']=='Autorka zdjęć' for p in place['details']['user_photos'])
            photo=client.get(url);assert photo.status_code==200 and photo.headers['content-type']=='image/webp'
            assert 'immutable' in photo.headers['cache-control']
            with Image.open(BytesIO(photo.content)) as rendered:assert rendered.size==(1600,800) and not rendered.getexif()
            assert client.post(path,headers=other,json={'photo_ids':[foreign],'photo_rights_confirmed':True}).status_code==403
            assert client.post('/api/places/1/photos',headers=owner,json={'photo_ids':[foreign],'photo_rights_confirmed':True}).status_code==403
            assert client.post(path,headers=owner,json={'photo_ids':[first],'photo_rights_confirmed':True}).status_code==422,'Cannot reuse attached photo'
            extra=[upload() for _ in range(3)]
            added=client.post(path,headers=owner,json={'photo_ids':extra,'photo_rights_confirmed':True})
            assert added.status_code==200 and len(added.json()['details']['user_photos'])==5
            assert 'like_count' not in added.json(),'Photo updates must not reset existing social counts'
            excess=upload()
            assert client.post(path,headers=owner,json={'photo_ids':[excess],'photo_rights_confirmed':True}).status_code==422
            with SessionLocal() as db:
                staged=db.get(PlacePhoto,foreign);staged.created_at=datetime.now(timezone.utc)-timedelta(days=2);db.commit()
            upload()
            with SessionLocal() as db:assert db.get(PlacePhoto,foreign) is None,'Abandoned uploads expire'
            with TestClient(app) as restarted:
                assert restarted.get(url).content==photo.content
                saved=next(p for p in restarted.get('/api/places').json() if p['id']==place_id)
                assert len(saved['details']['user_photos'])==5 and saved['image']==place['image']
        finally:
            with SessionLocal() as db:
                if place_id:db.execute(delete(Place).where(Place.id==place_id))
                db.execute(delete(User).where(User.email.in_(emails)));db.commit()
