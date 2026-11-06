"""Opt-in current positions, visible only to other active nearby participants."""
import logging
import math
import threading
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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


class PositionUpdate(PositionInput):
    session_id: UUID


class PositionStop(BaseModel):
    session_id: UUID


def now_utc():
    return datetime.now(timezone.utc)


def check_fix(data, now):
    if data.measured_at.utcoffset() is None or not -30 <= (now-data.measured_at).total_seconds() <= MAX_FIX_AGE_SECONDS:
        raise HTTPException(422, 'Pozycja GPS jest nieaktualna. Odśwież lokalizację.')


def private(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['Pragma'] = 'no-cache'


def purge_expired(db, Location):
    db.execute(delete(Location).where(Location.expires_at <= now_utc()))


def start_cleanup(SessionLocal, Location):
    stopped = threading.Event()
    def run():
        while not stopped.wait(30):
            try:
                with SessionLocal() as db:
                    purge_expired(db, Location)
                    db.commit()
            except Exception:
                logging.getLogger('uvicorn.error').warning('Live location cleanup will retry.')
    threading.Thread(target=run, daemon=True, name='live-location-cleanup').start()
    return stopped


def router_for(Location, User, get_db, current_user):
    router = APIRouter(prefix='/api/live-location')

    @router.post('')
    def start(data: PositionInput, response: Response, user=Depends(current_user), db=Depends(get_db)):
        private(response)
        now = now_utc()
        check_fix(data, now)
        purge_expired(db, Location)
        values = dict(user_id=user.id, session_id=str(uuid4()), lat=data.lat, lng=data.lng, accuracy=data.accuracy,
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
            lat=data.lat, lng=data.lng, accuracy=data.accuracy, measured_at=data.measured_at,
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
        dlat = func.sin(func.radians(Location.lat-own.lat)/2)
        dlng = func.sin(func.radians(Location.lng-own.lng)/2)
        h = dlat*dlat+math.cos(math.radians(own.lat))*func.cos(func.radians(Location.lat))*dlng*dlng
        distance = 6371000*2*func.asin(func.sqrt(case((h < 0, 0), (h > 1, 1), else_=h)))
        rows = db.execute(select(Location, User.name, distance.label('distance_m')).join(User, User.id == Location.user_id).where(
            Location.user_id != user.id, Location.expires_at > now, distance <= radius_km*1000
        ).order_by(distance, Location.user_id).limit(100)).all()
        return {'radius_km': radius_km, 'ttl_seconds': TTL_SECONDS, 'people': [
            {'id': location.user_id, 'name': name, 'lat': location.lat, 'lng': location.lng,
             'accuracy': location.accuracy, 'distance_m': round(meters),
             'updated_at': location.updated_at, 'expires_at': location.expires_at}
            for location, name, meters in rows
        ]}

    return router
