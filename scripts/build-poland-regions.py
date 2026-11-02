"""Build lightweight SVG contours from the retained, openly licensed source geometry."""
import json,math
from pathlib import Path

codes=['DS','KP','LU','LB','LD','MA','MZ','OP','PK','PD','PM','SL','SK','WN','WP','ZP']
slugs=['dolnoslaskie','kujawsko-pomorskie','lubelskie','lubuskie','lodzkie','malopolskie','mazowieckie','opolskie','podkarpackie','podlaskie','pomorskie','slaskie','swietokrzyskie','warminsko-mazurskie','wielkopolskie','zachodniopomorskie']
names=['Dolnośląskie','Kujawsko-pomorskie','Lubelskie','Lubuskie','Łódzkie','Małopolskie','Mazowieckie','Opolskie','Podkarpackie','Podlaskie','Pomorskie','Śląskie','Świętokrzyskie','Warmińsko-mazurskie','Wielkopolskie','Zachodniopomorskie']
lookup={f'PL-{code}':(slug,name) for code,slug,name in zip(codes,slugs,names)}
data=json.loads(Path('public/datasets/poland-voivodeships.geojson').read_text(encoding='utf-8'))
cos=math.cos(math.radians(52))
allpoints=[p for f in data['features'] for polygon in (f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]) for ring in polygon for p in ring]
x0,x1=min(p[0]*cos for p in allpoints),max(p[0]*cos for p in allpoints)
y0,y1=min(p[1] for p in allpoints),max(p[1] for p in allpoints)
scale=min(736/(x1-x0),706/(y1-y0));dx=(760-(x1-x0)*scale)/2;dy=(730-(y1-y0)*scale)/2
def project(p):return [round((p[0]*cos-x0)*scale+dx,1),round((y1-p[1])*scale+dy,1)]
def distance(p,a,b):
    px,py=p[0]*cos,p[1];ax,ay=a[0]*cos,a[1];bx,by=b[0]*cos,b[1];den=(bx-ax)**2+(by-ay)**2
    t=max(0,min(1,((px-ax)*(bx-ax)+(py-ay)*(by-ay))/den)) if den else 0
    return math.hypot(px-ax-t*(bx-ax),py-ay-t*(by-ay))
def simplify(points):
    if len(points)<=4:return points
    distances=[distance(p,points[0],points[-1]) for p in points[1:-1]];maximum=max(distances);index=distances.index(maximum)+1
    if maximum>.004:return simplify(points[:index+1])[:-1]+simplify(points[index:])
    return [points[0],points[-1]]
def center(ring):
    projected=[project(p) for p in ring];pairs=list(zip(projected,projected[1:]))
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in pairs)/2
    return abs(area),[round(sum((a[d]+b[d])*(a[0]*b[1]-b[0]*a[1]) for a,b in pairs)/(6*area),1) for d in (0,1)]
regions=[]
for f in data['features']:
    slug,name=lookup[f['properties']['shapeISO']]
    polygons=f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]
    rings=[]
    for polygon in polygons:
        converted=[]
        for ring in polygon:
            short=simplify(ring)
            converted.append([[round(v,5) for v in p[:2]] for p in (short if len(short)>=4 else ring)])
        rings.append(converted)
    path=''.join('M'+'L'.join(','.join(str(v) for v in project(p)) for p in ring)+'Z' for polygon in rings for ring in polygon)
    centroid=max((center(p[0]) for p in rings),key=lambda c:c[0])[1]
    lines={'kujawsko-pomorskie':['Kujawsko-','pomorskie'],'warminsko-mazurskie':['Warmińsko-','mazurskie'],'zachodniopomorskie':['Zachodnio-','pomorskie']}.get(slug,[name])
    regions.append({'slug':slug,'name':name,'lines':lines,'path':path,'center':centroid,'bounds':[min(p[0] for polygon in rings for ring in polygon for p in ring),min(p[1] for polygon in rings for ring in polygon for p in ring),max(p[0] for polygon in rings for ring in polygon for p in ring),max(p[1] for polygon in rings for ring in polygon for p in ring)],'polygons':rings})
assert len(regions)==16
out=Path('src/catalog/poland-regions.json');out.write_text(json.dumps(sorted(regions,key=lambda r:r['name']),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
Path('public/datasets/poland-regions-map.json').write_text(out.read_text(encoding='utf-8'),encoding='utf-8')
print(f'Built 16 region contours, {out.stat().st_size} bytes')
