import contours from './catalog/poland-regions.json' with {type:'json'}

function inRing(lng,lat,ring){
 let inside=false
 for(let i=0,j=ring.length-1;i<ring.length;j=i++){
  const a=ring[i],b=ring[j]
  if((a[1]>lat)!==(b[1]>lat)&&lng<(b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0])inside=!inside
 }
 return inside
}
export function regionAtPoint(point){
 if(!Number.isFinite(point?.lat)||!Number.isFinite(point?.lng))return null
 return contours.find(region=>point.lng>=region.bounds[0]&&point.lat>=region.bounds[1]&&point.lng<=region.bounds[2]&&point.lat<=region.bounds[3]&&region.polygons.some(polygon=>inRing(point.lng,point.lat,polygon[0])&&!polygon.slice(1).some(hole=>inRing(point.lng,point.lat,hole))))?.slug||null
}

export function regionOverview(regions=[],places=[],routes=[]){
 const published=new Map(regions.filter(r=>r.active!==false).map(r=>[r.slug,r]))
 const byId=new Map(places.filter(p=>p.details?.kind!=='custom').map(p=>[p.id,p]))
 const entries=contours.map(contour=>{
  const region=published.get(contour.slug)
  const count=region?.place_count
  return {...contour,active:!!region,places:region?(Number.isSafeInteger(count)&&count>=0?count:places.filter(p=>(p.region||'lubuskie')===contour.slug&&p.details?.kind!=='custom').length):0,walking:0,cycling:0}
 })
 const bySlug=new Map(entries.map(r=>[r.slug,r]));const seen=new Set()
 for(const route of routes){
  if(!route.is_public||!['walk','bike'].includes(route.transport)||seen.has(route.id))continue
  seen.add(route.id)
  const custom=new Map((route.custom_points||[]).map(p=>[p.id,p]));const moved=new Map((route.point_positions||[]).map(p=>[p.id,p]))
  const touched=new Set()
  for(const id of route.place_ids||[]){
   const place=byId.get(id),point=moved.get(id)||custom.get(id)
   const slug=point?regionAtPoint(point):place?(place.region||'lubuskie'):null
   if(bySlug.has(slug))touched.add(slug)
  }
  for(const slug of touched)bySlug.get(slug)[route.transport==='walk'?'walking':'cycling']++
 }
 return entries
}
