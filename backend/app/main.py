import os
import json
import logging
from uuid import uuid4
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

import jwt
from fastapi import FastAPI, Depends, HTTPException, Response, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import create_engine, String, Text, Float, Boolean, ForeignKey, JSON, DateTime, UniqueConstraint, select, func, text, or_, cast, case
from sqlalchemy.dialects.postgresql import insert, JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from .routing import calculate_route, route_gpx
from .maps import router as maps_router
from . import ai_routes, region_research, contact_research, photo_research

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg://perly:perly@localhost:5432/perly')
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if len(SECRET_KEY) < 32:
    raise RuntimeError('Ustaw SECRET_KEY o długości co najmniej 32 znaków.')
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
password_hash = PasswordHash.recommended()
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
DUMMY_HASH = password_hash.hash('invalid-account-timing-placeholder')


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password: Mapped[str] = mapped_column(String(255))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)


class Region(Base):
    __tablename__ = 'regions'
    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    allowed_types: Mapped[list[str]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class Place(Base):
    __tablename__ = 'places'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(30), index=True)
    image: Mapped[str] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    region: Mapped[str] = mapped_column(String(40), default='lubuskie', index=True)
    research_key: Mapped[str | None] = mapped_column(String(100),nullable=True)


class RegionResearchJob(Base):
    __tablename__='region_research_jobs'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    region: Mapped[str] = mapped_column(String(40),index=True)
    active_region: Mapped[str | None] = mapped_column(String(40),nullable=True,unique=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(20),default='queued')
    phase: Mapped[str] = mapped_column(String(30),default='discovery')
    max_places: Mapped[int] = mapped_column(default=5000)
    discovered: Mapped[int] = mapped_column(default=0)
    discovery_done: Mapped[bool] = mapped_column(Boolean,default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean,default=False)
    error: Mapped[str] = mapped_column(String(1000),default='')
    report: Mapped[dict] = mapped_column(JSON,default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))


class RegionResearchCandidate(Base):
    __tablename__='region_research_candidates'
    __table_args__=(UniqueConstraint('job_id','source_key'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey('region_research_jobs.id',ondelete='CASCADE'),index=True)
    source_key: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON,default=dict)
    status: Mapped[str] = mapped_column(String(20),default='pending')
    error: Mapped[str] = mapped_column(String(500),default='')
    place_id: Mapped[int | None] = mapped_column(nullable=True)
    photo_added: Mapped[bool] = mapped_column(Boolean,default=False)


class Favorite(Base):
    __tablename__ = 'favorites'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey('places.id', ondelete='CASCADE'), primary_key=True)


class Trip(Base):
    __tablename__ = 'trips'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000), default='')
    transport: Mapped[str] = mapped_column(String(20))
    place_ids: Mapped[list[int]] = mapped_column(JSON)
    point_positions: Mapped[list[dict]] = mapped_column(JSON, default=list)
    cover_image: Mapped[str] = mapped_column(Text, default='')
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_points: Mapped[list[dict]] = mapped_column(JSON, default=list)


class Visit(Base):
    __tablename__ = 'place_visits'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey('places.id', ondelete='CASCADE'), primary_key=True, index=True)


class PlaceLike(Base):
    __tablename__ = 'place_likes'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey('places.id', ondelete='CASCADE'), primary_key=True, index=True)


class Comment(Base):
    __tablename__ = 'place_comments'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey('places.id', ondelete='CASCADE'), index=True)
    body: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def get_db():
    with SessionLocal() as db:
        yield db


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=['HS256'], issuer='perly', options={'require': ['sub', 'exp', 'iss']})
        user_id = int(payload['sub'])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(401, 'Sesja wygasła. Zaloguj się ponownie.')
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, 'Nieprawidłowe konto.')
    return user


def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(optional_security), db: Session = Depends(get_db)):
    return current_user(credentials, db) if credentials else None


def catalog_viewer(credentials: HTTPAuthorizationCredentials | None = Depends(optional_security), db: Session = Depends(get_db)):
    try:
        return current_user(credentials, db) if credentials else None
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return None  # Public catalog remains readable after a saved session expires.


def superadmin(user: User = Depends(current_user)):
    if not user.is_superadmin:
        raise HTTPException(403, 'Ta operacja wymaga konta superadministratora.')
    return user


