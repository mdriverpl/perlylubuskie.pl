"""Opt-in current positions, visible only to other active nearby participants."""
import logging
import math
import threading
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, update, func, case
from sqlalchemy.dialects.postgresql import insert

TTL_SECONDS = 120
MAX_FIX_AGE_SECONDS = 60


class PositionInput(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy: float = Field(ge=0, le=100, allow_inf_nan=False)
    measured_at: datetime
    transport: Literal['walk', 'bike'] = 'walk'


class PositionUpdate(PositionInput):
    session_id: UUID


class PositionStop(BaseModel):
    session_id: UUID


class GuestPositionInput(PositionInput):
    nick: str = Field(min_length=2, max_length=32)


def now_utc():
    return datetime.now(timezone.utc)


def check_fix(data, now):
    if data.measured_at.utcoffset() is None or not -30 <= (now-data.measured_at).total_seconds() <= MAX_FIX_AGE_SECONDS:
        raise HTTPException(422, 'Pozycja GPS jest nieaktualna. Odśwież lokalizację.')


def private(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['Pragma'] = 'no-cache'


def purge_expired(db, *models):
    for model in models:
        db.execute(delete(model).where(model.expires_at <= now_utc()))


def start_cleanup(SessionLocal, *models):
    stopped = threading.Event()
    def run():
        while not stopped.wait(30):
            try:
                with SessionLocal() as db:
                    purge_expired(db, *models)
                    db.commit()
            except Exception:
                logging.getLogger('uvicorn.error').warning('Live location cleanup will retry.')
    threading.Thread(target=run, daemon=True, name='live-location-cleanup').start()
    return stopped


def router_for(Location, User, get_db, current_user, Guest=None):
    router = APIRouter(prefix='/api/live-location')

    def distance_from(model, own):
        dlat = func.sin(func.radians(model.lat-own.lat)/2)
        dlng = func.sin(func.radians(model.lng-own.lng)/2)
        h = dlat*dlat+math.cos(math.radians(own.lat))*func.cos(func.radians(model.lat))*dlng*dlng
        return 6371000*2*func.asin(func.sqrt(case((h < 0, 0), (h > 1, 1), else_=h)))

    def nearby_people(db, own, radius_km, own_user=None, own_guest=None, include_accounts=True):
        distance = distance_from(Location, own)
        query = select(Location, User.name, distance.label('distance_m')).join(User, User.id == Location.user_id).where(Location.expires_at > now_utc(), distance <= radius_km*1000)
        if own_user is not None:
            query = query.where(Location.user_id != own_user)
        rows = [(location, name, meters, location.user_id) for location, name, meters in db.execute(query.order_by(distance, Location.user_id).limit(100))] if include_accounts else []
        if Guest is not None:
            guest_distance = distance_from(Guest, own)
            query = select(Guest, guest_distance.label('distance_m')).where(Guest.expires_at > now_utc(), guest_distance <= radius_km*1000)
            if own_guest is not None:
                query = query.where(Guest.id != own_guest)
            rows += [(location, location.nick, meters, 'guest:'+location.id) for location, meters in db.execute(query.order_by(guest_distance, Guest.id).limit(100))]
        rows.sort(key=lambda row: (row[2], str(row[3])))
        return {'radius_km': radius_km, 'ttl_seconds': TTL_SECONDS, 'people': [
            {'id': public_id, 'name': name, 'lat': location.lat, 'lng': location.lng,
             'accuracy': location.accuracy, 'transport': location.transport, 'distance_m': round(meters),
             'updated_at': location.updated_at, 'expires_at': location.expires_at}
            for location, name, meters, public_id in rows[:100]
        ]}

    @router.post('')
    def start(data: PositionInput, response: Response, user=Depends(current_user), db=Depends(get_db)):
        private(response)
        now = now_utc()
        check_fix(data, now)
        purge_expired(db, Location)
        values = dict(user_id=user.id, session_id=str(uuid4()), lat=data.lat, lng=data.lng, accuracy=data.accuracy, transport=data.transport,
                      measured_at=data.measured_at, updated_at=now, expires_at=now+timedelta(seconds=TTL_SECONDS))
        # One position per account, across devices and server workers.
        statement = insert(Location).values(**values)
        statement = statement.on_conflict_do_update(index_elements=[Location.user_id], set_={key: value for key, value in values.items() if key != 'user_id'})
        db.execute(statement)
        db.commit()
        return {'session_id': values['session_id'], 'expires_at': values['expires_at'], 'ttl_seconds': TTL_SECONDS}

    @router.put('')
    def publish(data: PositionUpdate, response: Response, user=Depends(current_user), db=Depends(get_db)):
        private(response)
        now = now_utc()
        check_fix(data, now)
        # A delayed update cannot recreate a stopped session or replace another device.
        changed = db.execute(update(Location).where(Location.user_id == user.id, Location.session_id == str(data.session_id), Location.expires_at > now, Location.measured_at <= data.measured_at).values(
            lat=data.lat, lng=data.lng, accuracy=data.accuracy, transport=data.transport, measured_at=data.measured_at,
            updated_at=now, expires_at=now+timedelta(seconds=TTL_SECONDS)))
        if not changed.rowcount:
            raise HTTPException(409, 'Udostępnianie wygasło lub pozycja jest starsza od ostatniej aktualizacji.')
        db.commit()
        return {'expires_at': now+timedelta(seconds=TTL_SECONDS), 'ttl_seconds': TTL_SECONDS}

    @router.delete('', status_code=204)
    def stop(data: PositionStop, response: Response, user=Depends(current_user), db=Depends(get_db)):
        private(response)
        db.execute(delete(Location).where(Location.user_id == user.id, Location.session_id == str(data.session_id)))
        db.commit()

    @router.get('/nearby')
    def nearby(response: Response, radius_km: float = Query(5, ge=.1, le=10, allow_inf_nan=False), user=Depends(current_user), db=Depends(get_db)):
        private(response)
        now = now_utc()
        own = db.scalar(select(Location).where(Location.user_id == user.id, Location.expires_at > now))
        if not own:
            raise HTTPException(403, 'Włącz udostępnianie swojej pozycji, aby zobaczyć osoby w pobliżu.')
        return nearby_people(db, own, radius_km, own_user=user.id)

    if Guest is not None:
        def guest_session(db, token, require_active=True):
            if not token or not 20 <= len(token) <= 200:
                raise HTTPException(401, 'Brak aktywnej sesji udostępniania.')
            query = select(Guest).where(Guest.token_hash == hashlib.sha256(token.encode()).hexdigest())
            if require_active:
                query = query.where(Guest.expires_at > now_utc())
            guest = db.scalar(query)
            if not guest:
                raise HTTPException(401, 'Sesja udostępniania wygasła.')
            return guest

        @router.post('/guest')
        def start_guest(data: GuestPositionInput, response: Response, db=Depends(get_db)):
            private(response)
            now = now_utc()
            check_fix(data, now)
            nick = data.nick.strip()
            if len(nick) < 2 or any(ord(c) < 32 for c in nick):
                raise HTTPException(422, 'Wpisz nick od 2 do 32 znaków.')
            purge_expired(db, Guest)
            if db.scalar(select(func.count()).select_from(Guest)) >= 5000:
                raise HTTPException(503, 'Udostępnianie jest chwilowo zajęte. Spróbuj później.')
            token = secrets.token_urlsafe(32)
            guest = Guest(id=str(uuid4()), token_hash=hashlib.sha256(token.encode()).hexdigest(), nick=nick,
                          lat=data.lat, lng=data.lng, accuracy=data.accuracy, transport=data.transport, measured_at=data.measured_at,
                          updated_at=now, expires_at=now+timedelta(seconds=TTL_SECONDS))
            db.add(guest);db.commit()
            return {'session_id': guest.id, 'guest_token': token, 'expires_at': guest.expires_at, 'ttl_seconds': TTL_SECONDS}

        @router.put('/guest')
        def update_guest(data: PositionUpdate, response: Response, x_location_token: str | None = Header(default=None), db=Depends(get_db)):
            private(response)
            now = now_utc();check_fix(data, now)
            guest = guest_session(db, x_location_token)
            changed = db.execute(update(Guest).where(Guest.id == guest.id, Guest.id == str(data.session_id), Guest.expires_at > now, Guest.measured_at <= data.measured_at).values(lat=data.lat, lng=data.lng, accuracy=data.accuracy, transport=data.transport, measured_at=data.measured_at, updated_at=now, expires_at=now+timedelta(seconds=TTL_SECONDS)).execution_options(synchronize_session=False))
            if not changed.rowcount:
                raise HTTPException(409, 'Nieaktualna sesja lub pozycja GPS.')
            db.commit()
            return {'expires_at': now+timedelta(seconds=TTL_SECONDS), 'ttl_seconds': TTL_SECONDS}

        @router.delete('/guest', status_code=204)
        def stop_guest(data: PositionStop, response: Response, x_location_token: str | None = Header(default=None), db=Depends(get_db)):
            private(response)
            guest = guest_session(db, x_location_token, require_active=False)
            db.execute(delete(Guest).where(Guest.id == guest.id, Guest.id == str(data.session_id)))
            db.commit()

        @router.get('/guest/nearby')
        def guest_nearby(response: Response, radius_km: float = Query(5, ge=.1, le=10, allow_inf_nan=False), x_location_token: str | None = Header(default=None), db=Depends(get_db)):
            private(response)
            guest = guest_session(db, x_location_token)
            # Legacy account sessions opted into an account-only audience. A guest
            # must never widen that audience without a fresh nickname opt-in.
            return nearby_people(db, guest, radius_km, own_guest=guest.id, include_accounts=False)

    return router
