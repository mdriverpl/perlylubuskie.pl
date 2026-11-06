const storageKey='perly:navigation-travelled'
const limit=5000
export function trackRouteKey(geometry){
 const points=geometry?.coordinates
 if(!points?.length)return null
 let hash=2166136261
 for(const point of points)for(const char of point.slice(0,2).join(',')){hash^=char.charCodeAt(0);hash=Math.imul(hash,16777619)}
 return JSON.stringify([hash>>>0,points.length,points[0],points.at(-1)])
}
export function trackDistance(a,b){
 const rad=Math.PI/180,dlat=(b.lat-a.lat)*rad,dlng=(b.lng-a.lng)*rad
 const h=Math.sin(dlat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dlng/2)**2
 return 6371000*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)))
}
export function addTrackPoint(points,position){
 if(!Number.isFinite(position?.lat)||!Number.isFinite(position?.lng)||Math.abs(position.lat)>90||Math.abs(position.lng)>180||Number.isFinite(position.accuracy)&&position.accuracy>100)return points
 const last=points.at(-1)
 if(last&&trackDistance(last,position)<5)return points
 return [...points,{lat:position.lat,lng:position.lng,time:Date.now()}].slice(-limit)
}
export function readNavigationTrack(key){
 try{const saved=JSON.parse(localStorage.getItem(storageKey));return key&&saved?.key===key&&Array.isArray(saved.points)?saved.points.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lng)&&Math.abs(p.lat)<=90&&Math.abs(p.lng)<=180).slice(-limit):[]}catch{return []}
}
export function saveNavigationTrack(key,points){if(key)try{localStorage.setItem(storageKey,JSON.stringify({key,points:points.slice(-limit)}))}catch{}}