def bootstrap_admin_emails():
    return {email.strip().lower() for email in os.environ.get('SUPERADMIN_EMAILS', '').split(',') if email.strip()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    # Additive catalog migration; stable IDs preserve community data and saved trips.
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN NOT NULL DEFAULT FALSE'))
        connection.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS region VARCHAR(40) NOT NULL DEFAULT 'lubuskie'"))
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_places_region ON places(region)'))
        connection.execute(text('ALTER TABLE places ADD COLUMN IF NOT EXISTS research_key VARCHAR(100)'))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_places_research_key ON places(research_key) WHERE research_key IS NOT NULL'))
        connection.execute(text('CREATE SEQUENCE IF NOT EXISTS submitted_place_ids START WITH 1000000000'))
        connection.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS details JSON NOT NULL DEFAULT '{}'"))
        connection.execute(text('ALTER TABLE places ALTER COLUMN image TYPE TEXT'))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS description VARCHAR(2000) NOT NULL DEFAULT ''"))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS point_positions JSON NOT NULL DEFAULT '[]'"))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS cover_image TEXT NOT NULL DEFAULT ''"))
        connection.execute(text('ALTER TABLE trips ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE'))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS custom_points JSON NOT NULL DEFAULT '[]'"))
    with SessionLocal() as db:
        if not db.get(Region, 'lubuskie'):
            db.add(Region(slug='lubuskie', name='Lubuskie', allowed_types=['castle','palace','lake','nature','heritage','leisure','stay','vineyard','food'], active=True))
        configured_admins=bootstrap_admin_emails()
        matched_admins=0
        created_admins=0
        bootstrap_password=os.environ.get('SUPERADMIN_INITIAL_PASSWORD','')
        for email in configured_admins:
            connection_user = db.scalar(select(User).where(func.lower(User.email) == email))
            if not connection_user and len(configured_admins)==1 and len(bootstrap_password)>=24:
                connection_user=User(email=email,name='Administrator',password=password_hash.hash(bootstrap_password),is_superadmin=True)
                db.add(connection_user)
                created_admins+=1
            if connection_user:
                connection_user.is_superadmin = True
                matched_admins+=1
        if configured_admins:
            logging.getLogger('uvicorn.error').info('Superadmin bootstrap: %s accounts enabled, %s newly created, %s configured.',matched_admins,created_admins,len(configured_admins))
        data = json.loads((Path(__file__).resolve().parents[1] / 'seed.json').read_text(encoding='utf-8'))
        for place in data:
            statement = insert(Place).values(**dict(place, details=place.get('details', {})))
            updates = {key: getattr(statement.excluded, key) for key in place if key != 'id'}
            # Verified production contacts survive seed refreshes and deployments.
            updates['details'] = cast(statement.excluded.details, JSONB).op('||')(
                case((cast(Place.details, JSONB).has_key('contact'),
                      func.jsonb_build_object('contact', Place.details['contact'])),
                     else_=cast(text("'{}'"), JSONB)))
            keep_photo=statement.excluded.image.like('%placeholder.svg') & Place.details['photo']['source_url'].as_string().is_not(None) & ~Place.image.like('%placeholder.svg')
            updates['image']=case((keep_photo,Place.image),else_=statement.excluded.image)
            updates['details']=updates['details'].op('||')(case((keep_photo,func.jsonb_build_object('photo',Place.details['photo'])),else_=cast(text("'{}'"),JSONB)))
            statement = statement.on_conflict_do_update(index_elements=[Place.id], set_=updates,where=Place.details['admin_managed'].as_boolean().is_not(True))
            db.execute(statement)
        db.commit()
    from .local_catalog import import_catalogs
    import_catalogs()
    if os.environ.get('REGION_RESEARCH_AUTO_RECOVER','0')=='1':region_research.recover_discovery_jobs()
    worker=region_research.start_worker()
    contact_worker=contact_research.start_worker()
    photo_worker=photo_research.start_worker()
    try:
        yield
    finally:
        worker.set()
        contact_worker.set()
        photo_worker.set()


app = FastAPI(title='Perły Ziemi Lubuskiej API', version='1.0.0', lifespan=lifespan)
app.include_router(maps_router)
region_research.media_root().mkdir(parents=True,exist_ok=True)
app.mount('/api/media',StaticFiles(directory=str(region_research.media_root())),name='catalog-media')
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])


@app.get('/api/ai/config')
def ai_config():
    return {'enabled': ai_routes.configured()}


@app.post('/api/ai/plan')
def ai_plan(data: ai_routes.AiRequest, request: Request, db: Session = Depends(get_db)):
    statement=select(Place).join(Region,Region.slug==Place.region).where(Region.active.is_(True))
    if data.region:
        statement=statement.where(Place.region==data.region)
    catalog = [ai_routes.catalog_entry(p)
               for p in db.scalars(statement.order_by(Place.id).limit(5000)).all()]
    return ai_routes.propose(data.prompt, catalog, request.client.host if request.client else 'unknown')


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Register(Login):
    name: str = Field(min_length=1, max_length=80)


class PlaceOut(BaseModel):
    model_config = {'from_attributes': True}
    id: int
    name: str
    subtitle: str
    category: str
    image: str
    lat: float
    lng: float
    rating: float
    location: str
    description: str
    details: dict = Field(default_factory=dict)
    like_count: int = 0
    comment_count: int = 0
    popularity: int = 0
    liked: bool = False
    region: str = 'lubuskie'


class PlaceInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default='', max_length=250)
    location: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    place_type: Literal['castle', 'palace', 'vineyard', 'food', 'lake', 'nature', 'heritage', 'stay', 'leisure']
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    image: str = Field(default='', max_length=2000, pattern=r'^(?:https://[^\s]+)?$')
    region: str = Field(default='lubuskie', max_length=40)
    source_url: str = Field(default='', max_length=2000, pattern=r'^(?:https://[^\s]+)?$')


