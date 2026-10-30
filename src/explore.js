export const placeFacets = [
 { id:'castles', name:'Zamki', icon:'castle', match:p=>p.details?.kind?p.details.kind==='castle':p.category==='heritage'&&/zamek|zamki|castle/i.test(`${p.name} ${p.subtitle}`) },
 { id:'palaces', name:'Pałace', icon:'landmark', match:p=>p.details?.kind==='palace' },
 { id:'family', name:'Atrakcje rodzinne', icon:'sparkles', match:p=>p.category==='leisure' },
 { id:'lakes', name:'Jeziora', icon:'waves', match:p=>p.details?.kind==='lake'||p.category==='nature'&&/jezior/i.test(`${p.name} ${p.subtitle}`) },
 { id:'nature', name:'Parki i przyroda', icon:'trees', match:p=>p.category==='nature'||/park/i.test(p.name) },
 { id:'history', name:'Zabytki i historia', icon:'landmark', match:p=>p.category==='heritage' },
 { id:'stays', name:'Noclegi', icon:'bed', match:p=>p.category==='stay'||p.details?.categories?.includes('stay') },
 { id:'wineries', name:'Winiarnie', icon:'grape', match:p=>p.category==='vineyard' },
 { id:'restaurants', name:'Restauracje', icon:'utensils', match:p=>p.details?.kind!=='inspiration'&&(p.category==='food'||p.details?.categories?.includes('food')) },
]
export const defaultPlaceFacets=placeFacets.filter(f=>!['stays','wineries','restaurants'].includes(f.id)).map(f=>f.id)
export function normalizeRegion(value){return value.trim().toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l').replace(/^woj(?:ewodztwo)?\.?\s*/,'').trim()}
export function matchesRegion(value){return ['lubuskie','ziemia lubuska'].includes(normalizeRegion(value))}
export function filterPlaces(places,region,query,facets){
 if(!matchesRegion(region))return []
 const needle=query.trim().toLocaleLowerCase('pl')
 return places.filter(p=>(!needle||`${p.name} ${p.subtitle} ${p.location} ${p.details?.address||''} ${(p.details?.aliases||[]).join(' ')}`.toLocaleLowerCase('pl').includes(needle))&&(!facets.length||placeFacets.some(f=>facets.includes(f.id)&&f.match(p))))
}

// Great-circle distance in kilometres; unavailable coordinates sort last.
export function distanceKm(a,b){
 const valid=p=>Number.isFinite(p?.lat)&&Math.abs(p.lat)<=90&&Number.isFinite(p?.lng)&&Math.abs(p.lng)<=180
 if(!valid(a)||!valid(b))return Infinity
 const rad=Math.PI/180,dlat=(b.lat-a.lat)*rad,dlng=(b.lng-a.lng)*rad
 const h=Math.sin(dlat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dlng/2)**2
 return 6371.0088*2*Math.asin(Math.sqrt(Math.min(1,h)))
}

// Greedy geographic ordering: keep the next closest place beside the previous one.
// Chord distance on the unit sphere has the same ordering as great-circle distance.
export function sortNearby(places,anchor){
 const valid=p=>Number.isFinite(p?.lat)&&Math.abs(p.lat)<=90&&Number.isFinite(p?.lng)&&Math.abs(p.lng)<=180
 const vector=p=>{const lat=p.lat*Math.PI/180,lng=p.lng*Math.PI/180;return [Math.cos(lat)*Math.cos(lng),Math.cos(lat)*Math.sin(lng),Math.sin(lat)]}
 const distance=(a,b)=>(a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2
 const remaining=places.filter(valid).sort((a,b)=>a.lat-b.lat||a.lng-b.lng||a.id-b.id).map(place=>({place,position:vector(place)}))
 const ordered=[]
 let current=valid(anchor)?vector(anchor):remaining[0]?.position
 while(remaining.length){
  let nearest=0,best=Infinity
  for(let i=0;i<remaining.length;i++){const d=distance(current,remaining[i].position);if(d<best){nearest=i;best=d}}
  const [next]=remaining.splice(nearest,1);ordered.push(next.place);current=next.position
 }
 return [...ordered,...places.filter(p=>!valid(p))]
}
