import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

import jwt
from fastapi import FastAPI, Depends, HTTPException, Response, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import create_engine, String, Text, Float, Boolean, ForeignKey, JSON, DateTime, select, func, text, or_, cast
from sqlalchemy.dialects.postgresql import insert, JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from .routing import calculate_route, route_gpx
from .maps import router as maps_router
from . import ai_routes

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    # Additive catalog migration; stable IDs preserve community data and saved trips.
    with engine.begin() as connection:
        connection.execute(text('CREATE SEQUENCE IF NOT EXISTS submitted_place_ids START WITH 1000000000'))
        connection.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS details JSON NOT NULL DEFAULT '{}'"))
        connection.execute(text('ALTER TABLE places ALTER COLUMN image TYPE TEXT'))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS description VARCHAR(2000) NOT NULL DEFAULT ''"))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS point_positions JSON NOT NULL DEFAULT '[]'"))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS cover_image TEXT NOT NULL DEFAULT ''"))
        connection.execute(text('ALTER TABLE trips ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE'))
        connection.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS custom_points JSON NOT NULL DEFAULT '[]'"))
    with SessionLocal() as db:
        data = json.loads((Path(__file__).resolve().parents[1] / 'seed.json').read_text(encoding='utf-8'))
        for place in data:
            statement = insert(Place).values(**dict(place, details=place.get('details', {})))
            statement = statement.on_conflict_do_update(index_elements=[Place.id], set_={key: getattr(statement.excluded, key) for key in place if key != 'id'})
            db.execute(statement)
        db.commit()
    yield


app = FastAPI(title='Perły Ziemi Lubuskiej API', version='1.0.0', lifespan=lifespan)
app.include_router(maps_router)
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])


@app.get('/api/ai/config')
def ai_config():
    return {'enabled': ai_routes.configured()}


@app.post('/api/ai/plan')
def ai_plan(data: ai_routes.AiRequest, request: Request, db: Session = Depends(get_db)):
    catalog = [ai_routes.catalog_entry(p)
               for p in db.scalars(select(Place).order_by(Place.id).limit(400)).all()]
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


class PlaceInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default='', max_length=250)
    location: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    place_type: Literal['castle', 'palace', 'vineyard', 'food', 'lake', 'nature', 'heritage', 'stay', 'leisure']
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    image: str = Field(default='', max_length=2000, pattern=r'^(?:https://[^\s]+)?$')


@app.post('/api/places', response_model=PlaceOut, status_code=201)
def create_place(data: PlaceInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not all(value.strip() for value in (data.name, data.location, data.description)):
        raise HTTPException(422, 'Podaj nazwę, miejscowość i opis miejsca.')
    category = {'castle': 'heritage', 'palace': 'heritage', 'lake': 'nature'}.get(data.place_type, data.place_type)
    place = Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")), name=data.name.strip(), subtitle=data.subtitle.strip(), location=data.location.strip(), description=data.description.strip(), lat=data.lat, lng=data.lng, image=data.image or '/images/heritage-placeholder.svg', category=category, rating=0, details={'kind': data.place_type, 'submitted_by': user.id})
    db.add(place)
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
    found = db.scalars(select(Place).where(Place.id.in_([i for i in ids if i > 0]))).all()
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
def places(q: str = '', category: str = '', db: Session = Depends(get_db), user: User | None = Depends(catalog_viewer)):
    likes = select(PlaceLike.place_id, func.count().label('count')).group_by(PlaceLike.place_id).subquery()
    comments = select(Comment.place_id, func.count().label('count')).group_by(Comment.place_id).subquery()
    query = select(Place, func.coalesce(likes.c.count, 0), func.coalesce(comments.c.count, 0)).outerjoin(likes, likes.c.place_id == Place.id).outerjoin(comments, comments.c.place_id == Place.id).order_by(Place.id)
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
    if not db.get(Place, place_id):
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
