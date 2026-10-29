import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

import jwt
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import create_engine, String, Float, ForeignKey, JSON, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg://perly:perly@localhost:5432/perly')
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if len(SECRET_KEY) < 32:
    raise RuntimeError('Ustaw SECRET_KEY o długości co najmniej 32 znaków.')
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
password_hash = PasswordHash.recommended()
security = HTTPBearer()
DUMMY_HASH = password_hash.hash('invalid-account-timing-placeholder')


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password: Mapped[str] = mapped_column(String(255))


class Place(Base):
    __tablename__ = 'places'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(30), index=True)
    image: Mapped[str] = mapped_column(String(250))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))


class Favorite(Base):
    __tablename__ = 'favorites'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey('places.id', ondelete='CASCADE'), primary_key=True)


class Trip(Base):
    __tablename__ = 'trips'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    transport: Mapped[str] = mapped_column(String(20))
    place_ids: Mapped[list[int]] = mapped_column(JSON)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initial schema for the starter. Introduce Alembic before changing an existing production schema.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(Place.id).limit(1)):
            data = json.loads((Path(__file__).resolve().parents[1] / 'seed.json').read_text(encoding='utf-8'))
            db.add_all(Place(**p) for p in data)
            db.commit()
    yield


app = FastAPI(title='Perły Ziemi Lubuskiej API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])


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


class TripInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    transport: Literal['bike', 'walk', 'car']
    place_ids: list[int] = Field(min_length=1, max_length=50)


class TripOut(TripInput):
    model_config = {'from_attributes': True}
    id: int


def auth_response(user):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub': str(user.id), 'iat': now, 'exp': now + timedelta(hours=12), 'iss': 'perly'}, SECRET_KEY, algorithm='HS256')
    return {'access_token': token, 'token_type': 'bearer', 'user': {'id': user.id, 'name': user.name, 'email': user.email}}


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {'status': 'ok'}


@app.post('/api/auth/register', status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
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
def places(q: str = '', category: str = '', db: Session = Depends(get_db)):
    query = select(Place).order_by(Place.id)
    if q:
        query = query.where(Place.name.ilike(f'%{q}%'))
    if category:
        query = query.where(Place.category == category)
    return db.scalars(query).all()


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
    if not data.name.strip() or len(set(data.place_ids)) != len(data.place_ids):
        raise HTTPException(422, 'Podaj nazwę i niepowtarzające się punkty.')
    found = db.scalars(select(Place.id).where(Place.id.in_(data.place_ids))).all()
    if len(found) != len(data.place_ids):
        raise HTTPException(422, 'Plan zawiera nieistniejące miejsca.')
    trip = Trip(user_id=user.id, name=data.name.strip(), transport=data.transport, place_ids=data.place_ids)
    db.add(trip)
    db.commit()
    return trip


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


@app.get('/api/routes/{trip_id}/gpx')
def trip_gpx(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = owned_trip(trip_id, user, db)
    root = Element('gpx', version='1.1', creator='Perły Ziemi Lubuskiej', xmlns='http://www.topografix.com/GPX/1/1')
    metadata = SubElement(root, 'metadata')
    SubElement(metadata, 'desc').text = 'Plan punktów do odwiedzenia. Bez nawigacji po drogach.'
    route = SubElement(root, 'rte')
    SubElement(route, 'name').text = trip.name
    for place_id in trip.place_ids:
        place = db.get(Place, place_id)
        if place:
            point = SubElement(route, 'rtept', lat=str(place.lat), lon=str(place.lng))
            SubElement(point, 'name').text = place.name
    return Response(tostring(root, encoding='utf-8', xml_declaration=True), media_type='application/gpx+xml', headers={'Content-Disposition': 'attachment; filename="perly-lubuskie.gpx"'})
