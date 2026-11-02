import os
from uuid import uuid4
import pytest

if not os.environ.get('TEST_DATABASE_URL'):
    pytest.skip('Requires an isolated PostgreSQL test database.',allow_module_level=True)
os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
os.environ.setdefault('SECRET_KEY','test-only-secret-that-is-more-than-32-characters')
from fastapi.testclient import TestClient
from sqlalchemy import select,delete
from app.main import app,SessionLocal,User,Region,Place,CORE_TYPES


def account(client):
    email=f'admin-test-{uuid4().hex}@example.com'
    result=client.post('/api/auth/register',json={'email':email,'password':'test-password-123','name':'Test','is_superadmin':True})
    assert result.status_code==201,result.text
    assert result.json()['user']['is_superadmin'] is False
    return {'Authorization':'Bearer '+result.json()['access_token']},email


def test_region_permissions_draft_import_and_publication():
    with TestClient(app) as client:
        ordinary,ordinary_email=account(client)
        admin,email=account(client)
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==email));user.is_superadmin=True;db.commit()
        slug='kujawsko-pomorskie'
        try:
            assert client.get('/api/admin/regions').status_code in (401,403)
            assert client.get('/api/admin/regions',headers=ordinary).status_code==403
            assert client.post('/api/admin/regions',headers=ordinary,json={'slug':slug}).status_code==403
            assert client.get('/api/auth/me',headers=admin).json()['is_superadmin'] is True
            created=client.post('/api/admin/regions',headers=admin,json={'slug':slug})
            assert created.status_code==201,created.text
            region=next(r for r in created.json() if r['slug']==slug)
            assert set(region['allowed_types'])==set(CORE_TYPES)
            assert region['active'] is False
            assert client.post('/api/admin/regions',headers=admin,json={'slug':slug}).status_code==409
            assert client.patch('/api/admin/regions/'+slug,headers=admin,json={'active':True}).status_code==422
            record={'name':'Testowa atrakcja','location':'Toruń','description':'Opis','place_type':'heritage','lat':53.01,'lng':18.60,'region':slug,'source_url':'https://example.com/source'}
            assert client.post('/api/places',headers=ordinary,json=record).status_code==422
            for kind in ['food','stay','vineyard']:
                assert client.post('/api/places',headers=admin,json={**record,'place_type':kind}).status_code==422
            result=client.post('/api/places',headers=admin,json=record)
            assert result.status_code==201,result.text
            place=result.json();assert place['region']==slug
            assert place['id'] not in {p['id'] for p in client.get('/api/places').json()}
            assert not any(r['slug']==slug for r in client.get('/api/regions').json())
            assert client.get(f"/api/places/{place['id']}/community").status_code==404
            assert client.post('/api/routing',json={'transport':'walk','place_ids':[1,place['id']]}).status_code==422
            assert client.put(f"/api/admin/places/{place['id']}",headers=ordinary,json=record).status_code==403
            edited=client.put(f"/api/admin/places/{place['id']}",headers=admin,json={**record,'name':'Poprawiona nazwa'})
            assert edited.status_code==200
            batch=[{**record,'name':'Import 1'},{**record,'name':'Import 2','lat':53.02}]
            path='/api/admin/regions/'+slug+'/import'
            assert client.post(path,headers=ordinary,json={'places':batch}).status_code==403
            assert client.post(path,headers=admin,json={'places':batch}).json()=={'added':2,'skipped':0}
            assert client.post(path,headers=admin,json={'places':batch}).json()=={'added':0,'skipped':2}
            invalid=[{**record,'name':'Must rollback'},{**record,'place_type':'stay'}]
            assert client.post(path,headers=admin,json={'places':invalid}).status_code==422
            assert len(client.get('/api/admin/regions/'+slug+'/places',headers=admin).json())==3
            assert client.patch('/api/admin/regions/'+slug,headers=admin,json={'active':True}).status_code==200
            assert len(client.get('/api/places',params={'region':slug}).json())==3
            assert next(r for r in client.get('/api/regions').json() if r['slug']==slug)['place_count']==3
            with TestClient(app) as restarted:
                assert len(restarted.get('/api/places',params={'region':slug}).json())==3
                assert any(p['name']=='Poprawiona nazwa' for p in restarted.get('/api/admin/regions/'+slug+'/places',headers=admin).json())
            assert client.patch('/api/admin/regions/'+slug,headers=admin,json={'active':False}).status_code==200
            assert client.get('/api/places',params={'region':slug}).json()==[]
            assert client.patch('/api/admin/regions/lubuskie',headers=admin,json={'active':False}).status_code==422
        finally:
            with SessionLocal() as db:
                db.execute(delete(Place).where(Place.region==slug));db.execute(delete(Region).where(Region.slug==slug))
                db.execute(delete(User).where(User.email.in_([email,ordinary_email])));db.commit()


def test_bootstrap_promotes_existing_account_and_blocks_public_admin_registration(monkeypatch):
    with TestClient(app) as client:
        headers,email=account(client)
        reserved=f'reserved-{uuid4().hex}@example.com'
        monkeypatch.setenv('SUPERADMIN_EMAILS',email+','+reserved)
        try:
            with TestClient(app) as restarted:
                assert restarted.get('/api/auth/me',headers=headers).json()['is_superadmin'] is True
                assert restarted.post('/api/auth/register',json={'email':reserved,'name':'Untrusted','password':'test-password-123'}).status_code==403
        finally:
            with SessionLocal() as db:
                db.execute(delete(User).where(User.email==email));db.commit()


def test_initial_admin_password_only_creates_missing_account(monkeypatch):
    email=f'bootstrap-{uuid4().hex}@example.com'
    password='test-only-bootstrap-password-at-least-24'
    monkeypatch.setenv('SUPERADMIN_EMAILS',email)
    monkeypatch.setenv('SUPERADMIN_INITIAL_PASSWORD',password)
    try:
        with TestClient(app) as client:
            login=client.post('/api/auth/login',json={'email':email,'password':password})
            assert login.status_code==200
            assert login.json()['user']['is_superadmin'] is True
        monkeypatch.setenv('SUPERADMIN_INITIAL_PASSWORD','different-password-at-least-24-characters')
        with TestClient(app) as client:
            assert client.post('/api/auth/login',json={'email':email,'password':password}).status_code==200
            assert client.post('/api/auth/login',json={'email':email,'password':os.environ['SUPERADMIN_INITIAL_PASSWORD']}).status_code==401
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email==email));db.commit()
