"""Import factual map crops as fallbacks while preserving actual photographs."""
import json
import logging
import re
from pathlib import Path
from sqlalchemy import select
from .lake_catalog import source_keys,as_record,same_lake

logger=logging.getLogger('uvicorn.error')


def is_map_image(image,details):
    return bool(image and image.startswith('/images/lake-maps/'))


def has_photo(image,details):
    return bool(image and not image.endswith('placeholder.svg') and not is_map_image(image,details))


def import_previews(path=None):
    from .main import SessionLocal,Region,Place
    path=Path(path) if path else Path(__file__).resolve().parents[1]/'lake-map-previews.json'
    if not path.exists():return {'updated':0,'preserved':0}
    data=json.loads(path.read_text(encoding='utf-8'))
    for preview in data['previews']:
        if not re.fullmatch(r'/images/lake-maps/[a-f0-9]{24}\.webp',preview['image']):raise ValueError('Invalid map image path')
        if preview['map_preview'].get('image')!=preview['image'] or preview['map_preview'].get('kind')!='map':raise ValueError('Invalid map attribution')
        if not preview['map_preview'].get('attribution') or not preview['map_preview'].get('source_url','').startswith('https://www.openstreetmap.org/'):raise ValueError('Missing map source')
    updated=preserved=0
    with SessionLocal() as db:
        if not db.scalar(select(Region).where(Region.slug==data['region']).with_for_update()):return {'updated':0,'preserved':0}
        places=list(db.scalars(select(Place).where(Place.region==data['region'],Place.details['kind'].as_string()=='lake')))
        index={key:p for p in places for key in source_keys(as_record(p))}
        for preview in data['previews']:
            place=next((index[key] for key in sorted(source_keys(preview)) if key in index),None)
            if not place:place=next((p for p in places if same_lake(preview,as_record(p))),None)
            if not place:continue
            place=db.scalar(select(Place).where(Place.id==place.id).with_for_update().execution_options(populate_existing=True))
            if has_photo(place.image,place.details):preserved+=1;continue
            if place.image==preview['image'] and (place.details or {}).get('map_preview')==preview['map_preview']:continue
            place.image=preview['image'];place.details={**(place.details or {}),'map_preview':preview['map_preview']};updated+=1
        db.commit()
    logger.info('Lake map previews imported region=%s updated=%s preserved_photos=%s',data['region'],updated,preserved)
    return {'updated':updated,'preserved':preserved}
