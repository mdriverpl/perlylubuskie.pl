"""User-owned uploads, normalized images and atomic attachment to a place."""
from datetime import datetime,timedelta,timezone
from io import BytesIO
import warnings
from fastapi import HTTPException
from PIL import Image,ImageOps,UnidentifiedImageError
from sqlalchemy import select,delete,func

MAX_BYTES=10*1024*1024
MAX_PHOTOS=5


def normalize_photo(content):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format not in ('JPEG','PNG','WEBP') or getattr(image,'n_frames',1)!=1:
                    raise ValueError('format')
                if image.width*image.height>20_000_000:raise ValueError('dimensions')
                image=ImageOps.exif_transpose(image)
                image.thumbnail((1600,1600))
                if image.mode in ('RGBA','LA') or 'transparency' in image.info:
                    rgba=image.convert('RGBA');clean=Image.new('RGB',rgba.size,'white');clean.paste(rgba,mask=rgba.getchannel('A'))
                else:clean=image.convert('RGB')
                # Re-encode pixels only: filenames, EXIF/GPS and other metadata are discarded.
                output=BytesIO();clean.save(output,format='WEBP',quality=84)
                return output.getvalue()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombWarning,Image.DecompressionBombError):
        raise HTTPException(422,'Wybierz poprawne zdjęcie JPG, PNG lub WebP, do 20 megapikseli.')


def stage_photo(db,user,content):
    from .main import User,PlacePhoto
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    now=datetime.now(timezone.utc)
    db.execute(delete(PlacePhoto).where(PlacePhoto.place_id.is_(None),PlacePhoto.created_at<now-timedelta(hours=24)))
    pending=db.scalar(select(func.count()).select_from(PlacePhoto).where(PlacePhoto.user_id==user.id,PlacePhoto.place_id.is_(None)))
    recent=db.scalar(select(func.count()).select_from(PlacePhoto).where(PlacePhoto.user_id==user.id,PlacePhoto.created_at>now-timedelta(hours=1)))
    if pending>=20 or recent>=30:raise HTTPException(429,'Limit przesyłania zdjęć został osiągnięty. Spróbuj ponownie później.')
    photo=PlacePhoto(user_id=user.id,content=content);db.add(photo);db.commit()
    return {'id':photo.id}


def attach_photos(db,place,user,photo_ids,rights_confirmed):
    from .main import PlacePhoto
    if not photo_ids:return
    if not rights_confirmed:raise HTTPException(422,'Potwierdź, że masz prawo opublikować te zdjęcia.')
    if len(set(photo_ids))!=len(photo_ids):raise HTTPException(422,'Nie dodawaj tego samego zdjęcia dwukrotnie.')
    existing=list((place.details or {}).get('user_photos') or [])
    if len(existing)+len(photo_ids)>MAX_PHOTOS:raise HTTPException(422,'Miejsce może mieć do 5 przesłanych zdjęć.')
    rows=list(db.scalars(select(PlacePhoto).where(PlacePhoto.id.in_(photo_ids)).order_by(PlacePhoto.id).with_for_update()))
    by_id={photo.id:photo for photo in rows}
    if len(rows)!=len(photo_ids) or any(p.user_id!=user.id or p.place_id is not None for p in rows):
        raise HTTPException(422,'Zdjęcie jest niedostępne. Wybierz plik ponownie.')
    for photo_id in photo_ids:
        photo=by_id[photo_id];photo.place_id=place.id
        existing.append({'id':photo.id,'url':f'/api/place-photos/{photo.id}.webp','author':user.name,'uploaded_at':photo.created_at.isoformat()})
    place.details={**(place.details or {}),'user_photos':existing}
    place.image=existing[0]['url']