def new_catalog_place(data, user, db):
    if not all(value.strip() for value in (data.name, data.location, data.description)):
        raise HTTPException(422, 'Podaj nazwę, miejscowość i opis miejsca.')
    category = {'castle': 'heritage', 'palace': 'heritage', 'lake': 'nature'}.get(data.place_type, data.place_type)
    region = db.get(Region, data.region)
    if not region or (not region.active and not user.is_superadmin):
        raise HTTPException(422, 'Wybierz dostępne województwo.')
    if data.place_type not in region.allowed_types:
        raise HTTPException(422, 'Ten rodzaj miejsca jest wyłączony w województwie.')
    place = Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")), name=data.name.strip(), subtitle=data.subtitle.strip(), location=data.location.strip(), description=data.description.strip(), lat=data.lat, lng=data.lng, image=data.image or '/images/heritage-placeholder.svg', category=category, rating=0, region=data.region, details={'kind': data.place_type, 'submitted_by': user.id, **({'source_url':data.source_url} if data.source_url else {})})
    return place


@app.post('/api/places', response_model=PlaceOut, status_code=201)
def create_place(data: PlaceInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    place = new_catalog_place(data,user,db)
    db.add(place)
    db.commit()
    return place


REGION_NAMES = {
    'dolnoslaskie':'Dolnośląskie','kujawsko-pomorskie':'Kujawsko-pomorskie','lubelskie':'Lubelskie','lubuskie':'Lubuskie',
    'lodzkie':'Łódzkie','malopolskie':'Małopolskie','mazowieckie':'Mazowieckie','opolskie':'Opolskie',
    'podkarpackie':'Podkarpackie','podlaskie':'Podlaskie','pomorskie':'Pomorskie','slaskie':'Śląskie',
    'swietokrzyskie':'Świętokrzyskie','warminsko-mazurskie':'Warmińsko-mazurskie','wielkopolskie':'Wielkopolskie','zachodniopomorskie':'Zachodniopomorskie',
}
PLACE_TYPES = {'castle':'Zamki','palace':'Pałace','lake':'Jeziora','nature':'Parki i przyroda','heritage':'Zabytki i historia','leisure':'Atrakcje rodzinne','stay':'Noclegi','vineyard':'Winiarnie','food':'Restauracje'}
CORE_TYPES = ['castle','palace','lake','nature','heritage','leisure']


def region_summaries(db, include_drafts=False):
    regions = db.scalars(select(Region).order_by(Region.name)).all()
    counts = dict(db.execute(select(Place.region,func.count()).group_by(Place.region)).all())
    return [{'slug':r.slug,'name':r.name,'allowed_types':r.allowed_types,'active':r.active,'place_count':counts.get(r.slug,0)} for r in regions if include_drafts or r.active]


@app.get('/api/regions')
def public_regions(db: Session = Depends(get_db)):
    return region_summaries(db)


class RegionInput(BaseModel):
    slug: str = Field(min_length=2,max_length=40)
    allowed_types: list[str] = Field(default_factory=lambda:list(CORE_TYPES),min_length=1,max_length=9)


class RegionUpdate(BaseModel):
    active: bool
    finish_research: bool = False


class RegionImport(BaseModel):
    places: list[PlaceInput] = Field(min_length=1,max_length=500)


class RegionResearchInput(BaseModel):
    max_places: int = Field(default=25,ge=1,le=100)


def research_status(job,db):
    if not job:return None
    counts=dict(db.execute(select(RegionResearchCandidate.status,func.count()).where(RegionResearchCandidate.job_id==job.id).group_by(RegionResearchCandidate.status)).all())
    photos=db.scalar(select(func.count()).select_from(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job.id,RegionResearchCandidate.photo_added.is_(True)))
    issues=db.execute(select(RegionResearchCandidate.payload,RegionResearchCandidate.error).where(RegionResearchCandidate.job_id==job.id,RegionResearchCandidate.error!='').order_by(RegionResearchCandidate.id).limit(20)).all()
    saved=sum(counts.get(key,0) for key in ('added','updated','duplicate'))
    return {'id':job.id,'region':job.region,'status':job.status,'phase':job.phase,'max_places':job.max_places,'batch_size':region_research.BATCH_SIZE,'discovery_done':job.discovery_done,'active_jobs':db.scalar(select(func.count()).select_from(RegionResearchJob).where(RegionResearchJob.status.in_(['queued','running']))),'discovered':job.discovered,'total':sum(counts.values()),'processed':sum(value for key,value in counts.items() if key!='pending'),'added':counts.get('added',0),'updated':counts.get('updated',0),'duplicates':counts.get('duplicate',0),'review':counts.get('review',0),'photos':photos,'missing_photos':max(0,saved-photos),'cancel_requested':job.cancel_requested,'error':job.error,'report':job.report,'issues':[{'name':payload.get('name',''),'message':error} for payload,error in issues],'updated_at':job.updated_at}


def latest_research(slug,db):
    return db.scalar(select(RegionResearchJob).where(RegionResearchJob.region==slug).order_by(RegionResearchJob.created_at.desc()).limit(1))


@app.get('/api/admin/regions/{slug}/research')
def get_region_research(slug: str,user: User=Depends(superadmin),db: Session=Depends(get_db)):
    if not db.get(Region,slug):raise HTTPException(404,'Nie znaleziono województwa.')
    return {'configured':ai_routes.configured(),'job':research_status(latest_research(slug,db),db)}


@app.post('/api/admin/regions/{slug}/research',status_code=202)
def start_region_research(slug: str,data: RegionResearchInput,user: User=Depends(superadmin),db: Session=Depends(get_db)):
    region=db.scalar(select(Region).where(Region.slug==slug).with_for_update())
    if not region:raise HTTPException(404,'Nie znaleziono województwa.')
    if region.active:raise HTTPException(422,'Automatyczne zbieranie danych uruchom dla województwa w szkicu.')
    if not ai_routes.configured():raise HTTPException(503,'Wyszukiwanie AI wymaga konfiguracji klucza OpenAI na serwerze.')
    if not set(region.allowed_types).intersection(CORE_TYPES):raise HTTPException(422,'Wybierz przynajmniej jedną kategorię atrakcji.')
    job=RegionResearchJob(region=slug,active_region=slug,created_by=user.id,max_places=data.max_places,report={'manual_budget_start':0,'manual_budget_limit':data.max_places})
    db.add(job)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Zbieranie danych dla tego województwa jest już uruchomione.') from None
    return research_status(job,db)


@app.post('/api/admin/regions/{slug}/research/cancel')
def cancel_region_research(slug: str,user: User=Depends(superadmin),db: Session=Depends(get_db)):
    job=latest_research(slug,db)
    if not job:raise HTTPException(404,'Nie znaleziono zadania.')
    if job.status in ('queued','running'):
        job.cancel_requested=True;db.commit()
    return research_status(job,db)


@app.post('/api/admin/regions/{slug}/research/resume',status_code=202)
def resume_region_research(slug: str,user: User=Depends(superadmin),db: Session=Depends(get_db)):
    region=db.scalar(select(Region).where(Region.slug==slug).with_for_update());job=latest_research(slug,db)
    if not job or job.status not in ('failed','cancelled'):raise HTTPException(422,'To zadanie nie wymaga wznowienia.')
    if not region or region.active:raise HTTPException(422,'Przed wznowieniem województwo musi być szkicem.')
    if not ai_routes.configured():raise HTTPException(503,'Skonfiguruj klucz OpenAI na serwerze.')
    if job.discovery_done and (job.report or {}).get('discovery_errors'):
        job.discovery_done=False;job.phase='discovery';job.report={**job.report,'discovery_cursor':0,'discovery_errors':[]}
    job.status='queued';job.active_region=slug;job.cancel_requested=False;job.error=''
    processed=db.scalar(select(func.count()).select_from(RegionResearchCandidate).where(RegionResearchCandidate.job_id==job.id,RegionResearchCandidate.status!='pending'))
    job.report={**(job.report or {}),'manual_budget_start':processed,'manual_budget_limit':min(100,job.max_places)}
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Inne zadanie dla tego województwa jest uruchomione.') from None
    return research_status(job,db)


@app.get('/api/admin/regions')
def admin_regions(user: User = Depends(superadmin), db: Session = Depends(get_db)):
    return {'regions':region_summaries(db,True),'options':[{'slug':slug,'name':name} for slug,name in REGION_NAMES.items()],'types':[{'id':key,'name':value} for key,value in PLACE_TYPES.items()]}


@app.get('/api/admin/contact-research')
def contact_research_progress(user: User = Depends(superadmin)):
    return contact_research.progress()


@app.post('/api/admin/contact-research/resume')
def resume_contact_research(user: User = Depends(superadmin)):
    run = os.environ.get('CONTACT_RESEARCH_RUN', '').strip()
    if not run:
        raise HTTPException(409, 'Nie skonfigurowano zadania sprawdzania kontaktów.')
    if os.environ.get('CONTACT_RESEARCH_WORKER','1')=='0':raise HTTPException(409,'Sprawdzanie kontaktów jest wyłączone w konfiguracji serwera.')
    if not ai_routes.configured():raise HTTPException(503,'Brakuje klucza OpenAI.')
    if contact_research.progress()['status']=='running':raise HTTPException(409,'Sprawdzanie kontaktów już trwa.')
    with engine.begin() as db:
        db.execute(text("UPDATE place_contact_tasks SET status='pending',attempts=0,error='' WHERE run_id=:run AND status IN ('blocked','failed','cancelled','paused')"), {'run': run})
    contact_research.start_worker(manual=True)
    return contact_research.progress()


@app.post('/api/admin/contact-research/stop')
def stop_contact_research(user: User = Depends(superadmin)):
    return contact_research.stop_work()


class TaskCommand(BaseModel):
    region: str = Field(default='lubuskie',max_length=40)
    max_places: int = Field(default=25,ge=1,le=100)


@app.get('/api/admin/tasks')
def admin_tasks(region: str='lubuskie',user: User=Depends(superadmin),db: Session=Depends(get_db)):
    selected=db.get(Region,region)
    contact=contact_research.progress();photos=photo_research.progress('lubuskie')
    job=research_status(latest_research(region,db),db) if selected else None
    region_status=job['status'] if job else 'idle'
    if selected and selected.active and region_status not in ('queued','running'):region_status='published'
    tasks=[
        {'id':'photos','name':'Brakujące zdjęcia — Lubuskie','agent':'Wikimedia Commons / OpenStreetMap','model':None,'paid':False,
         'status':photos['status'],'processed':photos['processed'],'total':photos['total'],'added':photos['added'],'missing':photos['missing'],
         'message':photos.get('current_name') or photos.get('error',''),'region':'lubuskie','can_start':photos['status']!='running','can_stop':photos['status']=='running'},
        {'id':'contacts','name':'Zamki i pałace — usługi i kontakt','agent':'Weryfikacja źródeł','model':contact_research.model(),'paid':True,
         'status':contact['status'],'processed':contact['checked'],'total':contact['total'],'failed':contact['failed'],
         'message':contact['error'] if contact['status'] not in ('stopped','completed') else '',
         'limit':contact_research.MAX_PER_START,'can_start':bool(contact['run']) and ai_routes.configured() and os.environ.get('CONTACT_RESEARCH_WORKER','1')!='0' and contact['status']!='running',
         'can_stop':contact['status'] in ('running','blocked','paused')},
        {'id':'region','name':'Opisy i atrakcje — '+(selected.name if selected else region),'agent':'Badanie atrakcji','model':region_research.model(),'paid':True,
         'status':region_status,'processed':(job or {}).get('processed',0),'total':(job or {}).get('total',0),'limit':25,
         'message':(job or {}).get('error',''),'region':region,'can_start':bool(selected and not selected.active and ai_routes.configured()) and region_status not in ('queued','running'),
         'can_stop':region_status in ('queued','running')},
    ]
    return {'tasks':tasks,'planner':{'model':ai_routes.model(),'status':'Na żądanie użytkownika'},'configured':ai_routes.configured()}


@app.post('/api/admin/tasks/{kind}/start')
def start_admin_task(kind: Literal['photos','contacts','region'],data: TaskCommand,user: User=Depends(superadmin),db: Session=Depends(get_db)):
    if kind=='contacts':return resume_contact_research(user)
    if not db.get(Region,data.region):raise HTTPException(404,'Nie znaleziono województwa.')
    if kind=='photos':
        if photo_research.progress(data.region)['status']=='running':raise HTTPException(409,'Pobieranie zdjęć już trwa.')
        run_id=os.environ.get('PHOTO_RESEARCH_RUN') if data.region==os.environ.get('PHOTO_RESEARCH_REGION','lubuskie') else None
        photo_research.create_run(data.region,run_id=run_id);photo_research.start_worker()
        return photo_research.progress(data.region)
    previous=latest_research(data.region,db)
    if previous and previous.status in ('failed','cancelled') and not (previous.report or {}).get('local_import'):
        previous.max_places=min(previous.max_places,data.max_places);db.commit()
        return resume_region_research(data.region,user,db)
    return start_region_research(data.region,RegionResearchInput(max_places=data.max_places),user,db)


@app.post('/api/admin/tasks/{kind}/stop')
def stop_admin_task(kind: Literal['photos','contacts','region'],data: TaskCommand,user: User=Depends(superadmin),db: Session=Depends(get_db)):
    if kind=='contacts':return contact_research.stop_work()
    if kind=='photos':return photo_research.stop_work(data.region)
    return cancel_region_research(data.region,user,db)


@app.post('/api/admin/regions',status_code=201)
def add_region(data: RegionInput,user: User = Depends(superadmin),db: Session = Depends(get_db)):
    if data.slug not in REGION_NAMES or any(kind not in PLACE_TYPES for kind in data.allowed_types) or len(set(data.allowed_types))!=len(data.allowed_types):
        raise HTTPException(422,'Wybierz województwo i poprawne rodzaje miejsc.')
    if db.get(Region,data.slug):
        raise HTTPException(409,'To województwo już istnieje.')
    db.add(Region(slug=data.slug,name=REGION_NAMES[data.slug],allowed_types=data.allowed_types,active=False))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'To województwo już istnieje.') from None
    return region_summaries(db,True)


