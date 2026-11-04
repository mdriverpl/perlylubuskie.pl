"""Render factual lake map crops from the regional OSM extract, not public tiles.

Requires Pillow and shapely; run extract-lake-map-context.py beforehand. Real
photographs are retained by the API importer; this builds fallback map images.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape,Point,box
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.lake_catalog import source_keys,names

parser=argparse.ArgumentParser()
parser.add_argument('--limit',type=int,default=0)
parser.add_argument('--key',default='')
args=parser.parse_args()
source=ROOT/'.tools/lubuskie-lakes-sources'
catalog=json.loads((ROOT/'backend/lake-catalogs/lubuskie.json').read_text(encoding='utf-8'))
baseline=json.loads((source/'production-before-map-previews.json').read_text(encoding='utf-8'))
missing=[p for p in baseline if not p.get('image') or p['image'].endswith('placeholder.svg')]
eligible=set().union(*(source_keys(p) for p in missing))
targets=[p for p in catalog['places'] if source_keys(p)&eligible]
if args.key:targets=[p for p in targets if args.key in source_keys(p)]
if args.limit:targets=targets[:args.limit]
context=json.loads((source/'map-context.json').read_text(encoding='utf-8'))
features=context['features'];geometries=[shape(f['geometry']) for f in features]
tree=STRtree(geometries)
water_indices=[i for i,f in enumerate(features) if f['kind']=='water']
water_by_key={f.get('osm_key'):i for i,f in enumerate(features) if f['kind']=='water'}
width,height=1200,800
R=6378137


def mercator(lng,lat):return R*math.radians(lng),R*math.log(math.tan(math.pi/4+math.radians(lat)/2))
def inverse(x,y):return math.degrees(x/R),math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)


def font(size,bold=False):
    for path in ([ROOT/'.tools/fonts/DejaVuSans-Bold.ttf',Path('C:/Windows/Fonts/arialbd.ttf')] if bold else [ROOT/'.tools/fonts/DejaVuSans.ttf',Path('C:/Windows/Fonts/arial.ttf')]):
        if path.exists():return ImageFont.truetype(str(path),size)
    return ImageFont.load_default(size=size)


fonts={key:font(size,bold) for key,size,bold in [('name',25,True),('town',20,True),('village',17,False),('small',16,False),('badge',16,True)]}
colors={'forest':'#bdd2b0','wood':'#bdd2b0','scrub':'#cedcbd','meadow':'#e0e9cf','grass':'#dce8ce','farmland':'#eff0dc','orchard':'#d4e2c6','residential':'#e8e6df','industrial':'#e1e1db','allotments':'#d9e4cd'}
background='#f3f2e9'


def target_geometry(record):
    for key in source_keys(record):
        if key in water_by_key:return geometries[water_by_key[key]]
    point=Point(record['lng'],record['lat']);nearby=tree.query(point.buffer(.03))
    candidates=[]
    for raw_index in nearby:
        index=int(raw_index)
        if features[index]['kind']!='water':continue
        geometry=geometries[index]
        matching=bool(names(record)&names({'name':features[index].get('name',''),'details':{}}))
        if geometry.covers(point) or matching and geometry.distance(point)<.02:candidates.append((not matching,geometry.distance(point),index))
    return geometries[min(candidates)[2]] if candidates else None


def view(record,target):
    if target:
        west,south,east,north=target.bounds
        left,bottom=mercator(west,south);right,top=mercator(east,north)
        cx,cy=(left+right)/2,(bottom+top)/2
        span=max((right-left)*1.48,(top-bottom)*1.55*width/height,260/math.cos(math.radians(record['lat'])))
    else:
        cx,cy=mercator(record['lng'],record['lat']);span=2000/math.cos(math.radians(record['lat']))
    return cx-span/2,cy-span*height/width/2,cx+span/2,cy+span*height/width/2


def render(record):
    target=target_geometry(record);left,bottom,right,top=view(record,target)
    west,south=inverse(left,bottom);east,north=inverse(right,top)
    viewport=box(west,south,east,north)
    indices=[int(i) for i in tree.query(viewport)]
    indices.sort(key=lambda i:({'land':0,'water':1,'road':2,'building':3}[features[i]['kind']],i))
    image=Image.new('RGB',(width,height),background);draw=ImageDraw.Draw(image)
    def pixel(coord):
        x,y=mercator(coord[0],coord[1]);return ((x-left)/(right-left)*width,(top-y)/(top-bottom)*height)
    def polygon(poly,color,outline=None):
        points=[pixel(c) for c in poly.exterior.coords]
        if not poly.interiors:draw.polygon(points,fill=color)
        else:
            mask=Image.new('L',(width,height));md=ImageDraw.Draw(mask);md.polygon(points,fill=255)
            for ring in poly.interiors:md.polygon([pixel(c) for c in ring.coords],fill=0)
            image.paste(color,(0,0),mask)
        if outline:draw.line(points,fill=outline,width=3,joint='curve')
    def paint(geometry,color,outline=None):
        if geometry.is_empty:return
        if geometry.geom_type=='Polygon':polygon(geometry,color,outline)
        elif geometry.geom_type in ('MultiPolygon','GeometryCollection'):
            for part in geometry.geoms:paint(part,color,outline)
    ground_width=(right-left)*math.cos(math.radians(record['lat']))
    target_drawn=False
    for index in indices:
        feature=features[index];kind=feature['kind']
        if kind in ('road','building') and not target_drawn:
            if target:paint(target.intersection(viewport),'#9ccfe2','#4e93ad')
            target_drawn=True
        if kind=='building' and ground_width>5000:continue
        geometry=geometries[index].intersection(viewport)
        geometry=geometry.simplify((east-west)/2500,preserve_topology=True)
        if kind=='land':paint(geometry,colors.get(feature['subtype'],'#e5e9d5'))
        elif kind=='water':paint(geometry,'#afd4e1')
        elif kind=='building':paint(geometry,'#d5d0c6')
        elif kind=='road':
            paths=list(geometry.geoms) if geometry.geom_type=='MultiLineString' else [geometry]
            primary=feature['subtype'] in ('motorway','trunk','primary','secondary','tertiary')
            for path in paths:
                if path.geom_type!='LineString':continue
                points=[pixel(c) for c in path.coords]
                if len(points)<2:continue
                draw.line(points,fill='#d6d1c3' if primary else '#d5d5c8',width=8 if primary else 4,joint='curve')
                draw.line(points,fill='#fff5c2' if primary else '#fffdf7',width=5 if primary else 2,joint='curve')
    if target and not target_drawn:paint(target.intersection(viewport),'#9ccfe2','#4e93ad')
    used=[]
    def text(position,value,f,color,halo=True):
        draw.text(position,value,font=f,fill=color,stroke_width=3 if halo else 0,stroke_fill='#fafaf6')
    settlements=[p for p in context['places'] if west<p['lng']<east and south<p['lat']<north]
    settlements.sort(key=lambda p:({'city':0,'town':1,'village':2,'hamlet':3}[p['kind']],(p['lat']-record['lat'])**2+(p['lng']-record['lng'])**2))
    for place in settlements[:15]:
        x,y=pixel((place['lng'],place['lat']));f=fonts['town'] if place['kind'] in ('city','town') else fonts['village']
        bounds=draw.textbbox((x,y),place['name'],font=f,stroke_width=3)
        if x<35 or y<120 or bounds[2]>width-35 or bounds[3]>height-130:continue
        if any(not(bounds[2]+20<b[0] or bounds[0]-20>b[2] or bounds[3]+15<b[1] or bounds[1]-15>b[3]) for b in used):continue
        text((x,y),place['name'],f,'#596554');used.append(bounds)
    x,y=pixel((record['lng'],record['lat']));x=max(50,min(width-50,x));y=max(170,min(height-180,y))
    draw.ellipse((x-10,y-10,x+10,y+10),fill='#19744f',outline='white',width=3)
    label=record['name'] if not record['details']['lake_catalog'].get('unnamed') else 'Jezioro'
    label_width=draw.textlength(label,font=fonts['name'])
    text((max(35,min(width-label_width-35,x-label_width/2)),y+17),label,fonts['name'],'#22556e')
    # Place attribution inside the safe crop area as well as in the image metadata/UI.
    badge='PODGLĄD MAPY';credit='© OpenStreetMap contributors · ODbL'
    draw.rounded_rectangle((30,110,220,147),radius=10,fill='#fffef5')
    draw.text((43,120),badge,font=fonts['badge'],fill='#2e6849')
    credit_width=draw.textlength(credit,font=fonts['small'])
    draw.rounded_rectangle((width-credit_width-54,height-145,width-30,height-105),radius=7,fill='#fffef5')
    draw.text((width-credit_width-42,height-135),credit,font=fonts['small'],fill='#536050')
    # Ground-distance scale, accounting for Mercator distortion at this latitude.
    distance=next((v for v in [5000,2000,1000,500,250,100,50,25,10] if v<ground_width*.22),10)
    bar=distance/ground_width*width
    draw.line((40,height-117,40+bar,height-117),fill='#566352',width=3)
    draw.line((40,height-123,40,height-112),fill='#566352',width=2);draw.line((40+bar,height-123,40+bar,height-112),fill='#566352',width=2)
    text((40,height-147),f'{distance//1000} km' if distance>=1000 else f'{distance} m',fonts['small'],'#566352')
    return image,[west,south,east,north],bool(target)


output=ROOT/'public/images/lake-maps';output.mkdir(parents=True,exist_ok=True)
version=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
manifest=[]
for index,record in enumerate(targets):
    image,bounds,geometry=render(record)
    key=hashlib.sha256((record['research_key']+catalog['extract_sha256']+version).encode()).hexdigest()[:24]
    path=output/(key+'.webp');image.save(path,'WEBP',quality=86,method=6)
    url='/images/lake-maps/'+path.name
    manifest.append({'research_key':record['research_key'],'name':record['name'],'lat':record['lat'],'lng':record['lng'],
                     'details':record['details'],'image':url,'map_preview':{'image':url,'kind':'map','bounds':bounds,
                     'source_url':f"https://www.openstreetmap.org/?mlat={record['lat']}&mlon={record['lng']}#map=16/{record['lat']}/{record['lng']}",
                     'license':'Dane OpenStreetMap contributors — ODbL 1.0','license_url':'https://www.openstreetmap.org/copyright',
                     'attribution':'© OpenStreetMap contributors','geometry_available':geometry,'render_version':version}})
    if (index+1)%25==0:print(f'Rendered {index+1}/{len(targets)}',flush=True)
manifest_path=ROOT/('backend/lake-map-previews.json' if not args.limit and not args.key else '.tools/lake-map-preview-sample.json')
manifest_path.write_text(json.dumps({'region':'lubuskie','previews':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'rendered':len(manifest),'without_exact_geometry':sum(not p['map_preview']['geometry_available'] for p in manifest),'files_bytes':sum((ROOT/'public'/p['image'].lstrip('/')).stat().st_size for p in manifest)},ensure_ascii=True))
