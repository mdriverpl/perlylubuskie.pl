"""Import reviewed, repository-packaged regional data without replacing existing places."""
import hashlib
import json
import logging
import math
import re
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import select,text,func

logger=logging.getLogger('uvicorn.error')


def import_catalogs(directory=None):
    from .main import SessionLocal,Region,Place,RegionResearchJob,REGION_NAMES,CORE_TYPES
    from .region_research import existing_place
    root=Path(directory) if directory else Path(__file__).resolve().parents[1]/'region-catalogs'
    results=[]
    for path in sorted(root.glob('*.json')):
        raw=path.read_bytes();version=hashlib.sha256(raw).hexdigest();catalog=json.loads(raw)
        slug=catalog['region'];records=catalog['places']
        if slug not in REGION_NAMES or not isinstance(records,list):raise ValueError('Invalid local region catalog')
        for record in records:
            if not re.fullmatch(r'wd:Q[1-9][0-9]*',record['research_key']) or record['details'].get('wikidata')!=record['research_key'][3:]:raise ValueError('Invalid local catalog identity')
            if record['region']!=slug or record['details']['kind'] not in CORE_TYPES:raise ValueError('Invalid local catalog type')
            if not all(isinstance(record[k],(int,float)) and math.isfinite(record[k]) for k in ('lat','lng')) or not 49<=record['lat']<=55 or not 14<=record['lng']<=24.2:raise ValueError('Invalid local catalog coordinates')
            if not record['details'].get('sources') or len(record['name'])>200 or len(record['description'])>2000:raise ValueError('Invalid local catalog evidence')
            if record.get('image') and not record['image'].startswith('/images/'):raise ValueError('Invalid local catalog image')
        with SessionLocal() as db:
            db.execute(text('CREATE TABLE IF NOT EXISTS local_catalog_imports (region VARCHAR(40) PRIMARY KEY,version VARCHAR(64) NOT NULL,imported_at TIMESTAMPTZ NOT NULL DEFAULT now())'))
            if db.scalar(text('SELECT version FROM local_catalog_imports WHERE region=:region'),{'region':slug})==version:
                db.commit();continue
            region=db.scalar(select(Region).where(Region.slug==slug).with_for_update())
            if not region:
                region=Region(slug=slug,name=REGION_NAMES[slug],active=False,allowed_types=list(CORE_TYPES));db.add(region);db.flush()
            added=updated=skipped=0
            for record in records:
                if record['details']['kind'] not in region.allowed_types:skipped+=1;continue
                candidate={'source_key':record['research_key'],'wikidata':record['details']['wikidata'],'name':record['name'],'lat':record['lat'],'lng':record['lng']}
                previous=existing_place(db,slug,candidate)
                if previous:
                    skipped+=1
                    if not previous.details.get('admin_managed') and previous.image.endswith('placeholder.svg') and record['details'].get('photo'):
                        previous.image=record['image'];previous.details={**previous.details,'photo':record['details']['photo']};updated+=1
                    continue
                place=Place(id=db.scalar(text("SELECT nextval('submitted_place_ids')")),**record);db.add(place);db.flush();added+=1
            total=db.scalar(select(func.count()).select_from(Place).where(Place.region==slug))
            for index,job in enumerate(db.scalars(select(RegionResearchJob).where(RegionResearchJob.region==slug).order_by(RegionResearchJob.created_at.desc()))):
                active=job.status in ('queued','running')
                if active:job.cancel_requested=True;job.status='cancelled';job.active_region=None;job.updated_at=datetime.now(timezone.utc)
                if active or index==0:job.report={**(job.report or {}),'local_import':{'added':added,'updated':updated,'skipped':skipped,'total':total},'message':'Katalog uzupełniono lokalnie. Możesz opublikować zapisane miejsca.'}
            db.execute(text('INSERT INTO local_catalog_imports(region,version) VALUES (:region,:version) ON CONFLICT(region) DO UPDATE SET version=EXCLUDED.version,imported_at=now()'),{'region':slug,'version':version})
            db.commit();result={'region':slug,'added':added,'updated':updated,'skipped':skipped,'total':total};results.append(result)
            logger.info('Local catalog imported region=%s added=%s updated=%s skipped=%s total=%s',slug,added,updated,skipped,total)
    return results