@app.patch('/api/admin/regions/{slug}')
def publish_region(slug: str,data: RegionUpdate,user: User = Depends(superadmin),db: Session = Depends(get_db)):
    region=db.scalar(select(Region).where(Region.slug==slug).with_for_update())
    if not region:
        raise HTTPException(404,'Nie znaleziono województwa.')
    if slug=='lubuskie' and not data.active:
        raise HTTPException(422,'Podstawowe województwo musi pozostać dostępne.')
    active_job=db.scalar(select(RegionResearchJob).where(RegionResearchJob.active_region==slug))
    if active_job and not (data.active and data.finish_research):
        raise HTTPException(409,'Poczekaj na zakończenie zbierania AI albo zatrzymaj zadanie przed publikacją.')
    if data.active and not db.scalar(select(func.count()).select_from(Place).where(Place.region==slug)):
        raise HTTPException(422,'Dodaj co najmniej jedno miejsce przed publikacją.')
    if active_job:
        active_job.cancel_requested=True;active_job.status='cancelled';active_job.active_region=None;active_job.updated_at=datetime.now(timezone.utc)
    region.active=data.active
    db.commit()
    return region_summaries(db,True)


@app.get('/api/admin/regions/{slug}/places',response_model=list[PlaceOut])
def admin_places(slug: str,user: User = Depends(superadmin),db: Session = Depends(get_db)):
    return db.scalars(select(Place).where(Place.region==slug).order_by(Place.name)).all()


