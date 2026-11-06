// A few recent, already calculated tracks; this does not calculate new routes offline.
const storageKey='perly:offline-routes'
export function offlineRouteKey(payload){
 return JSON.stringify([payload.transport,payload.place_ids,...['custom_points','point_positions'].map(field=>(payload[field]||[]).map(({id,lat,lng})=>[id,lat,lng]).sort((a,b)=>a[0]-b[0]))])
}
function entries(){try{const value=JSON.parse(localStorage.getItem(storageKey)||'[]');return Array.isArray(value)?value:[]}catch{return []}}
export function validOfflineRoute(value){return value?.geometry?.type==='LineString'&&Array.isArray(value.geometry.coordinates)&&value.geometry.coordinates.length>=2&&value.geometry.coordinates.every(p=>Array.isArray(p)&&Number.isFinite(p[0])&&Number.isFinite(p[1])&&Math.abs(p[0])<=180&&Math.abs(p[1])<=90)&&Number.isFinite(value.distance_m)&&Number.isFinite(value.duration_s)}
export function readOfflineRoute(payload){
 const found=entries().find(entry=>entry.key===offlineRouteKey(payload))
 return validOfflineRoute(found?.route)?found.route:null
}
export function rememberOfflineRoute(payload,route){
 if(!validOfflineRoute(route))return
 const key=offlineRouteKey(payload)
 const next=[{key,route,savedAt:Date.now()},...entries().filter(entry=>entry.key!==key)].slice(0,5)
 while(next.length&&JSON.stringify(next).length>1_500_000)next.pop()
 try{localStorage.setItem(storageKey,JSON.stringify(next))}catch{}
}