@app.post('/api/admin/regions/{slug}/import')
def import_region_places(slug: str,data: RegionImport,user: User = Depends(superadmin),db: Session = Depends(get_db)):
    region=db.get(Region,slug)
    if not region:
        raise HTTPException(404,'Nie znaleziono województwa.')
    def signature(p):return (p.name.strip().casefold(),round(p.lat,6),round(p.lng,6))
    existing={signature(p) for p in db.scalars(select(Place).where(Place.region==slug))}
    added=skipped=0
    for record in data.places:
        if record.place_type not in region.allowed_types:
            raise HTTPException(422,f'Rodzaj miejsca „{record.place_type}” jest wyłączony. Nie zaimportowano pliku.')
        record=record.model_copy(update={'region':slug})
        if signature(record) in existing:
            skipped+=1
            continue
        place=new_catalog_place(record,user,db)
        db.add(place);existing.add(signature(record));added+=1
    db.commit()
    return {'added':added,'skipped':skipped}


@app.put('/api/admin/places/{place_id}',response_model=PlaceOut)
def update_catalog_place(place_id: int,data: PlaceInput,user: User = Depends(superadmin),db: Session = Depends(get_db)):
    place=db.get(Place,place_id)
    if not place:
        raise HTTPException(404,'Nie znaleziono miejsca.')
    replacement=new_catalog_place(data,user,db)
    for key in ('name','subtitle','location','description','lat','lng','image','category','region'):
        if key=='image' and not data.image:
            continue
        setattr(place,key,getattr(replacement,key))
    place.details={**(place.details or {}),'kind':data.place_type,'source_url':data.source_url,'admin_managed':True}
    db.commit()
    return place


class PointPosition(BaseModel):
    id: int
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)


class CustomRoutePoint(BaseModel):
    id: int = Field(lt=0)
    name: str = Field(min_length=1, max_length=80)
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)


class TripInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    transport: Literal['bike', 'walk', 'car']
    place_ids: list[int] = Field(min_length=1, max_length=50)
    point_positions: list[PointPosition] = Field(default_factory=list, max_length=50)
    is_public: bool = False
    custom_points: list[CustomRoutePoint] = Field(default_factory=list, max_length=50)
    cover_image: str = Field(default='', max_length=900000, pattern=r'^(?:data:image/webp;base64,[A-Za-z0-9+/]+={0,2})?$')


class TripOut(TripInput):
    model_config = {'from_attributes': True}
    id: int


class RoutingInput(BaseModel):
    transport: Literal['bike', 'walk']
    place_ids: list[int] = Field(min_length=2, max_length=20)
    custom_points: list[CustomRoutePoint] = Field(default_factory=list, max_length=20)
    point_positions: list[PointPosition] = Field(default_factory=list, max_length=50)


def route_places(ids, db, custom_points=(), point_positions=()):
    if len({p.id for p in custom_points}) != len(custom_points) or any(p.id not in ids or not p.name.strip() for p in custom_points):
        raise HTTPException(422, 'Nieprawidłowe własne punkty trasy.')
    found = db.scalars(select(Place).join(Region,Region.slug==Place.region).where(Region.active.is_(True),Place.id.in_([i for i in ids if i > 0]))).all()
    lookup = {p.id: p for p in found}
    lookup.update({p.id: p for p in custom_points})
    if any(place_id not in lookup for place_id in ids):
        raise HTTPException(422, 'Plan zawiera nieistniejące miejsca.')
    validate_point_positions(ids, point_positions)
    positions = {p.id: p for p in point_positions}
    return [{'name': lookup[i].name, 'lat': positions.get(i, lookup[i]).lat, 'lng': positions.get(i, lookup[i]).lng} for i in ids]


def validate_point_positions(ids, positions):
    if len({p.id for p in positions}) != len(positions) or any(p.id not in ids for p in positions):
        raise HTTPException(422, 'Nieprawidłowe przesunięte punkty trasy.')


@app.post('/api/routing')
def routing(data: RoutingInput, db: Session = Depends(get_db)):
    return calculate_route(route_places(data.place_ids, db, data.custom_points, data.point_positions), data.transport)


def auth_response(user):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub': str(user.id), 'iat': now, 'exp': now + timedelta(hours=12), 'iss': 'perly'}, SECRET_KEY, algorithm='HS256')
    return {'access_token': token, 'token_type': 'bearer', 'user': user_profile(user)}


def user_profile(user):
    return {'id':user.id,'name':user.name,'email':user.email,'is_superadmin':bool(user.is_superadmin)}


@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return user_profile(user)


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {'status': 'ok'}


@app.post('/api/auth/register', status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    if str(data.email).lower() in bootstrap_admin_emails():
        raise HTTPException(403, 'Konto administratora wymaga konfiguracji na serwerze.')
    if not data.name.strip():
        raise HTTPException(422, 'Podaj imię.')
    user = User(email=str(data.email).lower(), name=data.name.strip(), password=password_hash.hash(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Konto z tym adresem e-mail już istnieje.')
    return auth_response(user)


@app.post('/api/auth/login')
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = password_hash.verify(data.password, user.password if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, 'Nieprawidłowy e-mail lub hasło.')
    return auth_response(user)


@app.get('/api/places', response_model=list[PlaceOut])
def places(q: str = '', category: str = '', region: str = '', db: Session = Depends(get_db), user: User | None = Depends(catalog_viewer)):
    likes = select(PlaceLike.place_id, func.count().label('count')).group_by(PlaceLike.place_id).subquery()
    comments = select(Comment.place_id, func.count().label('count')).group_by(Comment.place_id).subquery()
    query = select(Place, func.coalesce(likes.c.count, 0), func.coalesce(comments.c.count, 0)).outerjoin(likes, likes.c.place_id == Place.id).outerjoin(comments, comments.c.place_id == Place.id).order_by(Place.id)
    query = query.join(Region, Region.slug == Place.region).where(Region.active.is_(True))
    if region:
        query = query.where(Place.region == region)
    if q:
        query = query.where(or_(Place.name.ilike(f'%{q}%'), Place.subtitle.ilike(f'%{q}%'), Place.location.ilike(f'%{q}%'), Place.details['address'].as_string().ilike(f'%{q}%'), cast(Place.details['aliases'], Text).ilike(f'%{q}%')))
    if category:
        query = query.where(or_(Place.category == category, cast(Place.details, JSONB).contains({'categories': [category]})))
        if category == 'food':
            query = query.where(func.coalesce(Place.details['kind'].as_string(), '') != 'inspiration')
    own_likes = set(db.scalars(select(PlaceLike.place_id).where(PlaceLike.user_id == user.id))) if user else set()
    result = []
    for place, like_count, comment_count in db.execute(query):
        data = PlaceOut.model_validate(place).model_dump()
        data.update(like_count=like_count, comment_count=comment_count, popularity=like_count + comment_count, liked=place.id in own_likes)
        result.append(data)
    return result


class CommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


def require_place(place_id, db):
    place=db.get(Place,place_id)
    region=db.get(Region,place.region) if place else None
    if not place or not region or not region.active:
        raise HTTPException(404, 'Nie znaleziono miejsca.')


def public_comment(comment, author_name, viewer):
    return {'id': comment.id, 'body': comment.body, 'author': author_name, 'created_at': comment.created_at, 'can_delete': bool(viewer and viewer.id == comment.user_id)}


def social_counts(place_id, user, db):
    likes = db.scalar(select(func.count()).select_from(PlaceLike).where(PlaceLike.place_id == place_id))
    comments = db.scalar(select(func.count()).select_from(Comment).where(Comment.place_id == place_id))
    return {'like_count': likes, 'comment_count': comments, 'popularity': likes + comments, 'liked': bool(user and db.get(PlaceLike, (user.id, place_id)))}


@app.put('/api/places/{place_id}/like')
def like_place(place_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_place(place_id, db)
    db.execute(insert(PlaceLike).values(user_id=user.id, place_id=place_id).on_conflict_do_nothing())
    db.commit()
    return social_counts(place_id, user, db)


@app.delete('/api/places/{place_id}/like')
def unlike_place(place_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_place(place_id, db)
    like = db.get(PlaceLike, (user.id, place_id))
    if like:
        db.delete(like)
        db.commit()
    return social_counts(place_id, user, db)


@app.get('/api/places/{place_id}/community')
def place_community(place_id: int, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50), user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    require_place(place_id, db)
    comments = db.execute(select(Comment, User.name).join(User, User.id == Comment.user_id).where(Comment.place_id == place_id).order_by(Comment.created_at.desc(), Comment.id.desc()).offset(offset).limit(limit)).all()
    return {
        **social_counts(place_id, user, db),
        'visit_count': db.scalar(select(func.count()).select_from(Visit).where(Visit.place_id == place_id)),
        'visited': bool(user and db.get(Visit, (user.id, place_id))),
        'comments': [public_comment(comment, name, user) for comment, name in comments],
    }


@app.put('/api/places/{place_id}/visit', status_code=204)
def mark_visit(place_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_place(place_id, db)
    if not db.get(Visit, (user.id, place_id)):
        db.add(Visit(user_id=user.id, place_id=place_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Concurrent idempotent marks count one person once.
    return Response(status_code=204)


@app.delete('/api/places/{place_id}/visit', status_code=204)
def unmark_visit(place_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_place(place_id, db)
    visit = db.get(Visit, (user.id, place_id))
    if visit:
        db.delete(visit)
        db.commit()
    return Response(status_code=204)


@app.post('/api/places/{place_id}/comments', status_code=201)
def add_comment(place_id: int, data: CommentInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_place(place_id, db)
    body = data.body.strip()
    if not body:
        raise HTTPException(422, 'Napisz treść komentarza.')
    recent = db.scalar(select(func.count()).select_from(Comment).where(Comment.user_id == user.id, Comment.created_at >= datetime.now(timezone.utc) - timedelta(minutes=1)))
    if recent >= 5:
        raise HTTPException(429, 'Możesz dodać do 5 komentarzy na minutę. Spróbuj ponownie za chwilę.')
    comment = Comment(user_id=user.id, place_id=place_id, body=body)
    db.add(comment)
    db.commit()
    return public_comment(comment, user.name, user)


@app.delete('/api/places/{place_id}/comments/{comment_id}', status_code=204)
def delete_comment(place_id: int, comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    if not comment or comment.place_id != place_id or comment.user_id != user.id:
        raise HTTPException(404, 'Nie znaleziono Twojego komentarza.')
    db.delete(comment)
    db.commit()
    return Response(status_code=204)


@app.get('/api/favorites', response_model=list[int])
def favorites(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Favorite.place_id).where(Favorite.user_id == user.id)).all()


@app.put('/api/favorites/{place_id}', status_code=204)
def favorite(place_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Place, place_id):
        raise HTTPException(404, 'Nie znaleziono miejsca.')
    if not db.get(Favorite, (user.id, place_id)):
        db.add(Favorite(user_id=user.id, place_id=place_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Concurrent idempotent PUT.
    return Response(status_code=204)


@app.delete('/api/favorites/{place_id}', status_code=204)
def delete_favorite(place_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Favorite, (user.id, place_id))
    if row:
        db.delete(row)
        db.commit()
    return Response(status_code=204)


@app.post('/api/routes', response_model=TripOut, status_code=201)
def save_trip(data: TripInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    validate_point_positions(data.place_ids, data.point_positions)
    if not data.name.strip() or len(set(data.place_ids)) != len(data.place_ids):
        raise HTTPException(422, 'Podaj nazwę i niepowtarzające się punkty.')
    route_places(data.place_ids, db, data.custom_points, data.point_positions)
    trip = Trip(user_id=user.id, name=data.name.strip(), description=data.description.strip(), transport=data.transport, place_ids=data.place_ids)
    db.add(trip)
    trip.point_positions = [p.model_dump() for p in data.point_positions]
    trip.cover_image = data.cover_image
    trip.is_public = data.is_public
    trip.custom_points = [p.model_dump() for p in data.custom_points]
    db.commit()
    return trip


@app.get('/api/routes/public', response_model=list[TripOut])
def public_trips(db: Session = Depends(get_db)):
    return db.scalars(select(Trip).where(Trip.is_public.is_(True)).order_by(Trip.id.desc())).all()


@app.get('/api/routes', response_model=list[TripOut])
def trips(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Trip).where(Trip.user_id == user.id).order_by(Trip.id.desc())).all()


def owned_trip(trip_id, user, db):
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(404, 'Nie znaleziono planu.')
    return trip


@app.delete('/api/routes/{trip_id}', status_code=204)
def delete_trip(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_trip(trip_id, user, db))
    db.commit()
    return Response(status_code=204)


@app.put('/api/routes/{trip_id}', response_model=TripOut)
def update_trip(trip_id: int, data: TripInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = owned_trip(trip_id, user, db)
    validate_point_positions(data.place_ids, data.point_positions)
    if not data.name.strip() or len(set(data.place_ids)) != len(data.place_ids):
        raise HTTPException(422, 'Podaj nazwę i niepowtarzające się punkty.')
    route_places(data.place_ids, db, data.custom_points, data.point_positions)
    trip.name = data.name.strip()
    trip.description = data.description.strip()
    trip.transport = data.transport
    trip.place_ids = data.place_ids
    trip.point_positions = [p.model_dump() for p in data.point_positions]
    trip.cover_image = data.cover_image
    trip.is_public = data.is_public
    trip.custom_points = [p.model_dump() for p in data.custom_points]
    db.commit()
    return trip


@app.get('/api/routes/{trip_id}/gpx')
def trip_gpx(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = owned_trip(trip_id, user, db)
    if trip.transport in ('bike', 'walk') and len(trip.place_ids) >= 2:
        points = route_places(trip.place_ids, db, custom_points=[CustomRoutePoint(**p) for p in trip.custom_points], point_positions=[PointPosition(**p) for p in trip.point_positions])
        result = calculate_route(points, trip.transport)
        return Response(route_gpx(trip.name, points, result), media_type='application/gpx+xml', headers={'Content-Disposition': 'attachment; filename="perly-lubuskie.gpx"'})
    root = Element('gpx', version='1.1', creator='Perły Ziemi Lubuskiej', xmlns='http://www.topografix.com/GPX/1/1')
    metadata = SubElement(root, 'metadata')
    SubElement(metadata, 'desc').text = 'Plan punktów do odwiedzenia. Bez nawigacji po drogach.'
    route = SubElement(root, 'rte')
    SubElement(route, 'name').text = trip.name
    for place in route_places(trip.place_ids, db, custom_points=[CustomRoutePoint(**p) for p in trip.custom_points], point_positions=[PointPosition(**p) for p in trip.point_positions]):
        point = SubElement(route, 'rtept', lat=str(place['lat']), lon=str(place['lng']))
        SubElement(point, 'name').text = place['name']
    return Response(tostring(root, encoding='utf-8', xml_declaration=True), media_type='application/gpx+xml', headers={'Content-Disposition': 'attachment; filename="perly-lubuskie.gpx"'})
